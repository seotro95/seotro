"""Pitch, timeline, native duration control and bounded worker reuse checks."""
import importlib
import json
import shutil
import wave

import numpy as np
import pytest

from cue_audio import fit_cue_audio, wsola_samples
from delivery import segment_delivery
from narration import Segment


RATE = 24000


def tones(frequencies, seconds=.4):
    clock=np.arange(round(seconds*RATE))/RATE
    return np.concatenate([.2*np.sin(2*np.pi*frequency*clock) for frequency in frequencies]).astype(np.float32)


def write_pcm(path, samples):
    with wave.open(str(path),'wb') as output:
        output.setparams((1,2,RATE,0,'NONE','not compressed'))
        output.writeframes((samples*32767).astype('<i2').tobytes())


def peak(samples):
    spectrum=np.abs(np.fft.rfft(samples*np.hanning(len(samples))))
    return np.fft.rfftfreq(len(samples),1/RATE)[np.argmax(spectrum)]


@pytest.mark.parametrize('tempo',[.7,1.57,3.75])
def test_fast_stretch_keeps_order_pitch_and_exact_length(tempo):
    source=tones([220,440,660])
    output=wsola_samples(source,tempo)
    assert len(output)==round(len(source)/tempo)
    for index,frequency in enumerate([220,440,660]):
        start=round(len(output)*(index/3+.09))
        end=round(len(output)*((index+1)/3-.09))
        assert peak(output[start:end])==pytest.approx(frequency,abs=20)
    # Boundary anchors preserve both ends rather than shortening the waveform.
    assert output[0]==source[0]
    assert output[-1]==source[-1]


def test_fast_fit_cancels_without_replacing_original(tmp_path):
    path=tmp_path/'cue.wav'
    write_pcm(path,tones([220,440]))
    original=path.read_bytes()
    cancel=tmp_path/'cancel.flag'
    cancel.touch()
    with pytest.raises(InterruptedError):
        fit_cue_audio(path,RATE//2,cancel,backend='wsola')
    assert path.read_bytes()==original


@pytest.fixture
def worker(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path))
    module=importlib.import_module('worker')
    monkeypatch.setattr(module,'DATA',tmp_path)
    monkeypatch.setattr(module,'_nano_pool',None)
    monkeypatch.setattr(module,'_nano_pool_key',None)
    (tmp_path/'audio').mkdir()
    return module


def test_native_nano_uses_model_tempo_and_normalizes_once(worker,tmp_path,monkeypatch):
    observed={}
    def native(text,path,speed=1):
        observed['native_speed']=speed
        write_pcm(path,tones([220],.1))
    def normalize(source,destination,tempo,gain,*args):
        observed['normalization_tempo']=tempo
        shutil.copyfile(source,destination)
    monkeypatch.setattr(worker,'get_synthesizer',lambda job:native)
    monkeypatch.setattr(worker,'normalize_audio',normalize)
    job={'engine':'vieneu_nano','speed':1.2,'delivery':'story'}
    worker.prepare_chunk(job,Segment(text='Một lời kể.',emphasis=True),0,tmp_path)
    assert observed['native_speed']==segment_delivery(job,True)['tempo']
    assert observed['normalization_tempo']==1
    assert (tmp_path/'000000.wav').is_file()


def test_pcm_normalization_retains_matching_audio_without_ffmpeg(worker,tmp_path,monkeypatch):
    source,destination=tmp_path/'source.wav',tmp_path/'normalized.wav'
    write_pcm(source,tones([220],.1))
    def unexpected(*args,**kwargs):
        pytest.fail('Matching PCM normalization must not launch FFmpeg.')
    monkeypatch.setattr(worker.subprocess,'run',unexpected)
    worker.normalize_audio(source,destination,1,1)
    assert source.read_bytes()==destination.read_bytes()


def test_turbo_constructor_uses_budgeted_threads_and_keeps_fp32(worker,monkeypatch):
    import sys
    from types import SimpleNamespace
    observed={}
    class Turbo:
        def __init__(self,**kwargs):observed.update(kwargs)
        def infer(self,text,**kwargs):observed.update(kwargs);return 'audio'
        def save(self,audio,path):pass
    monkeypatch.setitem(sys.modules,'local_vieneu',SimpleNamespace(LocalVieneu=Turbo))
    synth=worker.load_synthesizer({'engine':'vieneu','quality':'standard','nano_threads':1,'speaker':'Mai Anh'})
    synth('Xin chào.','unused.wav')
    assert observed['threads']==1 and observed['precision']=='fp32'
    assert observed['voice']=='Mai Anh'


@pytest.mark.parametrize('reused',[False,True])
def test_resumed_checkpoints_do_not_claim_loaded_model_memory(worker,tmp_path,monkeypatch,reused):
    import io
    ident='f'*32
    jobs=tmp_path/'jobs';jobs.mkdir()
    work=tmp_path/'parts'/ident;work.mkdir(parents=True)
    if reused:(work/'000000.wav').write_bytes(b'cached checkpoint')
    path=jobs/(ident+'.json');path.write_text(json.dumps({'id':ident,'engine':'vieneu'}))
    def render(job):
        (work/'result.json').write_text(json.dumps({'execution_settings':{
            'engine':'vieneu','workers':28,'threads':1,'precision':'fp32'}}))
    monkeypatch.setattr(worker,'render',render)
    monkeypatch.setattr(worker.sys,'stdin',io.StringIO(str(path)+'\n'))
    worker.serve()
    assert json.loads((work/'worker-done.json').read_text())['code']==0
    assert (tmp_path/'warm-model.json').exists() is (not reused)


@pytest.mark.parametrize('parallel_workers',[4,8,28,32])
@pytest.mark.parametrize('engine',['vieneu_nano','vieneu','voxcpm'])
def test_nano_and_turbo_pool_prefetch_is_bounded_and_model_settings_recreate_it(worker,tmp_path,monkeypatch,parallel_workers,engine):
    executors=[]
    selected=[]
    class Future:
        def __init__(self,pool,value):
            self.pool=pool
            self.value=value
        def result(self):
            self.pool.pending-=1
            return self.value
        def cancel(self):
            return True
    class Executor:
        def __init__(self,max_workers,**kwargs):
            self.workers=max_workers
            self.pending=self.peak=0
            self.closed=False
            executors.append(self)
        def submit(self,fn,*args):
            value=fn(*args)
            self.pending+=1
            self.peak=max(self.peak,self.pending)
            return Future(self,value)
        def shutdown(self,**kwargs):
            self.closed=True
    def native(text,path,speed=1):
        write_pcm(path,tones([220],.04))
    def choose(settings):
        selected.append({key:settings.get(key) for key in ('voice_id','language','voxcpm_steps','nano_threads')})
        return native
    monkeypatch.setattr(worker,'ProcessPoolExecutor',Executor)
    monkeypatch.setattr(worker,'get_synthesizer',choose)
    text='\n\n'.join(f'{index+1}\n00:00:{index:02d},000 --> 00:00:{index:02d},500\nXin chào.' for index in range(10))
    base={'text':text,'input_format':'srt','engine':engine,'format':'wav','speed':1,
          'nano_parallel':parallel_workers,'nano_steps':4,'cue_fit':'auto','audio_fit_backend':'wsola'}
    worker.render({**base,'id':'first'})
    worker.render({**base,'id':'reuse'})
    assert len(executors)==1
    active=min(parallel_workers,8 if engine=='voxcpm' else 32,10)
    assert executors[0].workers==active and executors[0].peak<=2*active
    worker.render({**base,'id':'changed','nano_steps':8,'voxcpm_steps':4,'nano_parallel':2})
    assert len(executors)==2 and executors[0].closed
    assert executors[1].workers==2 and executors[1].peak<=4
    result=json.loads((tmp_path/'parts/changed/result.json').read_text())
    assert result['completed']==10 and result['audio_seconds']==9.5
    assert result['execution_settings']['engine']==engine
    assert result['execution_settings']['workers']==2
    if engine=='vieneu':assert result['execution_settings']['precision']=='fp32'
    if engine=='voxcpm':
        assert result['execution_settings']['precision']=='fp32'
        assert result['execution_settings']['voxcpm_steps']==4
    assert result['spoken_audio_seconds']==pytest.approx(.4)
    if engine=='voxcpm':
        worker.render({**base,'id':'different-steps','nano_steps':8,'voxcpm_steps':10,'nano_parallel':2})
        assert len(executors)==2 and not executors[1].closed
        assert all(settings['voxcpm_steps']==10 for settings in selected[-10:])
        result=json.loads((tmp_path/'parts/different-steps/result.json').read_text())
        assert result['execution_settings']['voxcpm_steps']==10
        worker.render({**base,'id':'different-voice','voice_id':'another-reference','language':'ko',
                       'quality':'standard','nano_steps':16,'voxcpm_steps':4,'nano_parallel':2})
        assert len(executors)==2 and not executors[1].closed
        assert all(settings['voice_id']=='another-reference' and settings['language']=='ko'
                   and settings['voxcpm_steps']==4 for settings in selected[-10:])
        worker.render({**base,'id':'different-threads','nano_threads':3,'voxcpm_steps':4,'nano_parallel':2})
        assert len(executors)==3 and executors[1].closed
        assert all(settings['nano_threads']==3 for settings in selected[-10:])
        worker.render({**base,'id':'different-engine','engine':'vieneu','nano_threads':3,'nano_parallel':2})
        assert len(executors)==4 and executors[2].closed
    worker.close_nano_pool()


def test_international_constructor_preserves_reference_and_uses_budgeted_steps_threads(worker,tmp_path,monkeypatch):
    import sys
    from types import SimpleNamespace
    observed={}
    reference=tmp_path/'reference.wav'
    def create(path,data,**kwargs):
        observed.update(path=path,data=data,**kwargs)
        return lambda text,output:None
    monkeypatch.setitem(sys.modules,'voxcpm_backend',SimpleNamespace(create_synthesizer=create))
    monkeypatch.setitem(sys.modules,'voice_library',SimpleNamespace(resolve_reference=lambda ident,data:(reference,{})))
    worker.load_synthesizer({'engine':'voxcpm','voice_id':'chosen','nano_threads':3,'voxcpm_steps':4})
    assert observed=={'path':reference,'data':tmp_path,'threads':3,'steps':4,'precision':'fp32'}


def test_international_steps_change_invalidates_cached_synthesizer(worker,monkeypatch):
    loaded=[]
    def load(job):
        loaded.append(job['voxcpm_steps'])
        return object()
    monkeypatch.setattr(worker,'load_synthesizer',load)
    monkeypatch.setattr(worker,'_cached_synth',None)
    monkeypatch.setattr(worker,'_cached_key',None)
    settings={'engine':'voxcpm','voice_id':'same','voxcpm_steps':10,'nano_threads':2}
    original=worker.get_synthesizer(settings)
    assert worker.get_synthesizer(settings) is original
    assert worker.get_synthesizer({**settings,'voxcpm_steps':4}) is not original
    assert loaded==[10,4]


def test_single_multichunk_cue_loads_only_one_model(worker,tmp_path,monkeypatch):
    def unexpected(*args,**kwargs):
        pytest.fail('One cue cannot use multiple model workers.')
    def native(text,path):write_pcm(path,tones([220],.04))
    monkeypatch.setattr(worker,'ProcessPoolExecutor',unexpected)
    monkeypatch.setattr(worker,'get_synthesizer',lambda job:native)
    text='1\n00:00:00,000 --> 00:00:01,000\nLời đầu.\nLời sau.'
    job={'id':'single','text':text,'input_format':'srt','engine':'voxcpm','format':'wav','speed':1,
         'nano_parallel':8,'nano_threads':3,'voxcpm_steps':4,'cue_fit':'auto','audio_fit_backend':'ffmpeg'}
    worker.render(job)
    result=json.loads((tmp_path/'parts/single/result.json').read_text())
    assert result['completed']==2
    assert result['execution_settings']['workers']==1
    assert result['execution_settings']['threads']==3
    assert result['execution_settings']['voxcpm_steps']==4


def test_wsola_single_multichunk_cue_uses_chunk_workers_and_keeps_pcm_order(worker,tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    executors=[]
    def executor(max_workers,**kwargs):
        executors.append(max_workers)
        return ThreadPoolExecutor(max_workers=max_workers)
    def native(text,path):
        write_pcm(path,tones([220 if 'đầu' in text else 440],.7))
    monkeypatch.setattr(worker,'ProcessPoolExecutor',executor)
    monkeypatch.setattr(worker,'get_synthesizer',lambda job:native)
    text='1\n00:00:00,000 --> 00:00:01,000\nLời đầu.\nLời sau.'
    settings={'text':text,'input_format':'srt','engine':'vieneu','format':'wav','speed':1,
              'nano_threads':1,'cue_fit':'auto','audio_fit_backend':'wsola'}
    worker.render({**settings,'id':'one-model','nano_parallel':1})
    worker.render({**settings,'id':'two-models','nano_parallel':2})
    assert executors==[2]
    assert (tmp_path/'audio/one-model.wav').read_bytes()==(tmp_path/'audio/two-models.wav').read_bytes()
    result=json.loads((tmp_path/'parts/two-models/result.json').read_text())
    assert result['completed']==2 and result['audio_seconds']==1
    assert result['execution_settings']['workers']==2
    assert result['execution_settings']['cue_fit_pipeline']=='serial'
    assert json.loads((tmp_path/'parts/two-models/alignment.json').read_text())['sync_ok']
    worker.close_nano_pool()


def test_shared_synthesis_closures_are_thread_local_and_keep_each_voice_and_step(worker,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    monkeypatch.setattr(worker,'_thread_synth',threading.local())
    loaded=[]
    def load(job):
        signature=(threading.get_ident(),job['voice_id'],job['nano_steps'])
        loaded.append(signature)
        return lambda:signature
    monkeypatch.setattr(worker,'load_synthesizer',load)
    barrier=threading.Barrier(2)
    def task(voice):
        job={'engine':'vieneu_nano','model_memory':'shared','voice_id':voice,'nano_steps':4}
        first=worker.get_synthesizer(job)
        barrier.wait(timeout=3)
        assert worker.get_synthesizer(job) is first
        result=first()
        changed=worker.get_synthesizer({**job,'nano_steps':16})()
        return result,changed
    with ThreadPoolExecutor(2) as pool:
        outputs=list(pool.map(task,['first','second']))
    assert outputs[0][0][0]!=outputs[1][0][0]
    assert [(old[1:],new[1:]) for old,new in outputs]==[(('first',4),('first',16)),(('second',4),('second',16))]
    assert len(loaded)==4


def test_shared_pool_is_threaded_and_legacy_pool_remains_isolated(worker):
    from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
    shared=worker.create_render_pool(2,{'engine':'vieneu_nano','model_memory':'shared'})
    legacy=worker.create_render_pool(2,{'engine':'voxcpm','model_memory':'process'})
    try:
        assert isinstance(shared,ThreadPoolExecutor) and isinstance(legacy,ProcessPoolExecutor)
    finally:
        shared.shutdown();legacy.shutdown()

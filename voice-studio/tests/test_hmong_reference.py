"""Real MP3 decoding/cropping; these checks do not represent model inference."""
from test_hmong_variant import run_case


def test_known_long_originals_get_the_project_excerpt_and_editable_prefill(tmp_path):
    run_case(tmp_path, '''
import hashlib,io,wave
from fastapi.testclient import TestClient
from hmong_assets import ROOT,references
import app
with TestClient(app.app) as client:
    assert client.get('/api/config').json()['default_voice_id']=='hmong-male'
    for gender,item in references().items():
        content=(ROOT/item['file']).read_bytes()
        upload={'file':(item['user_filename'],content,'audio/mpeg')}
        meta=client.post('/api/hmong/reference-info',files=upload)
        assert meta.status_code==200,meta.text
        info=meta.json()
        assert info['duration']>8 and info['automatic'] and not info['requires_selection']
        assert not info['requires_transcript'] and info['known_preset']=='hmong-'+gender
        assert info['transcript']==item['reference']['text']
        assert info['transcript_verified'] is False and info['transcript_source']=='project_prefill'
        response=client.post('/api/voices/clone',data={'name':'Known '+gender,'language':'mww','consent':'true'},files=upload)
        assert response.status_code==201,response.text
        record=response.json()
        assert record['engine']=='f5_hmong' and record['automatic_reference']
        assert record['known_preset']=='hmong-'+gender
        assert record['source_sha256']==hashlib.sha256(content).hexdigest()
        assert record['reference_start']==item['reference']['start']
        assert record['reference_end']==item['reference']['end']
        assert record['transcript']==item['reference']['text']
        explicit=client.post('/api/voices/clone',data={'name':'Known explicit '+gender,'consent':'true',
            'reference_start':item['reference']['start'],'reference_end':item['reference']['end']},files=upload)
        assert explicit.status_code==201,explicit.text
        assert explicit.json()['automatic_reference'] and explicit.json()['transcript']==item['reference']['text']
        audio=client.get('/api/voices/'+record['id']+'/sample')
        with wave.open(io.BytesIO(audio.content),'rb') as sample:
            assert (sample.getnchannels(),sample.getsampwidth(),sample.getframerate())==(1,2,24000)
            assert sample.getnframes()==round((record['reference_end']-record['reference_start'])*24000)
        original=client.get('/api/hmong/presets/hmong-'+gender+'/sample')
        assert original.headers['content-type']=='audio/mpeg'
        assert original.content==content
    assert not list((app.DATA/'voices').glob('*.upload'))
    assert not list((app.DATA/'voices').glob('*.decoded.wav'))
    assert not list((app.DATA/'parts').glob('reference-info-*'))
''')


def test_known_crop_preserves_custom_words_and_marks_only_inherited_words_automatic(tmp_path):
    run_case(tmp_path, '''
from hmong_assets import ROOT,references
from hmong_reference import select_reference
custom='Kuv sau cov lus no rau kuv tus kheej.'
for gender,item in references().items():
    content=(ROOT/item['file']).read_bytes()
    saved=item['reference']
    for bounds in [(None,None),(saved['start'],saved['end'])]:
        for words,automatic in [('',True),(saved['text'],True),(custom,False)]:
            selected=select_reference(content,item['duration'],words,*bounds)
            assert selected['reference_start']==saved['start']
            assert selected['reference_end']==saved['end']
            assert selected['transcript']==(saved['text'] if automatic else custom)
            assert selected['automatic_reference'] is automatic
            assert selected['known_preset']=='hmong-'+gender
''')


def test_known_mp3_clone_keeps_custom_words_when_crop_bounds_are_omitted(tmp_path):
    run_case(tmp_path, '''
from fastapi.testclient import TestClient
from hmong_assets import ROOT,references
import app
custom='Kuv sau cov lus no rau kuv tus kheej.'
with TestClient(app.app) as client:
    for gender,item in references().items():
        upload={'file':(item['user_filename'],(ROOT/item['file']).read_bytes(),'audio/mpeg')}
        response=client.post('/api/voices/clone',data={'name':'Custom '+gender,
            'language':'mww','consent':'true','transcript':custom},files=upload)
        assert response.status_code==201,response.text
        record=response.json()
        assert record['transcript']==custom
        assert record['automatic_reference'] is False
        assert record['known_preset']=='hmong-'+gender
        assert record['reference_start']==item['reference']['start']
        assert record['reference_end']==item['reference']['end']
''')


def test_unknown_long_recording_needs_an_explicit_crop_and_matching_words(tmp_path):
    run_case(tmp_path, '''
import io,wave
from fastapi.testclient import TestClient
import app
buf=io.BytesIO()
with wave.open(buf,'wb') as audio:
    audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000)
    audio.writeframes(b'\\0\\0'*24000*4+b'\\x00\\x20'*24000*7+b'\\0\\0'*24000)
content=buf.getvalue()
with TestClient(app.app) as client:
    upload={'file':('long.wav',content,'audio/wav')}
    info=client.post('/api/hmong/reference-info',files=upload).json()
    assert info['duration']==12 and info['requires_selection'] and info['requires_transcript']
    assert info['known_preset'] is None and info['transcript']==''
    assert info['transcript_verified'] is False and info['transcript_source']=='manual'
    data={'name':'My selected voice','language':'mww','consent':'true','transcript':'Nyob zoo.'}
    assert client.post('/api/voices/clone',data=data,files=upload).status_code==422
    data.update(reference_start='4',reference_end='9')
    response=client.post('/api/voices/clone',data=data,files=upload)
    assert response.status_code==201,response.text
    record=response.json()
    assert record['duration']==5 and record['source_duration']==12
    assert record['reference_start']==4 and record['reference_end']==9
    assert not record['automatic_reference'] and record['known_preset'] is None
    assert record['transcript']=='Nyob zoo.'
    selected=client.get('/api/voices/'+record['id']+'/sample').content
    with wave.open(io.BytesIO(selected),'rb') as audio:
        assert audio.readframes(audio.getnframes())==b'\\x00\\x20'*24000*5
    for start,end in [('0','2'),('0','9'),('-1','4'),('9','14'),('nan','6'),('2','inf')]:
        invalid={**data,'reference_start':start,'reference_end':end}
        assert client.post('/api/voices/clone',data=invalid,files=upload).status_code==422
    for invalid in [{**data,'transcript':''},{**data,'reference_end':''},{**data,'reference_start':'0','reference_end':'3'}]:
        # Blank words, incomplete crop, and an entirely silent selected interval must fail.
        assert client.post('/api/voices/clone',data=invalid,files=upload).status_code==422
    assert len(list((app.DATA/'voices').glob('*.json')))==1
    assert not list((app.DATA/'voices').glob('*.upload'))
    assert not list((app.DATA/'voices').glob('*.decoded.wav'))
''')


def test_metadata_rejects_corruption_unsupported_files_and_oversized_uploads(tmp_path):
    run_case(tmp_path, '''
from fastapi.testclient import TestClient
import app
with TestClient(app.app) as client:
    for filename,data,status in [('broken.mp3',b'not audio',422),('sample.txt',b'not audio',422),('sample.wav',b'x'*(20*1024*1024+1),413)]:
        response=client.post('/api/hmong/reference-info',files={'file':(filename,data)})
        assert response.status_code==status,response.text
    assert not list((app.DATA/'parts').glob('reference-info-*'))
    assert not list((app.DATA/'voices').iterdir())
''')

"""Bounded public-sample Qwen diagnostic; never modifies product generation.

Compare checkpoint sampling defaults and the current greedy settings on one
warm CPU FP32 model, observing the existing talker output without changing it.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.parse

import prepare_complete_models as complete


def prepare(root):
    root=Path(root)
    if root.exists() or root.is_symlink():raise FileExistsError('Use a new probe directory')
    root.mkdir(parents=True)
    complete.write_json(root/'EXTRA-PACK-OWNER.json',complete.OWNER)
    plan=complete.resolve_qwen('qwen')
    complete.write_json(root/'EXTRA-MODEL-PLAN.json',{'purpose':'bounded-qwen-public-diagnostic','qwen':{'qwen':plan}})
    records=[]
    for entry in plan['files']:
        url=('https://huggingface.co/'+plan['repository']+'/resolve/'+plan['revision']+'/'
             +urllib.parse.quote(entry['name'],safe='/')+'?download=true')
        target=root/'app/.data/models'/plan['model_dir']/entry['name']
        records.append(complete._download_record(url,target,entry))
    marker={**plan,'files':records,'source_weights_verified':True,'cpu_synthesis_tested':False,
            'gpu_inference_tested':False,'target_30x_guaranteed':False}
    complete.write_json(root/'app/.data/models/qwen.ready',marker)
    complete.write_json(root/'EXTRA-MODEL-PINS.json',{'purpose':'bounded-qwen-public-diagnostic','qwen':{'qwen':marker}})


def _notice(title,value):
    text=json.dumps(value,ensure_ascii=False,separators=(',',':'))
    print('::notice title='+title+'::'+text.replace('%','%25').replace('\r','%0D').replace('\n','%0A'),flush=True)


def run(root,output,max_tokens=128):
    root=complete.owned(root)
    if os.name!='nt' or Path(sys.executable).resolve()!=(root/'runtime-qwen/python.exe').resolve():
        raise ValueError('Use the isolated Windows Qwen interpreter')
    if not 16<=max_tokens<=128:raise ValueError('Diagnostic token cap must be between 16 and 128')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    import torch
    import numpy as np
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    torch.set_num_threads(4)
    marker=json.loads((root/'app/.data/models/qwen.ready').read_text(encoding='utf-8'))
    for entry in marker['files']:
        path=root/'app/.data/models'/marker['model_dir']/entry['name']
        if path.stat().st_size!=entry['size'] or complete.sha256(path)!=entry['sha256']:
            raise ValueError('Diagnostic checkpoint changed after immutable verification')
    report={'format':'voice-studio-qwen-generation-probe-v1','platform':'win32','device':'cpu',
            'precision':'fp32','attention':'sdpa','threads':4,'torch':torch.__version__,
            'repository':marker['repository'],'revision':marker['revision'],
            'model_marker_sha256':complete.sha256(root/'app/.data/models/qwen.ready'),
            'speaker':'Ryan','text':'Hello.','max_new_tokens':max_tokens,'cases':[],
            'gpu_inference_tested':False,'human_pronunciation_or_voice_identity_tested':False,
            'product_generation_changed':False,'target_30x_guaranteed':False}
    _notice('Qwen bounded probe loading',{'revision':marker['revision'],'max_new_tokens':max_tokens})
    started=time.perf_counter()
    model=Qwen3TTSModel.from_pretrained(str(root/'app/.data/models'/marker['model_dir']),
        device_map='cpu',dtype=torch.float32,attn_implementation='sdpa',local_files_only=True)
    report['model_load_seconds']=time.perf_counter()-started
    talker=model.model.talker
    original=talker.generate
    config=model.model.config.talker_config
    eos=getattr(config,'codec_eos_token_id',None)
    folder=root/'qa-probe';folder.mkdir()
    for mode in ('standard','greedy'):
        observed=[]
        def capture(*args,**kwargs):
            result=original(*args,**kwargs)
            sequence=getattr(result,'sequences',None)
            if sequence is not None:
                row={'sequence_shape':list(sequence.shape),'codec_eos_token_id':eos,
                     'last_token':int(sequence[0,-1].item()),
                     'last_tokens':[int(v) for v in sequence[0,-8:].tolist()]}
                row['ended_with_codec_eos']=row['last_token']==eos if eos is not None else None
                observed.append(row)
            return result
        talker.generate=capture
        torch.manual_seed(1234)
        options={'text':'Hello.','language':'English','speaker':'Ryan','max_new_tokens':max_tokens}
        if mode=='greedy':options.update(do_sample=False,subtalker_dosample=False)
        _notice('Qwen bounded probe starting',{'mode':mode,'max_new_tokens':max_tokens})
        started=time.perf_counter()
        try:
            samples,rate=model.generate_custom_voice(**options)
            audio=np.asarray(samples[0],dtype=np.float32)
            if audio.ndim!=1 or len(audio)==0 or not np.isfinite(audio).all():raise ValueError('Invalid diagnostic PCM')
            destination=folder/(mode+'.wav');sf.write(str(destination),audio,rate,subtype='PCM_16')
            row={'mode':mode,'synthesis_seconds':time.perf_counter()-started,'audio_seconds':len(audio)/rate,
                 'sample_rate':int(rate),'non_silent':bool(np.max(np.abs(audio))>0.00001),
                 'talker_observations':observed,'wav_sha256':complete.sha256(destination)}
            row['audio_per_wall_second']=row['audio_seconds']/row['synthesis_seconds']
            row['diagnostic_cap_audio_seconds']=max_tokens*1920/24000
            report['cases'].append(row)
            complete.write_json(output,report)
            _notice('Qwen bounded probe result',row)
        except BaseException as exc:
            report['cases'].append({'mode':mode,'error_type':type(exc).__name__,'error':str(exc)[:2000],
                                    'seconds':time.perf_counter()-started,'talker_observations':observed})
            complete.write_json(output,report)
            raise
        finally:talker.generate=original
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','run'))
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--max-new-tokens',type=int,default=128)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.root)
    else:
        if args.output is None:parser.error('--output is required for run')
        run(args.root,args.output,args.max_new_tokens)


if __name__=='__main__':main()

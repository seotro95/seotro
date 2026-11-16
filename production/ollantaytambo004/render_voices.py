#!/usr/bin/env python3
"""Render 16 male narrations with the pinned Melo + Viet Studio 1.3.1 online backend.
Usage: python render_voices.py --script script_master.json --translations translations --out outputs/voices
Text goes to Microsoft Edge Read Aloud via third-party edge-tts; no paid API key is needed.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import wave

RATE = 24000
SECONDS = 1302
FRAMES = RATE * SECONDS
BACKEND_COMMIT = '4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043'
BACKEND_BLOB = '8df7c8375d9693bed644167290a3bb86cca705c0'
VOICES = {
'en':('en-US','en-US-AndrewNeural'), 'vi':('vi-VN','vi-VN-NamMinhNeural'),
'es':('es-ES','es-ES-AlvaroNeural'), 'fr':('fr-FR','fr-FR-HenriNeural'),
'ja':('ja-JP','ja-JP-KeitaNeural'), 'ko':('ko-KR','ko-KR-InJoonNeural'),
'de':('de-DE','de-DE-ConradNeural'), 'it':('it-IT','it-IT-DiegoNeural'),
'pt':('pt-PT','pt-PT-DuarteNeural'), 'nl':('nl-NL','nl-NL-MaartenNeural'),
'pl':('pl-PL','pl-PL-MarekNeural'), 'sv':('sv-SE','sv-SE-MattiasNeural'),
'da':('da-DK','da-DK-JeppeNeural'), 'fi':('fi-FI','fi-FI-HarriNeural'),
'no':('nb-NO','nb-NO-FinnNeural'), 'cs':('cs-CZ','cs-CZ-AntoninNeural')
}
ROOT = Path(__file__).resolve().parent

def write_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)

def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()

def command(args, timeout=600):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8','replace')[-1600:])
    return result.stdout

def wav_info(path):
    with wave.open(str(path),'rb') as source:
        if (source.getnchannels(),source.getsampwidth(),source.getframerate()) != (1,2,RATE):
            raise ValueError(f'Wrong WAV format: {path}')
        declared = source.getnframes(); actual = 0; signal = False
        while block := source.readframes(65536):
            actual += len(block)//2; signal = signal or any(block)
    if not signal or actual != declared or not actual:
        raise ValueError(f'Empty, silent or incomplete WAV: {path}')
    return {'sample_rate':RATE,'sample_frames':actual,'seconds':actual/RATE}

def load_backend():
    path = ROOT/'vendor/online_backend.py'; content = path.read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    if blob != BACKEND_BLOB:
        raise ValueError('Vendored Melo backend differs from pinned original.')
    spec = importlib.util.spec_from_file_location('original_melo_online_backend',path)
    backend = importlib.util.module_from_spec(spec); spec.loader.exec_module(backend)
    sys.path.insert(0,str(ROOT/'vendor'))
    from online_transport import configure
    return configure(backend), {'source_commit':BACKEND_COMMIT,'source_git_blob_sha1':blob,
        'source_sha256':hashlib.sha256(content).hexdigest(),
        'source_url':f'https://raw.githubusercontent.com/seotro95/seotro/{BACKEND_COMMIT}/melo-viet-local/online_backend.py',
        'original_source_modified':False,'complete_word_metadata_transport_wrapper':True,
        'transport_reference':'2f1ab371cacc140d180966bfc447c36cc11dfc0c/upano-moi011/online_transport.py'}

def extract_rows(data, language):
    if isinstance(data,dict):
        for key in ('rows','scenes','cues','script'):
            if key in data:
                data = data[key]; break
    if not isinstance(data,list):
        raise ValueError(f'{language}: expected list of rows.')
    rows = {}
    for index,row in enumerate(data,1):
        if isinstance(row,list):
            identifier = row[0]; text = row[2] if language == 'vi' and len(row)>2 else row[1]
        elif isinstance(row,str):
            identifier,text = index,row
        else:
            identifier = row.get('id',row.get('scene',row.get('scene_id',index)))
            text = row.get(language)
            if text is None:
                for key in ('text','voice','narration','voice_'+language,'narration_'+language):
                    if key in row:
                        text=row[key];break
            if isinstance(text,dict):
                text=text.get(language)
        identifier=int(identifier)
        if identifier in rows or not isinstance(text,str) or '\0' in text:
            raise ValueError(f'{language}: invalid row {identifier}.')
        rows[identifier]=text.strip()
    if set(rows) != set(range(1,132)) or any(not rows[i] for i in range(1,131)) or rows[131]:
        raise ValueError(f'{language}: need spoken IDs1-130 and empty ID131.')
    return rows

def split_text(text,limit=1100):
    sentences = re.split(r'(?<=[.!?。！？…])\s+',text.strip())
    atoms=[]
    for sentence in sentences:
        while len(sentence)>limit:
            cut=sentence.rfind(' ',0,limit+1)
            if cut<=0: cut=limit
            atoms.append(sentence[:cut].strip());sentence=sentence[cut:].lstrip()
        if sentence: atoms.append(sentence)
    pieces=[];buffer=''
    for atom in atoms:
        candidate=(buffer+' '+atom).strip()
        if buffer and len(candidate)>limit:
            pieces.append(buffer);buffer=atom
        else: buffer=candidate
    if buffer: pieces.append(buffer)
    compact=lambda s:re.sub(r'\s+','',s)
    if not pieces or any(not p or len(p)>1200 for p in pieces) or compact(''.join(pieces))!=compact(text):
        raise ValueError('Text splitting altered content.')
    return pieces

def concatenate(paths,output,listing):
    escape=lambda p:str(Path(p).resolve()).replace("'","'\\''")
    listing.write_text('ffconcat version 1.0\n'+''.join("file '"+escape(p)+"'\n" for p in paths),encoding='utf-8')
    command(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','0',
        '-i',str(listing),'-vn','-ac','1','-ar',str(RATE),'-c:a','pcm_s16le',str(output)])

def atempo(value):
    factors=[]
    while value<.5: factors.append(.5);value/=.5
    while value>2: factors.append(2);value/=2
    factors.append(value)
    return ','.join(f'atempo={v:.12g}' for v in factors)

def render_chunk(backend,language,rows,start,work,max_tempo):
    locale,voice=VOICES[language]
    ids=list(range(start,min(start+6,131)));number=(start-1)//6+1
    target=42 if start==127 else 60; spoken=40 if start==127 else 60
    budget=round((spoken-.25)*RATE); target_frames=target*RATE
    folder=work/language/f'chunk_{number:02}';folder.mkdir(parents=True,exist_ok=True)
    text='\n\n'.join(rows[i] for i in ids)
    (folder/'source.txt').write_text(text+'\n',encoding='utf-8')
    sources=[];segments=[]
    for n,piece in enumerate(split_text(text),1):
        signature=hashlib.sha256((voice+'\0'+piece).encode()).hexdigest()
        source=folder/f'raw_{n:02}_{signature[:12]}.wav';metadata=source.with_suffix('.json')
        cached=False
        if source.exists() and metadata.exists():
            old=json.loads(metadata.read_text(encoding='utf-8'))
            if old.get('signature')==signature and old.get('word_coverage_verified') is True:
                try: wav_info(source);cached=True
                except (ValueError,wave.Error,EOFError): pass
        if not cached:
            source.unlink(missing_ok=True)
            result=backend.handle({'op':'render','language':locale,'voice':voice,'text':piece,'output':str(source)})
            info=wav_info(source)
            words=json.loads(source.with_suffix('.edge.words.json').read_text(encoding='utf-8'))
            if words.get('verified') is not True: raise ValueError('Unverified speech completeness.')
            write_json(metadata,{'signature':signature,'voice_id':voice,'text':piece,
                'word_coverage_verified':True,'word_coverage_ratio':words['coverage_ratio'],
                'native_wav':info,'backend_result':result})
        sources.append(source);segments.append({'file':source.name,'cached':cached,**wav_info(source)})
    joined=folder/'native_joined.wav';concatenate(sources,joined,folder/'native.ffconcat')
    native=wav_info(joined);tempo=native['sample_frames']/budget
    if tempo>max_tempo: raise ValueError(f'{language} chapter{number}: required tempo{tempo:.3f} exceeds limit; no words cut.')
    fitted=folder/'fitted.wav';attempts=[]
    for attempt in range(7):
        command(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(joined),
            '-vn','-ac','1','-ar',str(RATE),'-af',atempo(tempo),'-c:a','pcm_s16le',str(fitted)])
        fitted_info=wav_info(fitted);attempts.append({'tempo':tempo,**fitted_info})
        if fitted_info['sample_frames']<=budget: break
        tempo*=fitted_info['sample_frames']/budget*1.001
        if tempo>max_tempo: raise ValueError('Measured fit exceeds tempo limit; no speech trimmed.')
    else: raise ValueError('Tempo fitting did not converge; no speech trimmed.')
    padding=target_frames-fitted_info['sample_frames']
    if padding<round(.25*RATE): raise ValueError('Missing verified silence margin.')
    aligned=folder/'aligned.wav'
    command(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(fitted),
        '-af',f'apad=pad_len={padding},atrim=end_sample={target_frames}','-ac','1','-ar',str(RATE),
        '-c:a','pcm_s16le',str(aligned)])
    info=wav_info(aligned)
    if info['sample_frames']!=target_frames: raise ValueError('Incorrect aligned chapter sample count.')
    report={'complete':True,'language':language,'voice_id':voice,'locale':locale,'chapter':number,
        'scene_ids':ids,'start_seconds':(number-1)*60,'target_seconds':target,
        'speech_budget_seconds':budget/RATE,'native':native,'segments':segments,
        'pitch_preserving_tempo':tempo,'attempts':attempts,'padding_frames':padding,
        'speech_truncated':False,'aligned':info,'file':str(aligned.resolve())}
    write_json(folder/'REPORT.json',report)
    print(f'VERIFIED {language} chapter {number}/22',flush=True)
    return report

def finalize(language,reports,work,out):
    reports=sorted(reports,key=lambda r:r['chapter'])
    if [r['chapter'] for r in reports]!=list(range(1,23)): raise ValueError('Missing chapters.')
    folder=work/language;master=folder/'master.wav'
    concatenate([r['file'] for r in reports],master,folder/'master.ffconcat')
    info=wav_info(master)
    if info['sample_frames']!=FRAMES: raise ValueError('Lossless master has incorrect duration.')
    voice=VOICES[language][1];base=f'004_{language}_{voice}'
    encoded=out/(base+'.partial.m4a');final=out/(base+'.m4a')
    command(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(master),
        '-vn','-ac','1','-ar',str(RATE),'-c:a','aac','-b:a','96k','-t',str(SECONDS),
        '-movflags','+faststart',str(encoded)])
    probe=json.loads(command(['ffprobe','-v','error','-select_streams','a:0',
        '-show_entries','stream=codec_name,sample_rate,channels,duration,duration_ts,time_base:format=duration',
        '-of','json',str(encoded)]))
    stream=probe['streams'][0];duration=float(stream.get('duration',probe['format']['duration']))
    if abs(duration-SECONDS)>1/RATE+1e-6 or stream['codec_name']!='aac' or int(stream['sample_rate'])!=RATE or stream['channels']!=1:
        raise ValueError(f'{language}: encoded format or media timeline incorrect.')
    pcm=folder/'decode_check.pcm'
    command(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(encoded),
        '-ac','1','-ar',str(RATE),'-c:a','pcm_s16le','-f','s16le',str(pcm)])
    size=pcm.stat().st_size;pcm.unlink()
    decoded=size//2
    if size%2 or not 0<=decoded-FRAMES<=1024: raise ValueError('Unexpected AAC decoded sample count.')
    encoded.replace(final)
    if language=='en': shutil.copyfile(master,out/(base+'.wav'))
    report={'complete':True,'language':language,'locale':VOICES[language][0],'voice_id':voice,
        'file':final.name,'sha256':digest(final),'duration_seconds':duration,
        'lossless_master':info,'lossless_sha256':digest(master),'ffprobe':probe,
        'aac_decoded_frames':decoded,'aac_codec_padding_frames':decoded-FRAMES,
        'speech_truncated':False,'word_coverage_verified':True,
        'alignment':'22 shared chapter boundaries, not word-level or every 10-second scene.',
        'chapters':reports}
    write_json(out/(base+'_REPORT.json'),report)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--script',type=Path,required=True);p.add_argument('--translations',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--work',type=Path,default=Path('work/voice_render'))
    p.add_argument('--workers',type=int,choices=(1,2,3,4),default=3)
    p.add_argument('--languages',default=','.join(VOICES));p.add_argument('--max-tempo',type=float,default=2)
    args=p.parse_args();languages=list(dict.fromkeys(args.languages.split(',')))
    if not languages or any(x not in VOICES for x in languages): p.error('Unknown language.')
    if not math.isfinite(args.max_tempo) or args.max_tempo<=0: p.error('Invalid tempo limit.')
    if version('edge-tts')!='7.3.1': p.error('Install pinned edge-tts==7.3.1.')
    for executable in ('ffmpeg','ffprobe'):
        if not shutil.which(executable): p.error('Missing '+executable)
    args.out.mkdir(parents=True,exist_ok=True);args.work.mkdir(parents=True,exist_ok=True)
    os.environ['MELO_VIET_ROOT']=str((args.work/'backend_state').resolve())
    master=json.loads(args.script.read_text(encoding='utf-8-sig'));texts={}
    for language in languages:
        path=args.translations/(language+'.json')
        data=master if language=='en' or (language=='vi' and not path.exists()) else json.loads(path.read_text(encoding='utf-8-sig'))
        texts[language]=extract_rows(data,language)
    backend,provenance=load_backend();started=time.time()
    catalogue=backend.handle({'op':'catalog','refresh':True})
    write_json(args.work/'SERVICE_CATALOGUE.json',catalogue)
    by_id={v['id']:v for v in catalogue['voices']};profiles=[]
    male_options={locale:sorted((v['id'] for v in catalogue['voices']
        if v['locale']==locale and v['gender'].casefold()=='male')) for locale,_ in VOICES.values()}
    print('LIVE_MALE_CATALOGUE '+json.dumps(male_options,ensure_ascii=False),flush=True)
    preferred_fallbacks={'de-DE':['de-DE-FlorianMultilingualNeural','de-DE-KillianNeural','de-DE-BerndNeural']}
    for language in languages:
        locale,requested=VOICES[language];voice=requested;v=by_id.get(voice)
        selected_as_requested=bool(v and v['locale']==locale and v['gender'].casefold()=='male')
        if not selected_as_requested:
            # Nam Minh is explicitly required by the user, so never replace him.
            if language=='vi':
                raise ValueError('Required vi-VN-NamMinhNeural unavailable; no Vietnamese substitution allowed.')
            candidates=male_options.get(locale,[])
            if not candidates:
                raise ValueError(f'No real male voice is available for {locale}.')
            voice=next((candidate for candidate in preferred_fallbacks.get(locale,[]) if candidate in candidates),candidates[0])
            v=by_id[voice];VOICES[language]=(locale,voice)
            print('SELECT_AVAILABLE_MALE '+json.dumps({'language':language,'requested':requested,'selected':voice,
                'reason':'Requested candidate unavailable in current catalogue; user authorized automatic male selection.'}),flush=True)
        profiles.append({'language':language,'locale':locale,'voice_id':voice,'requested_voice_id':requested,
            'selected_as_requested':selected_as_requested,'gender':v['gender'],
            'service_name':v['name'],'native_rate':'+0%','native_pitch':'+0Hz','reuse_exact_id':True})
    provenance.update({'status':'rendering','provider':'Microsoft Edge Read Aloud via original Melo + Viet Studio 1.3.1',
        'edge_tts_version':version('edge-tts'),'ffmpeg_version':command(['ffmpeg','-version']).decode().splitlines()[0],
        'catalogue_verified':True,'catalogue_sha256':digest(args.work/'SERVICE_CATALOGUE.json'),
        'tls_verification_enabled':True,'target_seconds':SECONDS,'sample_rate':RATE,'started_unix':started,
        'transport_wrapper_sha256':digest(ROOT/'vendor/online_transport.py')})
    write_json(args.out/'TOOL_PROVENANCE.json',provenance)
    write_json(args.out/'VOICE_PROFILES_LOCKED.json',{'episode':'004-ollantaytambo','profiles':profiles,
        'target_seconds':SECONDS,'online_update_note':'Reuse exact IDs and native settings. Provider models may change.',
        'alignment':'21 chapters of60seconds and final chapter42seconds; final2seconds without narration.'})
    reports={language:[] for language in languages}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(render_chunk,backend,language,texts[language],start,args.work,args.max_tempo)
                 for language in languages for start in range(1,131,6)]
        try:
            for future in as_completed(futures):
                item=future.result();reports[item['language']].append(item)
        except BaseException:
            for future in futures:future.cancel()
            raise
    deliveries=[]
    for language in languages:
        deliveries.append(finalize(language,reports[language],args.work,args.out))
        write_json(args.out/'MANIFEST_PARTIAL.json',{'complete':False,'verified_languages':[r['language'] for r in deliveries]})
        print(f'DELIVERED {language}: exact21:42 media timeline',flush=True)
    provenance.update({'status':'complete','elapsed_seconds':time.time()-started,'actual_tracks':len(deliveries)})
    write_json(args.out/'TOOL_PROVENANCE.json',provenance)
    write_json(args.out/'MANIFEST.json',{'complete':True,'episode':'004-ollantaytambo','target_seconds':SECONDS,
        'sample_exact_wav_frames':FRAMES,'sample_rate':RATE,'all_requested_languages':len(languages)==16,
        'tracks':deliveries,'source_script_sha256':digest(args.script)})
    (args.out/'MANIFEST_PARTIAL.json').unlink(missing_ok=True)
    print('All requested tracks were synthesized and technically verified.',flush=True)

if __name__=='__main__':
    main()

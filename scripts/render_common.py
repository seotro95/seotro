import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(os.environ.get('PRODUCTION_WORK_DIR',Path(__file__).resolve().parent)).resolve();BASE=ROOT/'voice';AUDIO=BASE/'audio';AUDIO.mkdir(parents=True,exist_ok=True)
TOOL=Path(os.environ.get('MELO_TOOL_DIR','/workspace/work/release/melo-viet-local')).resolve();sys.path.insert(0,str(TOOL))
from timing import TimedAssembler,measure_encoded
from documents import convert_audio
TARGET_SECONDS=int(os.environ.get('PRODUCTION_TARGET_SECONDS','1215'));TARGET_FRAMES=TARGET_SECONDS*48000
PROFILES={p['locale']:p for p in json.loads((ROOT/'BASELINE_VOICE_PROFILES.json').read_text())['profiles']}

def chunks(text,limit=980):
    # Keep numerical values intact across regional thousands conventions. A
    # period in 23.000 is not a sentence boundary; French thin-space groups
    # must not be separated into different synthesis requests either.
    text=re.sub(r'(?<!\d)\d{1,3}(?:(?:[.,\u00a0\u202f ]\d{3})+)(?!\d)',
                lambda m:re.sub(r'[.,\u00a0\u202f ]','',m.group()),text)
    sentences=re.split(r'(?<=[.!?])\s+|(?<=[。！？])',text.strip())
    result=[];current=''
    for sentence in sentences:
        sentence=sentence.strip()
        if not sentence:continue
        if len(sentence)>limit:
            words=sentence.split();pieces=[];piece=''
            if len(words)==1:pieces=[sentence[i:i+limit] for i in range(0,len(sentence),limit)]
            else:
                for word in words:
                    if piece and len(piece+' '+word)>limit:pieces.append(piece);piece=''
                    piece=(piece+' '+word).strip()
                if piece:pieces.append(piece)
        else:pieces=[sentence]
        for piece in pieces:
            if current and len(current+' '+piece)>limit:result.append(current);current=''
            current=(current+' '+piece).strip()
    if current:result.append(current)
    assert result and all(0<len(x)<=limit for x in result)
    return result

def make_plan(locale,rows):
    expected=int(os.environ.get('PREVIEW_CUES','122')) if locale=='en-US' else 12
    assert len(rows)==expected,(locale,len(rows))
    return {'source_format':'srt','target_seconds':TARGET_SECONDS,'target_frames':TARGET_FRAMES,
            'cues':[{'start_ms':int(r['start']*1000),'end_ms':int(r['end']*1000),'text':r['voice']} for r in rows]}

def finalize(locale,rows,records,out):
    shutil.rmtree(out/'.timing',ignore_errors=True)
    assembler=TimedAssembler(out,make_plan(locale,rows),max_tempo=1.4 if locale=='en-US' else 1.5)
    try:
        for cue,text,path in records:
            prepared=out/'prepared.wav';convert_audio(path,prepared,1,sample_rate=48000,gain_db=0)
            assembler.append(prepared,text,cue=cue)
        result=assembler.finish()
    except Exception:assembler.close();raise
    assert max(c['padding_frames'] for c in result['sync_report']['cues'])/48000<.1, 'Incomplete synthesis: excessive cue padding; preserve checkpoints for repair.'
    suffix='mww_female' if locale=='mww' else locale
    mp3=out/f'KOSTENKI_19_{suffix}.mp3'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-threads','1','-y','-i',str(out/'part-0001.wav'),
                    '-map','0:a:0','-ac','1','-ar','24000','-c:a','libmp3lame','-b:a','64k',str(mp3)],check=True)
    duration=measure_encoded(mp3,out,48000,TARGET_FRAMES)
    sync=result['sync_report']['cues'];profile=PROFILES[locale]
    result.update(locale=locale,voice_id=profile['voice_id'],gender=profile['gender'],engine=profile['engine'],
                  source_commit=profile['source_commit'],alignment_granularity='121x10_seconds_plus_final5_seconds' if locale=='en-US' else '11chapters100_seconds_plus_final115_seconds',
                  expected_pcm_frames_48000=TARGET_FRAMES,mp3_decoded_duration=duration,
                  mp3_file=mp3.name,mp3_bytes=mp3.stat().st_size,mp3_sha256=hashlib.sha256(mp3.read_bytes()).hexdigest(),
                  max_used_post_tempo=max(c['tempo'] for c in sync),min_used_post_tempo=min(c['tempo'] for c in sync),
                  max_cue_padding_seconds=max(c['padding_frames'] for c in sync)/48000,
                  translation_review_status='original English script' if locale=='en-US' else 'Translated and terminology/context reviewed by assistant; independent native editorial/listening review pending')
    result['numeric_speech_handling']='Original English numerals preserved; translated grouped integers normalized before sentence splitting; Hmong uses native number-word normalization.'
    if locale=='mww':
        result.update(reference_sha256=profile['reference_sha256'],reference_url=profile['reference_url'],
                      audio_profile='clear-v1',white_hmong_dialect_independently_verified=False,
                      native_speed=1.0,native_quality='fast',native_precision='fp32',native_device='cpu')
    result['narration_style_id']='science-documentary-expressive-v1'
    result['prosody_method']='Native phrase speed/gain/pause controls; no word timing' if locale=='mww' else 'Melo online backend with Edge rate/word-boundary adapter and gentle1.2dB word accents'
    result['voice_identity_preserved']=True
    result['pitch_shift_applied']=False
    notes=[json.loads(p.read_text()) for p in out.glob('raw-*.style.json')]
    if notes:result['prosody_summary']={'pieces':len(notes),'word_boundaries':sum(n['word_boundary_count'] for n in notes),'word_accents':sum(len(n['word_accents']) for n in notes),'settings_used':sorted({n['settings']['rate'] for n in notes})}
    (out/'render_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    for p in out.glob('raw-*.wav'):p.unlink()
    (out/'prepared.wav').unlink(missing_ok=True)
    if locale!='en-US':(out/'part-0001.wav').unlink(missing_ok=True)
    print(json.dumps({'VOICE_DONE':locale,'seconds':result['audio_seconds'],'decoded_verified':duration['verified'],
                      'max_tempo':result['max_used_post_tempo'],'max_padding_seconds':result['max_cue_padding_seconds'],'mp3':mp3.name}),flush=True)
    return result

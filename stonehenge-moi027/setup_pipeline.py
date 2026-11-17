import json,shutil
from pathlib import Path
R=Path(__file__).parent;OLD=R.parent/'roman-concrete-moi022'
def adapt(s):
    for a,b in [('1282','1292'),('61536000','62016000'),('ROMAN_MOI022','STONEHENGE_MOI027'),('MOI-022','MOI-027'),('roman-concrete-moi-022-21m22s','stonehenge-moi-027-21m32s'),('roman-concrete-moi022','stonehenge-moi027'),('melo-roman022','melo-stone027'),('roman-moi022','stonehenge-moi027'),('21m22s','21m32s'),('21:22','21:32')]:s=s.replace(a,b)
    return s
for name in ['render_common.py','online_transport.py','render_english_groups.py','recover_english_group.py','render_online.py','request_adaptive.py','bootstrap_tool.py','ensure_ffmpeg.py','extract_content.py','english_gate.py','publish_documents.py','voice_gate.py','extract_voice_inputs.py','wait_for_english.py']:
    s=adapt((OLD/name).read_text())
    if name=='render_english_groups.py':s=s.replace('len(rows)==129','len(rows)==130')
    if name=='voice_gate.py':s=s.replace('else 129','else 130').replace('==129','==130')
    if name=='publish_documents.py':s=s.replace('Bê tông La Mã','Stonehenge').replace('TIMELINE_136','TIMELINE_137').replace('BACKUP_137_140','BACKUP_138_140')
    if name=='render_common.py':
        a=s.index('KEYWORDS=');b=s.index('LOCAL=threading.local()',a)
        keys={'en-US':['stone','route','evidence','source'],'vi-VN':['đá','tuyến','bằng chứng','nguồn'],'es-ES':['piedra','ruta','prueba'],'fr-FR':['pierre','trajet','preuve'],'ja-JP':['石','経路','証拠'],'ko-KR':['돌','경로','증거'],'de-DE':['Stein','Weg','Belege'],'it-IT':['pietra','percorso','prova'],'pt-PT':['pedra','percurso','prova'],'nl-NL':['steen','route','bewijs'],'pl-PL':['kamień','trasa','dowody'],'sv-SE':['sten','väg','bevis'],'da-DK':['sten','rute','beviser'],'fi-FI':['kivi','reitti','todiste'],'nb-NO':['stein','rute','bevis'],'cs-CZ':['kámen','trasa','důkazy']}
        s=s[:a]+'KEYWORDS='+repr(keys)+'\n'+s[b:]
    (R/name).write_text(s,encoding='utf-8')
profile=json.loads((OLD/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
profile.update(topic_id='MOI-027',target_seconds=1292,locked_from='productions/video-moi022-roman-concrete/VOICE_PROFILES_LOCKED.json',voice_changes=[],previous_voice_ids_retained=16)
(R/'VOICE_PROFILES_LOCKED_BASELINE.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(OLD/'MELO_SOURCE_LOCK.json',R/'MELO_SOURCE_LOCK.json')
print('STONEHENGE_PIPELINE_PREPARED')

"""Run the delivered ZIP on Windows, then reproduce/repair the original defect."""
import hashlib,json,shutil,subprocess,sys,urllib.request,uuid,zipfile
from pathlib import Path
from autodoc.common import save_json,digest
from autodoc.resources import validate_archive,VAD_ASSET,VAD_SHA256

R=Path(__file__).resolve().parent;release=R/'release';work=R/'delivery test'/uuid.uuid4().hex;work.mkdir(parents=True)
archive=release/'AutoDocStudio-2.2.1-Full-Windows-x64.zip';archive_check=validate_archive(archive);archive_sha=digest(archive)
with zipfile.ZipFile(archive) as z:z.extractall(work/'Full đã giải nén')
app=work/'Full đã giải nén/AutoDocStudio';exe=app/'AutoDocStudio.exe'
# The original dist tree must not accidentally supply a missing resource.
original=R/'dist/AutoDocStudio'
if original.exists():original.rename(R/'dist/AutoDocStudio.pre_package_disabled')

def call_app(program,args,result,ok=True):
    result=Path(result);proc=subprocess.run([str(program)]+[str(x) for x in args]+['--result-json',str(result)],timeout=300)
    if not result.is_file():raise RuntimeError('EXE did not write result JSON: '+str(result))
    data=json.loads(result.read_text(encoding='utf-8-sig'))
    if ok:assert proc.returncode==0 and data.get('status')!='failed',data
    else:assert proc.returncode!=0 and data.get('status')=='failed',data
    return data

doctor=work/'doctor.json';subprocess.run([str(exe),'--doctor','--doctor-output',str(doctor)],check=True,timeout=120)
d=json.loads(doctor.read_text(encoding='utf-8-sig'));assert d['status']=='ready' and d['vad']['onnx_inference_passed'] and d['vad']['sha256']==VAD_SHA256
assert Path(d['vad']['asset_path']).resolve().is_relative_to(app.resolve())
fixtures=R/'windows test/Nguồn thử nghiệm';media=fixtures/'Ảnh và video';english=fixtures/'Giọng Anh 21.wav'
settings=work/'settings.json';save_json(settings,{'language':'auto','whisper_model':'tiny','quality':'fast','resolution':720,'full_verify':True,'screen_minors':False})
def auto(program,voice,out,result,config=settings):
    return call_app(program,['--auto-edit','--voice',voice,'--media',media,'--output',out,'--settings',config],result)

en=auto(exe,english,work/'Phim Anh',work/'english.json');assert not en['asr_skipped'] and en['report']['audio_alignment']
vi_voice=R/'windows test/Đa ngôn ngữ/Giọng Viet_Nam.wav';vi_settings=work/'vi_settings.json';save_json(vi_settings,{'language':'auto','whisper_model':'base','quality':'fast','resolution':720,'full_verify':True,'screen_minors':False})
vi=auto(exe,vi_voice,work/'Phim Việt',work/'vietnamese.json',vi_settings);assert vi['report']['detected_language']=='vi' and vi['report']['visual_matching']=='translated_en' and vi['report']['audio_alignment']
gui=work/'gui.json';subprocess.run([str(exe),'--gui-smoke','--project',en['project'],'--gui-report',str(gui)],check=True,timeout=90);g=json.loads(gui.read_text(encoding='utf-8-sig'));assert g['status']=='passed' and g['preview_frame_displayed']

# Verify that the small repair ZIP fixes the exact already-shipped 2.2.0 app.
old_archive=work/'Original-2.2.0.zip';expected_old='4eeff285ec4983db3482a0eaeba1ee309c804038a035a935b77cc27cd6834faa'
url='https://github.com/seotro95/seotro/releases/download/autodoc-studio-v2.2.0/AutoDocStudio-2.2.0-Full-Windows-x64.zip';h=hashlib.sha256()
with urllib.request.urlopen(url,timeout=120) as response,old_archive.open('wb') as out:
    while True:
        b=response.read(1024*1024)
        if not b:break
        out.write(b);h.update(b)
assert h.hexdigest()==expected_old
old_folder=work/'Bản 2.2.0 cần vá'
with zipfile.ZipFile(old_archive) as z:z.extractall(old_folder)
old_app=old_folder/'AutoDocStudio';old_exe=old_app/'AutoDocStudio.exe';old_exe_sha=digest(old_exe)
assert not (old_app/'_internal/faster_whisper/assets'/VAD_ASSET).exists()
failed=call_app(old_exe,['--auto-edit','--voice',english,'--media',media,'--output',work/'Trước vá','--settings',settings],work/'before_repair.json',ok=False)
assert VAD_ASSET in failed['error'] and ('NO_SUCHFILE' in failed['error'] or 'File doesn\'t exist' in failed['error'])
repair=release/'SUA_LOI_VAD_2.2.0.zip'
with zipfile.ZipFile(repair) as z:
    assert z.testzip() is None;z.extractall(old_app)
assert digest(old_app/'_internal/faster_whisper/assets'/VAD_ASSET)==VAD_SHA256 and digest(old_exe)==old_exe_sha
repaired=auto(old_exe,english,work/'Sau vá',work/'after_repair.json');assert not repaired['asr_skipped'] and repaired['report']['audio_alignment']
report={'status':'passed','version':'2.2.1','tested_archive':archive.name,'tested_archive_sha256':archive_sha,'zip_checks':archive_check,'original_dist_tree_disabled_during_test':True,'vad_loaded_from_extracted_archive':True,'vad_onnx_inference_passed':True,'english_auto_edit_after_extraction_passed':True,'vietnamese_transcription_translation_export_after_extraction_passed':True,'extracted_app_gui_preview_passed':True,'old_release_missing_vad_reproduced':True,'small_patch_restored_original_2_2_0_auto_edit':True,'patch_did_not_modify_original_exe':True,'repair_archive':repair.name,'repair_archive_sha256':digest(repair),'source_audio_timing_verified':True}
save_json(release/'POST_PACKAGE_TEST_REPORT.json',report)
# Metadata finalization does not modify either ZIP that was actually tested.
assets=[]
for p in sorted(release.iterdir()):
    if p.is_file() and p.name not in ['SHA256SUMS.txt','RELEASE_MANIFEST.json']:assets.append({'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)})
manifest=release/'RELEASE_MANIFEST.json';m=json.loads(manifest.read_text(encoding='utf-8-sig'));m.update(post_package_test_passed=True,post_package_report='POST_PACKAGE_TEST_REPORT.json',assets=assets);save_json(manifest,m)
(release/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets),encoding='utf-8')
assert digest(archive)==archive_sha
print(json.dumps(report),flush=True)

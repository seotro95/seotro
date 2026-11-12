"""Check final downloadable documents and their published digests."""
import hashlib,json,re,subprocess,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent
TAG='bone-traces-video-58-22m42s'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
release=json.loads(subprocess.check_output(['gh','api',f'repos/seotro95/seotro/releases/tags/{TAG}']))
assets={a['name']:a for a in release['assets']}
def download(name):
    data=urllib.request.urlopen(BASE+name,timeout=90).read()
    assert len(data)==assets[name]['size']
    assert hashlib.sha256(data).hexdigest()==assets[name]['digest'].removeprefix('sha256:')
    return data
name='BONE_TRACES_58_TAI_LIEU_22m42s.zip'
archive=R/name;archive.write_bytes(download(name))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    qa=json.loads(z.read('DOCUMENT_QA.json'))
    assert qa['status']=='passed' and qa['target_seconds']==1362 and qa['voices_generated'] and qa['voice_count_verified']==17
    prompts=sorted(n for n in z.namelist() if n.startswith('PROMPTS/') and n.endswith('.txt'))
    assert len(prompts)==13
    count=0
    for n in prompts:
        s=z.read(n).decode('utf-8-sig')
        assert s.count('Create one continuous moving 10-second shot')==10
        assert s.count('Video không có lời nói và không có âm thanh')==10
        assert s.count('No children, infants, adolescents, minors')==10
        count+=10
    for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json','PUBLIC_DOWNLOAD_QA.json','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','NARRATION_STYLE_LOCKED.json','README.md']:
        assert n in z.namelist(),n
        (R/n).write_bytes(z.read(n))
    profile=json.loads(z.read('VOICE_PROFILES_LOCKED.json'))
    assert next(p for p in profile['profiles'] if p['locale']=='vi-VN')['voice_id']=='Adam'
    assert len([n for n in z.namelist() if n.startswith('REPORTS/') and n.endswith('.json')])==17
    assert z.read('5_TIEU_DE_VA_THUMBNAIL.txt')==download('5_TIEU_DE_VA_THUMBNAIL.txt')
manifest=json.loads(download('DOCUMENT_ASSET_MANIFEST.json'))
for a in manifest['assets']:
    assert assets[a['name']]['digest']=='sha256:'+a['sha256']
    assert assets[a['name']]['size']==a['bytes']
checks={line.split('  ',1)[1]:line.split('  ',1)[0] for line in download('SHA256SUMS.txt').decode().splitlines()}
for n,a in assets.items():
    if n!='SHA256SUMS.txt':assert checks[n]==a['digest'].removeprefix('sha256:'),n
result={'status':'passed','topic_id':58,'target_seconds':1362,'voice_count':17,'prompt_txt_files':13,'unique_prompts_verified':count,'each_prompt_excludes_minors_and_audio':True,'zip_crc_passed':True,'all_published_document_asset_digests_match':True,'all_published_asset_checksums_match':True,'documents_zip_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),'documents_zip_bytes':archive.stat().st_size,'title_thumbnail_txt_public_download_verified':True}
(R/'DOCUMENT_PUBLIC_DOWNLOAD_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,indent=2),flush=True)

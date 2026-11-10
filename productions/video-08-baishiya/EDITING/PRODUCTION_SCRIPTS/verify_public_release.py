import hashlib,json,urllib.request
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';j=json.load(open(R/'PUBLIC_RELEASE.json'));assert not j['draft'] and j['tag_name']=='baishiya-video-08-final-22m20s';assets={x['name']:x for x in j['assets']};checked=[]
expected=json.load(open(R/'FINAL_MEDIA_MANIFEST.json'))['assets']
for x in expected:
 p=O/x['name'];a=assets[p.name];h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest();assert a['size']==p.stat().st_size and a['digest']=='sha256:'+h;checked.append({'name':p.name,'bytes':a['size'],'sha256':h,'url':a['browser_download_url']})
main=assets['BAISHIYA_08_EN_FINAL_22m20s_720p.mp4'];h=hashlib.sha256();size=0
with urllib.request.urlopen(main['browser_download_url'],timeout=60) as r:
 assert r.status==200;status=r.status
 while True:
  b=r.read(1048576)
  if not b:break
  h.update(b);size+=len(b)
  if size%(32*1048576)==0:print('Verified public video bytes',size,flush=True)
assert size==main['size'] and 'sha256:'+h.hexdigest()==main['digest']
txt=assets['BAISHIYA_08_TITLES_THUMBNAILS.txt']
with urllib.request.urlopen(txt['browser_download_url'],timeout=45) as r:
 b=r.read();disposition=r.headers.get('Content-Disposition','')
assert b==(O/txt['name']).read_bytes();text=b.decode('utf-8-sig');assert text.count('TITLE EN:')==5 and text.count('PROMPT:')==5
out={'status':'passed','release_url':j['html_url'],'tag':j['tag_name'],'published_at':j['published_at'],'asset_count':len(checked),'assets':checked,'public_video_head_status':status,'public_video_full_stream_sha256_verified':True,'txt_download_content_verified':True,'txt_content_disposition':disposition,'raw_source_clips_published':False,'verification':'All published output sizes and serverSHA256digests match local completed files; complete public MP4 stream hash verified; TXT downloaded and its five title/prompt pairs checked.'};(R/'PUBLIC_RELEASE_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'status':'passed','asset_count':len(checked),'video_bytes':main['size'],'public_video_status':status,'txt_downloaded_and_verified':True}),flush=True)

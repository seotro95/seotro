import hashlib,json,urllib.request
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';j=json.loads((R/'PUBLIC_RELEASE.json').read_text())
assert not j['draft'] and j['tag_name']=='yana-video-04-final-23min'
assets={x['name']:x for x in j['assets']};checked=[]
for p in sorted(O.iterdir()):
 if not p.is_file():continue
 a=assets[p.name];h=hashlib.sha256(p.read_bytes()).hexdigest()
 assert a['size']==p.stat().st_size,(p.name,'size')
 assert a['digest']=='sha256:'+h,(p.name,a.get('digest'))
 checked.append({'name':p.name,'bytes':a['size'],'sha256':h,'url':a['browser_download_url']})
main=assets['YANA_04_EN_FINAL_23m_720p.mp4']
req=urllib.request.Request(main['browser_download_url'],method='HEAD',headers={'User-Agent':'Yana-Delivery-QA'})
with urllib.request.urlopen(req,timeout=45) as r:
 assert r.status==200,r.status
 n=r.headers.get('Content-Length')
 if n:assert int(n)==main['size']
 status=r.status
out={'status':'passed','release_url':j['html_url'],'tag':j['tag_name'],'published_at':j['published_at'],'asset_count':len(checked),'assets':checked,'public_video_head_status':status,'verification':'Public release asset sizes and server SHA256 digests match local finished files; final MP4 download returns HTTP 200.'}
(R/'PUBLIC_RELEASE_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'status':'passed','asset_count':len(checked),'video_bytes':main['size'],'public_video_status':status}),flush=True)

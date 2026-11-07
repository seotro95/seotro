"""Restore authenticated encrypted edit components, mux and verify the deliverable."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64,hashlib,json,re,subprocess,tempfile,time

BASE=Path(__file__).resolve().parent
manifest=json.loads((BASE/'final-video-export/encrypted-components.json').read_text())
REPO=manifest['repo'];OUT=Path('siberia-final-delivery');OUT.mkdir(exist_ok=True)
def api(route,method='GET',body=None):
 cmd=['gh','api',route]
 if method!='GET':cmd+=['--method',method]
 with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
  if body is not None:json.dump(body,f,ensure_ascii=False);f.flush();cmd+=['--input',f.name]
  for attempt in range(4):
   p=subprocess.run(cmd,capture_output=True,text=True)
   if p.returncode==0:return json.loads(p.stdout)
   if attempt==3:raise RuntimeError(p.stderr[-1600:])
   time.sleep(3*2**attempt)
release=api('repos/'+REPO+'/releases/'+str(manifest['draft_release_id']))
match=re.search(r'SIBERIA_TRANSFER_KEY_BASE64=([A-Za-z0-9+/=]+)',release['body'])
if not match:raise RuntimeError('The private transfer key is unavailable; no data was decoded.')
key=base64.b64decode(match[1]);assert len(key)==32
cipher=AESGCM(key)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def fetch(part,name):
 blob=api('repos/'+REPO+'/git/blobs/'+part['blob_sha'])
 data=cipher.decrypt(base64.b64decode(part['nonce_base64']),base64.b64decode(blob['content']),f"{name}:{part['offset']}".encode())
 assert len(data)==part['plaintext_bytes'];return data
with ThreadPoolExecutor(max_workers=6) as pool:
 for component in manifest['files']:
  name=component['name'];relative=Path(name)
  assert not relative.is_absolute() and '..' not in relative.parts
  p=OUT/relative;p.parent.mkdir(parents=True,exist_ok=True)
  futures=[pool.submit(fetch,part,name) for part in component['chunks']]
  with p.open('wb') as f:
   for result in futures:f.write(result.result())
  assert p.stat().st_size==component['bytes'] and digest(p)==component['sha256'],name
  print('Verified component: '+name,flush=True)

def run(args,capture=False):
 return subprocess.run(args,check=True,capture_output=capture,text=capture)
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(p)],True).stdout)
listing=OUT/'segments/concat.txt';listing.write_text(''.join(f"file '{i:04}.mp4'\n" for i in range(1,185)))
video=OUT/manifest['video_filename']
run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','1','-i',str(listing),'-i',str(OUT/'audio/EN_FINAL_AAC.m4a'),'-i',str(OUT/'EN_SUBTITLES_25m36.srt'),'-i',str(OUT/'chapters.ffmeta'),'-map','0:v:0','-map','1:a:0','-map','2:0','-map_metadata','3','-map_chapters','3','-c:v','copy','-c:a','copy','-c:s','mov_text','-metadata:s:a:0','language=eng','-metadata:s:s:0','language=eng','-metadata:s:s:0','title=English narration','-disposition:s:0','0','-t','1536','-movflags','+faststart',str(video)])
info=probe(video);v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
assert int(v['nb_frames'])==46080 and v['avg_frame_rate']=='30/1' and [v['width'],v['height']]==[1280,720]
assert abs(float(info['format']['duration'])-1536)<.001 and abs(float(a['duration'])-1536)<.001
assert abs(float(v.get('start_time',0)))<.001 and abs(float(a.get('start_time',0)))<.001
assert len(info['chapters'])==13
def packet_hash(inputs,selector):
 args=['ffmpeg','-hide_banner','-loglevel','error',*inputs,'-map',selector,'-c','copy']
 if ':v:' in selector:args+=['-bsf:v','h264_mp4toannexb']
 return run([*args,'-f','hash','-hash','sha256','-'],True).stdout.strip()
source_v=packet_hash(['-f','concat','-safe','1','-i',str(listing)],'0:v:0');final_v=packet_hash(['-i',str(video)],'0:v:0')
source_a=packet_hash(['-i',str(OUT/'audio/EN_FINAL_AAC.m4a')],'0:a:0');final_a=packet_hash(['-i',str(video)],'0:a:0')
assert source_v==final_v and source_a==final_a,'Muxing changed compressed audio or picture data'
print('Checking complete video decode and final audio loudness...',flush=True)
decode=run(['ffmpeg','-hide_banner','-nostats','-xerror','-err_detect','explode','-threads','2','-i',str(video),'-map','0:v:0','-map','0:a:0','-filter_threads','2','-af','ebur128=peak=true','-f','null','-'],True)
summary=decode.stderr[decode.stderr.rfind('Summary:'):]
(OUT/'FINAL_AUDIO_MEASUREMENT.txt').write_text(summary+'\n')
loudness=re.findall(r'I:\s*(-?[\d.]+) LUFS',summary);assert loudness and -17.5<float(loudness[-1])<-14.5
report=json.loads((OUT/'FINAL_VIDEO_QA.json').read_text());report['local_container_sha256']=report['sha256'];report.update(
 sha256=digest(video),bytes=video.stat().st_size,full_video_and_audio_decode_passed=True,
 authenticated_component_hashes_verified=True,compressed_video_preserved_during_export=True,
 compressed_audio_preserved_during_export=True,video_packet_hash=final_v,audio_packet_hash=final_a,
 integrated_lufs=float(loudness[-1]),video_start_seconds=float(v.get('start_time',0)),audio_start_seconds=float(a.get('start_time',0)),
 export_note='Final container remuxed from authenticated local edit components; no audio or picture re-encoding during transfer.')
(OUT/'FINAL_VIDEO_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
deliver=[video,OUT/'EN_SUBTITLES_25m36.srt',OUT/'FINAL_VIDEO_QA.json',OUT/'FINAL_EDIT_TIMELINE.csv',OUT/'VIDEO_README_VI.md',OUT/'FINAL_AUDIO_MEASUREMENT.txt']
checks=OUT/'VIDEO_SHA256SUMS.txt';checks.write_text(''.join(digest(p)+'  '+p.name+'\n' for p in deliver));deliver.append(checks)
run(['gh','release','upload',manifest['release_tag'],*[str(p) for p in deliver],'--repo',REPO,'--clobber'])
notes='''Video Siberia tiếng Anh hoàn chỉnh, 25:36, 1280×720, 30 fps.\n\nTải Siberia_EN_FINAL_25m36_720p.mp4 để xem. Có chương điều hướng và phụ đề Anh mặc định tắt. Voice giữ nguyên tốc độ và mốc thời gian của bản đã chốt.\n\nBản dựng dùng clip Muse đã gửi, một số cảnh được dùng lại và bổ sung sơ đồ có nhãn cho phần thiếu hoặc hình không khớp lời. Chi tiết trong VIDEO_README_VI.md và FINAL_EDIT_TIMELINE.csv.\n\nĐã kiểm tra đủ 46.080 frame, giải mã toàn bộ video/âm thanh và kiểm tra SHA-256. Bản nháp dành cho chủ kho seotro95; cần đăng nhập tài khoản này để tải.\n'''
api('repos/'+REPO+'/releases/'+str(manifest['draft_release_id']),'PATCH',{'body':notes})
print(json.dumps({'completed':True,'release_id':manifest['draft_release_id'],'file':video.name,'sha256':report['sha256'],'bytes':report['bytes'],'seconds':1536,'frames':46080}),flush=True)

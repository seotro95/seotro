"""Verify the actual uploaded asset hashes against the measured WAV reports."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,html,json,os,subprocess

LANGUAGES={'en':'Tiếng Anh','vi':'Việt Nam','es':'Tây Ban Nha','fr':'Pháp','ja':'Nhật Bản','ko':'Hàn Quốc','de':'Đức','it':'Ý','pt':'Bồ Đào Nha','nl':'Hà Lan','pl':'Ba Lan','sv':'Thụy Điển','da':'Đan Mạch','fi':'Phần Lan','no':'Na Uy','cs':'Séc','hi':'Hindi'}

def verify(root,required=False):
 base=Path(__file__).resolve().parent;root=Path(root);root.mkdir(parents=True,exist_ok=True)
 def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout
 repo=os.environ['GITHUB_REPOSITORY'];tag='siberia-2536-production-v1'
 data=json.loads(run(['gh','api','repos/'+repo+'/releases/436895553']))
 assets={a['name']:a for a in data['assets']}
 run(['gh','release','download',tag,'--repo',repo,'--pattern','*-report.json','--pattern','*.srt','--pattern','*.txt','--dir',str(root),'--clobber'])
 master=json.loads((base/'master_timeline.json').read_text());curation_sha=hashlib.sha256((base/'curated_cues.json').read_bytes()).hexdigest()
 tracks=[];missing=[]
 for code,name in LANGUAGES.items():
  names=[code+s for s in ['.wav','.mp3','.srt','-report.json']]
  if any(n not in assets for n in names):missing.append(code);continue
  r=json.loads((root/(code+'-report.json')).read_text())
  current=code=='en' or r.get('text_review',{}).get('curation_sha256')==curation_sha
  current=current and (code in {'en','vi'} or r.get('text_review',{}).get('translation_status','').startswith('Public web translation'))
  if not current:missing.append(code);continue
  assert r['version']=='1.3.1' and r['duration_verified'] and r['sync_ok'],code
  assert r['language']=={'ja':'JP','ko':'KR'}.get(code,code.upper()),(code,'language metadata')
  assert r['duration_report']['sample_frames']==73728000 and r['sample_rate']==48000 and r['audio_seconds']==1536,code
  assert r['sync_report']['error_frames']==0,code
  cues=r['sync_report']['cues'];assert len(cues)==59,code
  for a,b in zip(cues,master['cues']):
   assert a['start_frame']==b['start_ms']*48 and a['end_frame']==b['end_ms']*48,(code,b['id'])
  assert assets[code+'.wav']['digest']=='sha256:'+r['audio_sha256'],(code,'uploaded WAV hash')
  srt_hash=hashlib.sha256((root/(code+'.srt')).read_bytes()).hexdigest()
  assert assets[code+'.srt']['digest']=='sha256:'+srt_hash,(code,'uploaded SRT hash')
  maximum_padding=max(c['padding_frames']/48000 for c in cues)
  if maximum_padding>2:missing.append(code);continue
  tracks.append({'code':code,'language':name,'seconds':1536,'samples':73728000,'sample_rate':48000,
   'shared_cues_verified':59,'cue_boundary_error_samples':0,'maximum_cue_end_padding_seconds':maximum_padding,
   'wav_sha256':r['audio_sha256'],'voice':r['selected_voice_metadata'],
   'wav_url':assets[code+'.wav']['browser_download_url'],'mp3_url':assets[code+'.mp3']['browser_download_url'],
   'srt_url':assets[code+'.srt']['browser_download_url']})
 assert len({t['wav_sha256'] for t in tracks})==len(tracks),'Different language tracks must not be the same audio under different labels'
 if required and missing:raise RuntimeError('Tracks not finalized: '+', '.join(missing))
 report={'verified_utc':datetime.now(timezone.utc).isoformat(),'scope':'Technical timing, sample counts and asset hashes; not a certification of native pronunciation or translation style',
  'target_seconds':1536,'target_samples':73728000,'sample_rate':48000,'all_17_verified':len(tracks)==17,
  'verified_languages':len(tracks),'remaining_languages':missing,'tracks':tracks,'finished_muse_video_included':False}
 (root/'VOICE_TIMING_VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 page=data['html_url']
 text='# Tải các bản giọng 25:36\n\nĐăng nhập tài khoản chủ kho seotro95 rồi mở [GitHub Releases]('+page+'). Bản nháp chưa được công bố công khai.\n\nWAV để ghép vào video, MP3 để nghe. Các tệp dưới đây đã kiểm tra cùng 59 mốc đoạn, cùng 73.728.000 mẫu ở 48 kHz.\n\n| Ngôn ngữ | WAV | MP3 | Mốc đoạn |\n|---|---|---|---|\n'
 for t in tracks:text+='| '+t['language']+' | [Tải WAV]('+t['wav_url']+') | [Tải MP3]('+t['mp3_url']+') | [SRT]('+t['srt_url']+') |\n'
 if missing:text+='\nChưa chốt: '+', '.join(missing)+'.\n'
 text+='\nGiọng tổng hợp từ Melo + Việt Studio 1.3.1; không nhân bản người đọc gốc. Kiểm tra kỹ thuật không thay thế việc nghe duyệt phát âm và bản dịch. Chưa có MP4 Muse hoàn chỉnh trong bộ tải này.\n'
 (root/'TAI_CAC_GIONG.md').write_text(text,encoding='utf-8')
 rows=''.join('<tr><td>'+html.escape(t['language'])+'</td>'+''.join('<td><a href="'+html.escape(t[key],quote=True)+'" target="_blank" rel="noopener">'+label+'</a></td>' for key,label in [('wav_url','Tải WAV'),('mp3_url','Tải MP3'),('srt_url','Tải SRT')])+'</tr>' for t in tracks)
 page_html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tải giọng đọc Siberia 25:36</title><style>body{font:16px system-ui,sans-serif;max-width:940px;margin:40px auto;padding:0 20px;color:#172d40;background:#f4f7fa}main{padding:28px;background:white;border-radius:18px}h1{font-size:27px;margin:0 0 16px}p{line-height:1.6}table{width:100%;border-collapse:collapse}td,th{padding:14px 8px;text-align:left;border-bottom:1px solid #dde4eb}a{color:#0755aa;font-weight:600}th{font-size:14px;color:#536576}.status{color:#176738;font-weight:600}.note{font-size:14px;color:#526274}footer{margin-top:25px;line-height:1.6}</style><main><h1>Các bản giọng Siberia · 25:36</h1>'''
 page_html+='<p class="status">'+str(len(tracks))+'/17 ngôn ngữ đã kiểm tra đồng bộ.</p><p>Đăng nhập GitHub bằng tài khoản chủ kho <strong>seotro95</strong>, rồi chọn giọng cần tải. WAV dùng để ghép vào video; MP3 dùng để nghe thử.</p><table><thead><tr><th>Ngôn ngữ</th><th>WAV · 48 kHz</th><th>MP3</th><th>Mốc đoạn</th></tr></thead><tbody>'+rows+'</tbody></table>'
 page_html+='<footer><a href="'+html.escape(page,quote=True)+'" target="_blank" rel="noopener">Mở bản nháp trên GitHub Releases</a><p class="note">Các WAV có cùng thời lượng và cùng 59 mốc đoạn. Giọng tổng hợp từ Melo + Việt Studio 1.3.1. Hãy nghe duyệt phát âm và bản dịch trước khi phát hành. MP4 hoàn chỉnh được tạo sau khi chạy Muse và bước dựng trên máy Windows của bạn.</p></footer></main></html>'
 (root/'TAI_CAC_GIONG.html').write_text(page_html,encoding='utf-8')
 return report

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',default='delivery-verification');p.add_argument('--require-all',action='store_true');args=p.parse_args()
 print(json.dumps(verify(args.directory,args.require_all),ensure_ascii=False,indent=2))

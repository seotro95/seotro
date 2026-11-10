import collections,concurrent.futures,hashlib,json,re,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent
for n in ['frames','review','graphics','overlays','delivery']:(R/n).mkdir(exist_ok=True)
receipts=json.load(open(R/'DOWNLOAD_RECEIPTS.json'))['files'];assert len(receipts)==104
starts=[518,528,538,548,558,568,577,587,597,604,613];prompts={x['clip_id']:x for x in json.load(open(R.parent/'package/UNIQUE_PROMPTS_110.json'))}
items=[]
for x in receipts:
 p=Path(x['path']);assert p.exists() and p.stat().st_size==x['size_bytes'];num=int(x['number']);group=max(i for i,start in enumerate(starts) if num>=start);scene=int(re.search(r'scene-(\d+)',p.name)[1]);cid=group*10+scene
 items.append(dict(x,number=num,label=f'DE06_{cid:03d}',clip_id=cid,source_name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),expected_kind=prompts[cid]['kind'],expected_scene=prompts[cid]['scene_and_camera']))
def inspect(x):
 p=Path(x['path']);j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]));frames=[]
 for n,t in enumerate([.8,4.9,9.1],1):
  out=R/'frames'/f"{x['label']}_{n}.jpg";subprocess.run(['ffmpeg','-v','error','-threads','1','-ss',str(t),'-i',str(p),'-frames:v','1','-vf','scale=320:180','-threads','1','-y',str(out)],check=True);frames.append(str(out))
 return dict(x,streams=j['streams'],format=j['format'],frames=frames)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 final=[]
 for n,x in enumerate(pool.map(inspect,items),1):
  final.append(x)
  if n%10==0:print(json.dumps({'clips_inspected':n,'total':104}),flush=True)
items=sorted(final,key=lambda x:x['clip_id']);assert len({x['clip_id'] for x in items})==104;(R/'inventory.json').write_text(json.dumps(items,ensure_ascii=False,indent=2))
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
for start in range(0,len(items),8):
 group=items[start:start+8];im=Image.new('RGB',(960,len(group)*212),'#101923');d=ImageDraw.Draw(im)
 for n,x in enumerate(group):
  for col,p in enumerate(x['frames']):im.paste(Image.open(p),(col*320,n*212+28))
  d.text((8,n*212+5),f"{x['label']}  | source {x['number']} | {x['expected_kind']} | 0.8s / 4.9s / 9.1s",font=font,fill='white')
 im.save(R/'review'/f'CONTACT_{start//8+1:02d}.jpg',quality=89)
videos=[next(s for s in x['streams'] if s['codec_type']=='video') for x in items];groups=collections.defaultdict(list)
for x in items:groups[x['sha256']].append(x['label'])
summary=dict(uploaded_files=104,unique_checksums=len(groups),exact_duplicates=[v for v in groups.values() if len(v)>1],source_bytes=sum(x['size_bytes'] for x in items),audio_sources=sum(any(s['codec_type']=='audio' for s in x['streams']) for x in items),resolutions=sorted(set((v['width'],v['height']) for v in videos)),durations=sorted(set(float(x['format']['duration']) for x in items)),missing_prompt_ids=sorted(set(range(1,111))-{x['clip_id'] for x in items}))
(R/'INVENTORY_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

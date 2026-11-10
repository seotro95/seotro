import collections,concurrent.futures,hashlib,json,re,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent
for n in ['frames','review','delivery','graphics','overlays','scenes']:(R/n).mkdir(exist_ok=True)
receipts=json.loads((R/'DOWNLOAD_RECEIPTS.json').read_text());unique={};duplicates=[]
starts=[403,413,423,433,443,452,462,472,482,490,499,509]
for x in receipts:
 p=Path(x['path']);assert p.exists() and p.stat().st_size==x['size_bytes']
 digest=hashlib.sha256(p.read_bytes()).hexdigest()
 if digest in unique:duplicates.append({'duplicate_path':str(p),'same_as':unique[digest]['path'],'sha256':digest});continue
 number=int(x['number']);label=f'V{number}'
 if any(v['label']==label for v in unique.values()):label+='b'
 group=max(i for i,start in enumerate(starts) if number>=start)
 scene=int(re.search(r'scene-(\d+)',p.name)[1]);prompt=group*10+scene
 unique[digest]=dict(x,label=label,name=p.name,sha256=digest,inferred_prompt_id=prompt,original_scene_suffix=scene)
def inspect(x):
 p=Path(x['path']);j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
 out=R/'frames'/(x['label']+'.jpg')
 subprocess.run(['ffmpeg','-v','error','-threads','1','-ss','4','-i',str(p),'-frames:v','1','-vf','scale=384:216','-threads','1','-y',str(out)],check=True)
 return dict(x,streams=j['streams'],format=j['format'],frame=str(out))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:items=list(pool.map(inspect,unique.values()))
items.sort(key=lambda x:(x['number'],x['label']));(R/'inventory.json').write_text(json.dumps(items,ensure_ascii=False,indent=2));(R/'DUPLICATES.json').write_text(json.dumps(duplicates,indent=2))
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
for start in range(0,len(items),20):
 group=items[start:start+20];im=Image.new('RGB',(1536,1200),'#101923');d=ImageDraw.Draw(im)
 for n,x in enumerate(group):
  px=(n%4)*384;py=(n//4)*240;im.paste(Image.open(x['frame']),(px,py));d.text((px+8,py+218),f"{x['label']}  /  candidate YA04_{x['inferred_prompt_id']:03d}",font=font,fill='white')
 im.save(R/'review'/f'CONTACT_{start//20+1:02d}.jpg',quality=92)
videos=[next(s for s in x['streams'] if s['codec_type']=='video') for x in items]
summary=dict(uploaded_files=len(receipts),unique_clips=len(items),exact_duplicates=len(duplicates),source_bytes=sum(x['size_bytes'] for x in items),audio_sources=sum(any(s['codec_type']=='audio' for s in x['streams']) for x in items),resolutions=sorted(set((v['width'],v['height']) for v in videos)),durations=sorted(set(float(x['format']['duration']) for x in items)),missing_candidate_prompt_ids=sorted(set(range(1,121))-{x['inferred_prompt_id'] for x in items}))
(R/'INVENTORY_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

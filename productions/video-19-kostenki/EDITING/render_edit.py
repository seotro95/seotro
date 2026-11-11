import argparse,concurrent.futures,hashlib,json,os,subprocess
from pathlib import Path
R=Path(__file__).parent;S=R/'scenes';S.mkdir(exist_ok=True)
plan=json.loads((R/'EDIT_PLAN.json').read_text())
def render(item):
 out=S/f"{item['cue']:03d}.mp4";stamp=out.with_suffix('.sha256');sig=hashlib.sha256(json.dumps(item,sort_keys=True).encode()+Path(__file__).read_bytes()).hexdigest()
 if out.exists() and stamp.exists() and stamp.read_text()==sig:return item['cue'],'cached'
 out.unlink(missing_ok=True)
 segs=item['segments'];a=segs[0]
 if len(segs)==1 and a['duration']==10 and a['source_in']==0 and a['crop']==1 and a['clip_id'] not in [11,51,60] and not item.get('fade_out_seconds'):
  os.link(R/'sources'/f"{a['label']}.mp4",out);stamp.write_text(sig);return item['cue'],'full silent shot reused without another encoding'
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','1','-y'];filters=[]
 for i,s in enumerate(segs):
  cmd+=['-threads','1','-ss',str(s['source_in']),'-i',str(R/'sources'/f"{s['label']}.mp4")]
  vf=f"trim=duration={s['duration']},setpts=PTS-STARTPTS,fps=24"
  if s['clip_id'] in [11,51,60]:vf+=',crop=1172:660:54:0,scale=1280:720:flags=lanczos'
  if s['crop']>1:
   w=int(1280/s['crop'])//2*2;h=int(720/s['crop'])//2*2;vf+=f',crop={w}:{h},scale=1280:720:flags=lanczos'
  filters.append(f'[{i}:v]{vf},setsar=1,format=yuv420p,settb=AVTB[v{i}]')
 stage='v0'
 if len(segs)>1:
  if item['transition']=='dissolve':filters.append('[v0][v1]xfade=transition=fade:duration=0.4:offset=4.8[j]')
  else:filters.append(''.join(f'[v{i}]' for i in range(len(segs)))+f'concat=n={len(segs)}:v=1:a=0[j]')
  stage='j'
 if item['cue']==1:
  filters.append(f"[{stage}]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='ILLUSTRATIVE RECONSTRUCTIONS':fontsize=13:fontcolor=white@0.7:x=24:y=h-32:box=1:boxcolor=black@0.3:boxborderw=4[l]");stage='l'
 if item.get('fade_out_seconds'):
  filters.append(f"[{stage}]fade=t=out:st={item['duration']-item['fade_out_seconds']}:d={item['fade_out_seconds']}[f]");stage='f'
 filters.append(f"[{stage}]trim=duration={item['duration']},setpts=PTS-STARTPTS,format=yuv420p[final]")
 cmd+=['-filter_complex',';'.join(filters),'-map','[final]','-an','-frames:v',str(round(item['duration']*24)),'-r','24','-c:v','libx264','-preset','fast','-crf','20','-maxrate','2200k','-bufsize','4400k','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
 log=out.with_suffix('.log')
 with log.open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(log.read_text())
 stamp.write_text(sig);return item['cue'],'rendered'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=2);p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=122);a=p.parse_args()
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
  for cue,status in ex.map(render,[x for x in plan if a.start<=x['cue']<=a.end]):print(json.dumps({'cue':cue,'status':status}),flush=True)
 (R/'concat.txt').write_text(''.join(f"file '{(S/f'{i:03d}.mp4').as_posix()}'\n" for i in range(1,123)))

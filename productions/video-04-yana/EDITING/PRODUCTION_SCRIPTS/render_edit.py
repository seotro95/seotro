import argparse,concurrent.futures,csv,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).parent
RENDERS=ROOT/'scenes';OVERLAYS=ROOT/'overlays';DELIVERY=ROOT/'delivery'
assets={x['label']:x for x in json.loads((ROOT/'inventory.json').read_text())}
plan=json.loads((ROOT/'EDIT_PLAN.json').read_text())
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def render(item):
    cue=item['cue'];output=RENDERS/f'{cue:03d}.mp4';log=RENDERS/f'{cue:03d}.log'
    signature_inputs={'item':item,'pipeline_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'visual_asset_hashes':[]}
    for asset in item['segments']:
        label=asset['label']
        digest=hashlib.sha256((ROOT/'graphics'/f'{label[1:]}.png').read_bytes()).hexdigest() if label.startswith('@') else assets[label]['sha256']
        signature_inputs['visual_asset_hashes'].append(digest)
    for key in ['chapter_overlay','lower_overlay']:
        if item[key]:signature_inputs['visual_asset_hashes'].append(hashlib.sha256(Path(item[key]).read_bytes()).hexdigest())
    signature=hashlib.sha256(json.dumps(signature_inputs,sort_keys=True).encode()).hexdigest()
    stamp=RENDERS/f'{cue:03d}.sha256'
    if output.exists() and stamp.exists() and stamp.read_text()==signature:return cue,'cached'
    cmd=['ffmpeg','-hide_banner','-loglevel','warning','-filter_complex_threads','1','-y']
    filters=[]
    for n,s in enumerate(item['segments']):
        if s['label'].startswith('@'):
            path=ROOT/'graphics'/f"{s['label'][1:]}.png"
            cmd+=['-loop','1','-framerate','24','-t',str(s['duration']+.1),'-i',str(path)]
            vf=f'trim=duration={s["duration"]},setpts=PTS-STARTPTS,fps=24,setsar=1,format=yuv420p'
        else:
            path=assets[s['label']]['path']
            cmd+=['-threads','1','-ss',str(s['source_in']),'-t',str(s['duration']),'-i',path]
            vf=f'trim=duration={s["duration"]},setpts=PTS-STARTPTS,fps=24'
            if s['crop']>1:
                w=int(1280/s['crop'])//2*2;h=int(720/s['crop'])//2*2
                vf+=f',crop={w}:{h},scale=1280:720:flags=lanczos'
            vf+=',setsar=1,eq=contrast=1.015:brightness=0.004:saturation=0.965,format=yuv420p'
        filters.append(f'[{n}:v]{vf}[v{n}]')
    count=len(item['segments'])
    if count==1:stage='v0'
    elif item['transition']=='dissolve':
        filters.append('[v0][v1]xfade=transition=fade:duration=0.6:offset=4.7,trim=duration=10,setpts=PTS-STARTPTS[joined]');stage='joined'
    else:
        filters.append(''.join(f'[v{n}]' for n in range(count))+f'concat=n={count}:v=1:a=0[joined]');stage='joined'
    next_input=count
    for key,delay,hold in [('chapter_overlay',.5,6.3 if cue==1 else 4.8),('lower_overlay',1.1,6.9)]:
        if item[key]:
            cmd+=['-loop','1','-framerate','24','-t','10','-i',item[key]]
            ol=f'ol{next_input}';out=f'out{next_input}'
            filters.append(f'[{next_input}:v]format=rgba,fade=t=in:st={delay}:d=0.35:alpha=1,fade=t=out:st={hold}:d=0.45:alpha=1[{ol}]')
            filters.append(f'[{stage}][{ol}]overlay=0:0:shortest=1[{out}]');stage=out;next_input+=1
    # Small, consistent provenance label, kept separate from the explanatory captions.
    filters.append(f'[{stage}]drawtext=fontfile={font_path}:text=ILLUSTRATIVE\\ VISUALS:fontsize=10:fontcolor=white@0.56:x=w-tw-24:y=h-17:box=1:boxcolor=black@0.22:boxborderw=4[labeled]')
    stage='labeled'
    if cue==138:
        filters.append('[labeled]fade=t=out:st=9.1:d=0.9[ending]');stage='ending'
    filters.append(f'[{stage}]trim=duration=10,setpts=PTS-STARTPTS,format=yuv420p[final]')
    cmd+=['-filter_complex',';'.join(filters),'-map','[final]','-an','-frames:v','240','-r','24',
          '-c:v','libx264','-preset','veryfast','-crf','21','-threads','1','-pix_fmt','yuv420p',
          '-g','48','-keyint_min','24','-movflags','+faststart',str(output)]
    (RENDERS/f'{cue:03d}.command.json').write_text(json.dumps(cmd))
    with log.open('w') as f:
        result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Cue {cue}: '+log.read_text()[-2000:])
    stamp.write_text(signature)
    return cue,'rendered'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=138);ap.add_argument('--workers',type=int,default=2)
    args=ap.parse_args();work=[p for p in plan if args.start<=p['cue']<=args.end]
    started=time.time();done=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for cue,status in pool.map(render,work):
            done+=1
            print(json.dumps({'cue':cue,'status':status,'done':done,'total':len(work),'elapsed_seconds':round(time.time()-started)}),flush=True)
    concat=ROOT/'concat.txt'
    concat.write_text(''.join(f"file '{(RENDERS/f'{i:03d}.mp4').as_posix()}'\n" for i in range(1,139)))
    print('Render stage complete',flush=True)

if __name__=='__main__':main()

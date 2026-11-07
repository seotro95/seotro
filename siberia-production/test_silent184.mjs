/** Real media check: remove sound and prove the compressed video packets survived. */
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const packageRoot=path.resolve(process.argv[2]);
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'silent184-'));const input=path.join(temp,'in');const output=path.join(temp,'out');await fs.mkdir(input);
function run(exe,args){const r=spawnSync(exe,args,{encoding:'utf8'});if(r.status!==0)throw Error(r.stderr||r.stdout);return r.stdout;}
try{
 const src=path.join(input,'0001.mp4');
 run('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','3','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-c:a','aac',src]);
 run(process.execPath,[path.join(packageRoot,'silence_clips.mjs'),input,output]);
 const dst=path.join(output,'0001.mp4');
 const meta=p=>JSON.parse(run('ffprobe',['-v','error','-count_frames','-show_streams','-of','json',p]));
 const a=meta(src),b=meta(dst);
 if(!a.streams.some(s=>s.codec_type==='audio')||b.streams.some(s=>s.codec_type==='audio'))throw Error('Fixture/result audio expectation failed');
 const va=a.streams.find(s=>s.codec_type==='video'),vb=b.streams.find(s=>s.codec_type==='video');
 if(va.nb_read_frames!=='90'||vb.nb_read_frames!=='90')throw Error('Video frame count changed');
 const rawHash=p=>createHash('sha256').update(run('ffmpeg',['-v','error','-i',p,'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-'])).digest('hex');
 if(rawHash(src)!==rawHash(dst))throw Error('Compressed video packet content changed');
 run(process.execPath,[path.join(packageRoot,'silence_clips.mjs'),input,output]);
 console.log(JSON.stringify({test:'silent184 media removal',passed:true,audio_streams_before:1,audio_streams_after:0,video_frames:90,compressed_video_preserved:true,verified_rerun:true}));
}finally{await fs.rm(temp,{recursive:true,force:true});}

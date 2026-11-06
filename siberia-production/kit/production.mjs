/** Local production helper for the owner's running Muse AI Studio 1.6.0.
 * Uses only its documented loopback routes. No login data is read or exported.
 * Node 22+ or the unmodified bundled Muse Electron runtime is sufficient.
 */
import fs from 'node:fs/promises';
import { existsSync, createReadStream, createWriteStream } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

export const ROOT = path.dirname(fileURLToPath(import.meta.url));
const argument = (name, fallback) => { const i=process.argv.indexOf(name); return i<0?fallback:process.argv[i+1]; };
const fps=30;
const toolVersion={url:'https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-11-06-12-50/ffmpeg-N-128532-g5d85b7bfb2-win64-gpl.zip',
 sha256:'b027eb661954382e86a29ea8b04b4944b32bb66fa029006823acbd058cf4bbda'};
const idFile=id=>String(id).padStart(4,'0');
const json=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const save=async (p,v)=>{ await fs.mkdir(path.dirname(p),{recursive:true}); await fs.writeFile(p+'.tmp',JSON.stringify(v,null,2),'utf8'); await fs.rename(p+'.tmp',p); };
export async function digest(p) { const h=createHash('sha256'); for await (const b of createReadStream(p)) h.update(b); return h.digest('hex'); }

export function validatePlan(plan) {
 if(plan.fps!==30||!Array.isArray(plan.shots)||!plan.shots.length)throw Error('Invalid shot plan');
 let frame=0;
 for(const s of plan.shots) {
  if(s.start_frame!==frame||s.end_frame-s.start_frame!==s.frames||s.frames<=0)throw Error('Noncontiguous timeline at shot '+s.id);
  if(!['cut','dissolve','light_leak'].includes(s.transition))throw Error('Unknown transition');
  frame=s.end_frame;
 }
 if(frame!==plan.total_frames||Math.abs(frame/30-plan.duration_seconds)>1e-8)throw Error('Timeline duration mismatch');
 return plan;
}

export async function command(exe,args,{cwd=ROOT,capture=false}={}) {
 return new Promise((resolve,reject)=>{
  const child=spawn(exe,args,{cwd,windowsHide:true,stdio:capture?['ignore','pipe','pipe']:['ignore','inherit','inherit']});
  let out='',err='';
  if(capture){child.stdout.on('data',b=>out+=b);child.stderr.on('data',b=>{err=(err+b).slice(-24000);});}
  child.once('error',reject);
  child.once('close',code=>code===0?resolve({stdout:out,stderr:err}):reject(Error(path.basename(exe)+' exited '+code+'\n'+err.slice(-4500))));
 });
}

async function find(root,base){
 for(const e of await fs.readdir(root,{withFileTypes:true})){
  if(e.name===base&&e.isFile())return path.join(root,e.name);
  if(e.isDirectory()){const r=await find(path.join(root,e.name),base);if(r)return r;}
 }
}
export async function tools({download=true}={}) {
 const ext=process.platform==='win32'?'.exe':'';
 let ffmpeg,ffprobe;
 for(const candidate of [path.join(ROOT,'tools','ffmpeg'+ext),'ffmpeg'+ext]){
  try {await command(candidate,['-version'],{capture:true});ffmpeg=candidate;break;} catch{}
 }
 for(const candidate of [path.join(ROOT,'tools','ffprobe'+ext),'ffprobe'+ext]){
  try {await command(candidate,['-version'],{capture:true});ffprobe=candidate;break;} catch{}
 }
 if(ffmpeg&&ffprobe)return {ffmpeg,ffprobe};
 if(process.platform!=='win32'||!download)throw Error('FFmpeg and FFprobe are required.');
 const archive=path.join(ROOT,'tools','ffmpeg-win64.zip');
 await fs.mkdir(path.dirname(archive),{recursive:true});
 console.log('Downloading the pinned FFmpeg Windows build (about 202 MB)...');
 const response=await fetch(toolVersion.url);
 if(!response.ok)throw Error('FFmpeg download HTTP '+response.status);
 await pipeline(Readable.fromWeb(response.body),createWriteStream(archive+'.part'));
 if(await digest(archive+'.part')!==toolVersion.sha256)throw Error('FFmpeg checksum mismatch; installation stopped.');
 await fs.rename(archive+'.part',archive);
 // Environment values avoid evaluating paths as PowerShell code.
 const previous=process.env.SIBERIA_FFMPEG_ARCHIVE;
 process.env.SIBERIA_FFMPEG_ARCHIVE=archive;
 try {await command('powershell.exe',['-NoProfile','-NonInteractive','-Command',
  'Expand-Archive -LiteralPath $env:SIBERIA_FFMPEG_ARCHIVE -DestinationPath ($env:SIBERIA_FFMPEG_ARCHIVE + ".expanded") -Force']);}
 finally {if(previous===undefined)delete process.env.SIBERIA_FFMPEG_ARCHIVE;else process.env.SIBERIA_FFMPEG_ARCHIVE=previous;}
 const a=await find(archive+'.expanded','ffmpeg.exe'),b=await find(archive+'.expanded','ffprobe.exe');
 if(!a||!b)throw Error('The verified archive did not contain FFmpeg / FFprobe.');
 for(const [src,name] of [[a,'ffmpeg.exe'],[b,'ffprobe.exe']])await fs.copyFile(src,path.join(ROOT,'tools',name));
 await save(path.join(ROOT,'tools','SOURCE.json'),{...toolVersion,source:'https://github.com/BtbN/FFmpeg-Builds',license:'See the complete expanded upstream archive retained here.'});
 return tools({download:false});
}
export async function probe(file,ffprobe) {
 const r=await command(ffprobe,['-v','error','-show_streams','-show_format','-of','json',file],{capture:true});
 return JSON.parse(r.stdout);
}
export function localURL(raw) {
 const u=new URL(raw);
 if(u.protocol!=='http:'||!['127.0.0.1','localhost'].includes(u.hostname)||u.username||u.password||u.search||u.hash||u.pathname!=='/')throw Error('Muse URL must be http://127.0.0.1:PORT with no credentials.');
 return u.origin;
}
export async function museStatus(raw) {
 const base=localURL(raw);
 const r=await fetch(base+'/api/status',{signal:AbortSignal.timeout(20000)});
 if(!r.ok)throw Error('Muse local API HTTP '+r.status);
 const value=await r.json();
 if(!value.museConfigured||!Array.isArray(value.accounts))throw Error('This endpoint is not a configured Muse Studio.');
 return {base,value};
}

/** A request is recorded before submission. Ambiguous failures never auto-resubmit. */
export async function generate(plan,{baseURL,limit=Infinity,retryShot,root=ROOT}={}) {
 const {base,value}=await museStatus(baseURL);
 if(value.busy)throw Error('Muse is busy. Finish its current request before starting this job.');
 if(value.transport==='browser'&&!value.accounts.find(a=>a.id===1)?.authenticated)throw Error('Open Muse 01, log in and click its session check first.');
 const {ffprobe}=await tools();
 const stateFile=path.join(root,'generation-state.json');
 const state=existsSync(stateFile)?await json(stateFile):{version:1,shots:{}};
 const media=path.join(root,'media');await fs.mkdir(media,{recursive:true});
 let created=0;
 for(let index=0;index<plan.shots.length;index++){
  const shot=plan.shots[index],key=idFile(shot.id),prior=state.shots[key];
  const promptHash=createHash('sha256').update(shot.prompt).digest('hex');
  if(prior?.status==='done'&&Number(retryShot)!==shot.id){
   if(!prior.file||!existsSync(path.join(root,prior.file)))throw Error('Completed file is missing for shot '+key);
   if(await digest(path.join(root,prior.file))!==prior.sha256)throw Error('Saved media changed for shot '+key+'; inspect it before continuing.');
   if(prior.prompt_sha256!==promptHash)throw Error('The prompt changed for completed shot '+key+'. To deliberately replace it use --retry-shot '+shot.id);
   continue;
  }
  if(prior&&prior.status!=='done'&&Number(retryShot)!==shot.id)throw Error('Shot '+key+' has an unresolved submission. Check Muse history first. To deliberately resubmit only this shot use: generate --retry-shot '+shot.id);
  if(created>=limit)break;
  const request={accountId:1,accountMode:'single',batchId:randomUUID(),sceneId:((shot.id-1)%10)+1,prompt:shot.prompt,
   aspectRatio:'16:9',resolution:plan.requested_resolution,model:plan.requested_model,duration:10,sourceMode:'text',characterLock:true};
  if(prior?.file&&existsSync(path.join(root,prior.file))){
   const history=path.join(media,'history');await fs.mkdir(history,{recursive:true});
   await fs.copyFile(path.join(root,prior.file),path.join(history,key+'-'+Date.now()+path.extname(prior.file)));
  }
  state.shots[key]={status:'submitting',submitted_at:new Date().toISOString(),prompt_sha256:promptHash};
  await save(stateFile,state);
  console.log('Muse shot '+shot.id+'/'+plan.shots.length+' — '+shot.chapter);
  try {
   const response=await fetch(base+'/api/video',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:AbortSignal.timeout(650000)});
   const result=await response.json();
   if(!response.ok)throw Error(String(result.error||('HTTP '+response.status)));
   const extension={'video/mp4':'.mp4','video/webm':'.webm','video/quicktime':'.mov'}[result.mimeType];
   if(!extension||typeof result.base64!=='string'||!result.base64.length)throw Error('No valid video file in Muse response.');
   const relative='media/'+key+extension,file=path.join(root,relative);
   const bytes=Buffer.from(result.base64,'base64');if(bytes.length<1000)throw Error('Muse returned an unexpectedly small video.');
   await fs.writeFile(file+'.part',bytes);await fs.rename(file+'.part',file);
   // Record receipt before media verification, so failed validation cannot lose the result.
   state.shots[key]={...state.shots[key],status:'received',file:relative,mime:result.mimeType,sha256:await digest(file)};await save(stateFile,state);
   const info=await probe(file,ffprobe),video=info.streams.find(s=>s.codec_type==='video');
   const actual=Number(video?.duration||info.format.duration);
   const required=shot.source_in_seconds+shot.frames/30+8/30;
   if(!video||!Number.isFinite(actual)||actual+1/30<required)throw Error('Shot '+key+' is too short ('+actual+' sec, need '+required.toFixed(3)+'). Saved the returned media; did not resubmit.');
   state.shots[key]={...state.shots[key],status:'done',received_at:new Date().toISOString(),actual_seconds:actual,width:video.width,height:video.height,
    upscaled_for_1080p:video.width<plan.width||video.height<plan.height};
   if(state.shots[key].upscaled_for_1080p)console.log('  Returned '+video.width+'x'+video.height+'; the export will record its upscale.');
   await save(stateFile,state);created++;
  } catch(error) {
   state.shots[key]={...state.shots[key],status:state.shots[key].status==='received'?'needs_review':'uncertain',error:String(error.message).slice(0,1500)};
   await save(stateFile,state);throw error;
  }
 }
 return state;
}

export async function ensureFont(root=ROOT) {
 const dest=path.join(root,'font.ttf');if(existsSync(dest))return dest;
 const candidates=process.platform==='win32'?[path.join(process.env.WINDIR||'C:\\Windows','Fonts','arial.ttf')]:[
  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'];
 for(const c of candidates)if(existsSync(c)){await fs.copyFile(c,dest);return dest;}
 throw Error('A local Arial or DejaVu font is required.');
}
const normalise=(s,width,height,frames)=>`fps=30,scale=${width}:${height}:force_original_aspect_ratio=increase,crop=${width}:${height},setsar=1,format=yuv420p,trim=start_frame=${Math.round(s.source_in_seconds*30)}:end_frame=${Math.round(s.source_in_seconds*30)+frames},setpts=PTS-STARTPTS`;

export async function renderClip({shot,previous,next,input,previousInput,output,ffmpeg,width=1920,height=1080,root=ROOT}) {
 await fs.mkdir(path.dirname(output),{recursive:true});await ensureFont(root);
 const args=['-hide_banner','-loglevel','error','-y','-filter_complex_threads','1','-i',input];
 let graph;
 if(shot.transition==='dissolve'&&previous){
  args.push('-i',previousInput);
  graph=`[0:v]${normalise(shot,width,height,shot.frames)},split=2[a][b];`+
   `[a]trim=end_frame=8,setpts=PTS-STARTPTS[head];`+
   `[b]trim=start_frame=8:end_frame=${shot.frames},setpts=PTS-STARTPTS[rest];`+
   `[1:v]${normalise(previous,width,height,previous.frames+8)},trim=start_frame=${previous.frames}:end_frame=${previous.frames+8},setpts=PTS-STARTPTS[tail];`+
   `[tail][head]blend=all_expr='A*(1-min(T*30/7,1))+B*min(T*30/7,1)'[bridge];`+
   `[bridge][rest]concat=n=2:v=1:a=0[image];`;
 }else graph=`[0:v]${normalise(shot,width,height,shot.frames)}[image];`;
 const filters=[];
 if(shot.transition==='light_leak')filters.push('fade=t=in:st=0:d=0.2:color=white');
 if(next?.transition==='light_leak'){
  const start=(shot.frames-9)/30;
  filters.push(`drawbox=x=0:y=0:w=iw*0.60:h=ih:color=0xFFB45C@0.25:t=fill:enable='gte(t,${start})'`,
   `fade=t=out:st=${(shot.frames-4)/30}:d=${4/30}:color=white`);
 }
 const label=shot.kind==='schematic'?'SCHEMATIC':shot.kind==='historical reconstruction'?'RECONSTRUCTION':'AI VISUALISATION';
 const scale=width/1920;
 filters.push(`drawbox=x=${Math.round(36*scale)}:y=ih-${Math.round(58*scale)}:w=${Math.round(300*scale)}:h=${Math.round(32*scale)}:color=black@0.35:t=fill`,
  `drawtext=fontfile=font.ttf:text='${label}':fontsize=${Math.max(9,Math.round(18*scale))}:x=${Math.round(48*scale)}:y=h-${Math.round(50*scale)}:fontcolor=white`);
 if(shot.title){
  await fs.mkdir(path.join(root,'titles'),{recursive:true});await fs.writeFile(path.join(root,'titles',idFile(shot.id)+'.txt'),shot.title,'utf8');
  filters.push(`drawtext=fontfile=font.ttf:textfile=titles/${idFile(shot.id)}.txt:fontsize=${Math.round(42*scale)}:x=${Math.round(64*scale)}:y=${Math.round(76*scale)}:fontcolor=white:shadowcolor=black@0.8:shadowx=2:shadowy=2:enable='between(t,0.45,${Math.min(4.8,(shot.frames-2)/30)})'`);
 }
 graph+='[image]'+filters.join(',')+'[v]';
 args.push('-filter_complex',graph,'-map','[v]','-an','-frames:v',String(shot.frames),'-r','30',
  '-c:v','libx264','-threads','2','-preset','medium','-crf','18','-pix_fmt','yuv420p','-profile:v','high',
  '-video_track_timescale','90000','-movflags','+faststart',output);
 await command(ffmpeg,args,{cwd:root});
}

/** Original deterministic ambient score, generated from oscillators and filtered noise. */
export async function createScore(file,seconds,chapters=[]) {
 const rate=48000,frames=Math.round(seconds*rate),header=Buffer.alloc(44);
 header.write('RIFF');header.writeUInt32LE(36+frames*4,4);header.write('WAVEfmt ',8);header.writeUInt32LE(16,16);
 header.writeUInt16LE(1,20);header.writeUInt16LE(2,22);header.writeUInt32LE(rate,24);header.writeUInt32LE(rate*4,28);
 header.writeUInt16LE(4,32);header.writeUInt16LE(16,34);header.write('data',36);header.writeUInt32LE(frames*4,40);
 await fs.mkdir(path.dirname(file),{recursive:true});const handle=await fs.open(file+'.part','w');
 const chords=[[50,57,62,65],[46,53,58,62],[48,55,60,64],[45,52,57,60]];
 const freq=chords.map(c=>c.map(m=>440*2**((m-69)/12)));
 let seed=2536,brown=0;const blocks=8192;
 const boundaries=chapters.map(c=>c.start_ms/1000).filter(t=>t>0&&t<seconds-1);
 try{
  await handle.write(header);
  for(let start=0;start<frames;start+=blocks){
   const size=Math.min(blocks,frames-start),block=Buffer.allocUnsafe(size*4);
   for(let j=0;j<size;j++){
    const t=(start+j)/rate,ci=Math.floor(t/32)%4,pi=(ci+3)%4;
    const w=Math.min(1,(t%32)/3),mix=w*w*(3-2*w);
    let left=0,right=0;
    for(let n=0;n<4;n++){
     const a=2*Math.PI*freq[ci][n]*t,b=2*Math.PI*freq[pi][n]*t;
     const weight=[1,.7,.55,.4][n];
     left+=weight*(mix*Math.sin(a+.025*Math.sin(t*.31+n))+(1-mix)*Math.sin(b));
     right+=weight*(mix*Math.sin(a+.2+n*.07)+(1-mix)*Math.sin(b+.2+n*.07));
    }
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;const noise=seed/2147483648-1;
    brown=.995*brown+.005*noise;
    let sweep=0;
    for(const boundary of boundaries){const d=t-boundary;if(d>-.4&&d<.8)sweep+=Math.sin(Math.PI*(d+.4)/1.2)**2;}
    const envelope=Math.min(1,t/6,(seconds-t)/8);
    const amp=.016*(.88+.12*Math.sin(t*.075));
    const l=envelope*(amp*left+.018*brown+.009*noise*sweep),r=envelope*(amp*right+.018*brown+.009*noise*sweep);
    block.writeInt16LE(Math.round(Math.max(-1,Math.min(1,l))*32767),j*4);
    block.writeInt16LE(Math.round(Math.max(-1,Math.min(1,r))*32767),j*4+2);
   }
   await handle.write(block);
  }
 }finally{await handle.close();}
 await fs.rename(file+'.part',file);return file;
}

export async function verifyWav(file,seconds,ffprobe) {
 const info=await probe(file,ffprobe),a=info.streams.find(s=>s.codec_type==='audio');
 if(!a||a.codec_name!=='pcm_s16le'||Number(a.sample_rate)!==48000||a.channels!==1)throw Error('Voice must be mono PCM16 WAV, 48 kHz.');
 const samples=Number(a.duration_ts)*Number(a.time_base.split('/')[0])*48000/Number(a.time_base.split('/')[1]);
 if(samples!==Math.round(seconds*48000))throw Error('Voice sample count mismatch: '+samples);
 return info;
}
export async function mixAudio({voice,score,output,seconds,ffmpeg,root=ROOT}) {
 const raw=output+'.mix.wav';
 await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',voice,'-i',score,'-filter_complex',
  '[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][side];'+
  '[1:a]volume=0.65[bed];'+
  '[bed][side]sidechaincompress=threshold=0.02:ratio=5:attack=25:release=500[duck];'+
  '[v][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.85:level=false:latency=true[m]',
  '-map','[m]','-t',String(seconds),'-ar','48000','-c:a','pcm_s16le',raw],{cwd:root});
 const measured=await command(ffmpeg,['-hide_banner','-nostats','-i',raw,'-af','loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json','-f','null','-'],{capture:true,cwd:root});
 const block=measured.stderr.match(/\{\s*"input_i"[\s\S]*?\}/g)?.at(-1);if(!block)throw Error('Could not measure final audio loudness.');
 const l=JSON.parse(block);
 const filter=`loudnorm=I=-16:TP=-1.5:LRA=7:measured_I=${l.input_i}:measured_TP=${l.input_tp}:measured_LRA=${l.input_lra}:measured_thresh=${l.input_thresh}:offset=${l.target_offset}:linear=true`;
 await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',raw,'-af',filter,'-t',String(seconds),'-ar','48000','-c:a','pcm_s16le',output],{cwd:root});
 await fs.unlink(raw);return l;
}

export async function render(plan,{voiceCode='en',includeSubtitles=false}={}) {
 const {ffmpeg,ffprobe}=await tools();
 const voice=path.join(ROOT,'audio',voiceCode+'.wav');
 if(!existsSync(voice))throw Error('Download '+voiceCode+'.wav from the draft GitHub Release into the audio folder first.');
 await verifyWav(voice,plan.duration_seconds,ffprobe);
 const stateFile=path.join(ROOT,'generation-state.json');
 if(!existsSync(stateFile))throw Error('Muse media has not been generated. Run the generation step first.');
 const state=await json(stateFile),folder=path.join(ROOT,'rendered-shots');await fs.mkdir(folder,{recursive:true});
 for(let i=0;i<plan.shots.length;i++){
  const shot=plan.shots[i],record=state.shots[idFile(shot.id)];
  if(record?.status!=='done')throw Error('Muse shot '+shot.id+' is not verified. No substitute or placeholder was inserted.');
  const input=path.join(ROOT,record.file);
  if(await digest(input)!==record.sha256)throw Error('Source media checksum changed for shot '+shot.id);
  const output=path.join(folder,idFile(shot.id)+'.mp4'),cache=output+'.json';
  const previous=i>0?plan.shots[i-1]:null;
  const signature=createHash('sha256').update(JSON.stringify({shot,next:plan.shots[i+1],previous,source:record.sha256,
   previousSource:previous?state.shots[idFile(previous.id)]?.sha256:null,renderer:await digest(fileURLToPath(import.meta.url))})).digest('hex');
  if(existsSync(output)&&existsSync(cache)&&(await json(cache)).signature===signature)continue;
  console.log('Editing '+shot.id+'/'+plan.shots.length+' — '+shot.frames+' frames');
  await renderClip({shot,previous,next:plan.shots[i+1],input,previousInput:previous?path.join(ROOT,state.shots[idFile(previous.id)].file):null,
   output:output+'.part.mp4',ffmpeg});
  const info=await probe(output+'.part.mp4',ffprobe),v=info.streams.find(s=>s.codec_type==='video');
  if(Number(v.nb_frames)!==shot.frames)throw Error('Rendered shot frame count mismatch at '+shot.id);
  await fs.rename(output+'.part.mp4',output);await save(cache,{signature,frames:shot.frames});
 }
 const list=path.join(folder,'concat.txt');
 await fs.writeFile(list,plan.shots.map(s=>`file '${idFile(s.id)}.mp4'`).join('\n')+'\n');
 const picture=path.join(ROOT,'Siberia_PICTURE_25m36.mp4');
 await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-f','concat','-safe','1','-i',list,'-c','copy','-an','-movflags','+faststart',picture]);
 const score=path.join(ROOT,'audio','original-score.wav');
 if(!existsSync(score)){console.log('Creating the original ambient music and chapter sweeps...');await createScore(score,plan.duration_seconds,(await json(path.join(ROOT,'scripts','master_timeline.json'))).chapters);}
 const mix=path.join(ROOT,'audio',voiceCode+'-final-mix.wav');
 console.log('Mixing narration and background, then measuring loudness...');
 const inputLoudness=await mixAudio({voice,score,output:mix,seconds:plan.duration_seconds,ffmpeg});
 const subtitle=path.join(ROOT,'scripts',voiceCode+'.srt'),output=path.join(ROOT,'Siberia_'+voiceCode.toUpperCase()+'_25m36.mp4');
 const args=['-hide_banner','-loglevel','error','-y','-i',picture,'-i',mix];
 if(includeSubtitles&&existsSync(subtitle))args.push('-i',subtitle);
 args.push('-map','0:v:0','-map','1:a:0');if(includeSubtitles&&existsSync(subtitle))args.push('-map','2:0','-c:s','mov_text','-disposition:s:0','0');
 args.push('-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t',String(plan.duration_seconds),'-movflags','+faststart',output);
 await command(ffmpeg,args);
 const info=await probe(output,ffprobe),video=info.streams.find(s=>s.codec_type==='video');
 if(Number(video.nb_frames)!==plan.total_frames||video.width!==1920||video.height!==1080)throw Error('Final video failed frame count / size verification.');
 const finalMeasure=await command(ffmpeg,['-hide_banner','-nostats','-i',output,'-filter:a','ebur128=peak=true','-f','null','-'],{capture:true});
 await fs.writeFile(path.join(ROOT,'FINAL_AUDIO_MEASUREMENT.txt'),finalMeasure.stderr.slice(-5000),'utf8');
 await save(path.join(ROOT,'FINAL_REPORT.json'),{completed_at:new Date().toISOString(),file:path.basename(output),sha256:await digest(output),
  duration_seconds:plan.duration_seconds,frames:Number(video.nb_frames),fps:video.avg_frame_rate,resolution:[video.width,video.height],
  voice:voiceCode,voice_sha256:await digest(voice),all_visuals_from_local_muse:true,
  upscaled_source_shots:plan.shots.filter(s=>state.shots[idFile(s.id)].upscaled_for_1080p).map(s=>s.id),
  measurement_before_normalisation:inputLoudness,needs_human_visual_review:true,
  review:'Watch the encoded MP4 and compare geography to cited references before publication. AI-generated illustration is labelled.'});
 console.log('DONE: '+output+' — exact '+plan.total_frames+' video frames.');
 return output;
}

async function main(){
 const operation=process.argv[2]||'help';
 const plan=validatePlan(await json(path.join(ROOT,'shot_plan.json')));
 const baseURL=argument('--base-url',process.env.SIBERIA_MUSE_URL);
 if(operation==='help'){console.log('Commands: check | generate [--limit N] [--retry-shot ID] | render [--voice en] | all | score\nMuse must already be open and logged in. Example: --base-url http://127.0.0.1:8788');return;}
 if(operation==='check'){
  const t=await tools();console.log('FFmpeg / FFprobe OK. Timeline: '+plan.shots.length+' shots, '+plan.duration_seconds+' seconds.');
  if(baseURL){const s=await museStatus(baseURL);console.log('Muse local API OK. Account 01 authenticated: '+Boolean(s.value.accounts.find(a=>a.id===1)?.authenticated));}
  await verifyWav(path.join(ROOT,'audio','en.wav'),plan.duration_seconds,t.ffprobe);console.log('English WAV has exactly 73,728,000 samples.');
 }else if(operation==='score')await createScore(path.join(ROOT,'audio','original-score.wav'),plan.duration_seconds,(await json(path.join(ROOT,'scripts','master_timeline.json'))).chapters);
 else if(operation==='generate')await generate(plan,{baseURL,limit:Number(argument('--limit',Infinity)),retryShot:argument('--retry-shot',undefined)});
 else if(operation==='render')await render(plan,{voiceCode:argument('--voice','en'),includeSubtitles:process.argv.includes('--subtitles')});
 else if(operation==='all'){await generate(plan,{baseURL});await render(plan);}
 else throw Error('Unknown command: '+operation);
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error('\nSTOPPED: '+e.message+'\nSaved results are retained. Read README_VI.md for resuming.');process.exitCode=1;});

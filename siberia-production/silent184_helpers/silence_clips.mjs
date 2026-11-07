/** Remove audio by stream copy, then verify every output. Never edits originals. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {tools,command,probe,digest} from './ffmpeg_tools.mjs';

const root=path.dirname(fileURLToPath(import.meta.url));
const input=path.resolve(process.argv[2]||path.join(root,'clips'));
const output=path.resolve(process.argv[3]||path.join(root,'SILENT'));
if(input===output)throw Error('Input and output must be different folders.');
await fs.mkdir(input,{recursive:true});await fs.mkdir(output,{recursive:true});
const files=(await fs.readdir(input,{withFileTypes:true})).filter(e=>e.isFile()&&/\.(mp4|mov|webm|mkv)$/i.test(e.name)).sort((a,b)=>a.name.localeCompare(b.name));
if(!files.length)throw Error('Put the Muse clips into the clips folder first. No media files were found.');
const {ffmpeg,ffprobe}=await tools();const results=[];
for(const e of files){
 const src=path.join(input,e.name),dst=path.join(output,e.name);
 // Exclusive output: a previous verified file is reused; an unrelated file is never overwritten.
 const before=await probe(src,ffprobe);const v=before.streams.find(s=>s.codec_type==='video');
 if(!v)throw Error('No video stream: '+e.name);
 const sourceHash=await digest(src);
 let existing;
 try{existing=JSON.parse(await fs.readFile(dst+'.source.json','utf8'));}catch{}
 if(existing?.source_sha256===sourceHash&&existing?.output_sha256===await digest(dst).catch(()=>null)){
  const p=await probe(dst,ffprobe);if(p.streams.some(s=>s.codec_type==='audio'))throw Error('Previously silent file contains audio.');
  results.push({...existing,filename:e.name,reused:true});continue;
 }
 try{await fs.access(dst);throw Error('Output already exists and is not a verified match: '+dst);}catch(error){if(error.code!=='ENOENT')throw error;}
 const part=path.join(output,path.parse(e.name).name+'.partial'+path.extname(e.name));
 await command(ffmpeg,['-hide_banner','-loglevel','error','-n','-i',src,'-map','0:v:0','-c:v','copy','-an','-sn','-dn',part]);
 const after=await probe(part,ffprobe);const av=after.streams.find(s=>s.codec_type==='video');
 if(after.streams.some(s=>s.codec_type==='audio'))throw Error('Audio removal verification failed: '+e.name);
 if(av.codec_name!==v.codec_name||av.width!==v.width||av.height!==v.height)throw Error('Video properties changed.');
 const a=Number(v.duration??before.format.duration),b=Number(av.duration??after.format.duration);
 if(!Number.isFinite(a)||!Number.isFinite(b)||Math.abs(a-b)>.05)throw Error('Unexpected video duration change.');
 await fs.rename(part,dst);
 const record={filename:e.name,source_sha256:sourceHash,output_sha256:await digest(dst),audio_stream_count:0,
  source_seconds:a,output_seconds:b,codec:v.codec_name,width:v.width,height:v.height,video_reencoded:false};
 await fs.writeFile(dst+'.source.json',JSON.stringify(record,null,2)+'\n');results.push(record);
 console.log(e.name+': SILENT — video copied without re-encoding');
}
await fs.writeFile(path.join(output,'SILENCE_REPORT.json'),JSON.stringify({files:results.length,all_outputs_have_zero_audio_streams:true,results},null,2)+'\n');
console.log('Done: '+results.length+' silent clips in '+output);

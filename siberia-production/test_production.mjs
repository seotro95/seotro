/** Integration checks with synthetic test media, not generated Muse deliverables. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import http from 'node:http';
import {validatePlan,localURL,command,tools,probe,renderClip,createScore,mixAudio,verifyWav,generate} from './kit/production.mjs';
const root=await fs.mkdtemp(path.join(os.tmpdir(),'siberia-integration-'));
const {ffmpeg,ffprobe}=await tools();
const colors=['red','blue','green'];
const shots=colors.map((c,i)=>({id:i+1,start_frame:i*60,end_frame:(i+1)*60,frames:60,
 source_in_seconds:.4,transition:['cut','dissolve','light_leak'][i],kind:'AI visualisation',title:i===0?'TEST ONLY':''}));
assert.equal(validatePlan({fps:30,shots,total_frames:180,duration_seconds:6}).total_frames,180);
assert.throws(()=>validatePlan({fps:30,shots,total_frames:179,duration_seconds:6}));
assert.throws(()=>localURL('https://example.com'));assert.throws(()=>localURL('http://user:password@localhost:8788'));
for(let i=0;i<3;i++){
 await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-f','lavfi','-i',`color=c=${colors[i]}:s=320x180:r=30:d=3`,'-c:v','libx264','-threads','2',path.join(root,'source'+i+'.mp4')],{cwd:root});
 await renderClip({shot:shots[i],previous:i?shots[i-1]:null,next:shots[i+1],input:path.join(root,'source'+i+'.mp4'),
  previousInput:i?path.join(root,'source'+(i-1)+'.mp4'):null,output:path.join(root,'edited'+i+'.mp4'),ffmpeg,width:320,height:180,root});
 const info=await probe(path.join(root,'edited'+i+'.mp4'),ffprobe);
 assert.equal(Number(info.streams[0].nb_frames),60,'Transition must preserve every target frame');
}
// Read three actual RGB pixels across the dissolve: red -> mixed -> blue.
async function pixel(frame){
 const args=['-hide_banner','-loglevel','error','-i',path.join(root,'edited1.mp4'),'-vf',`select=eq(n\\,${frame}),crop=2:2:150:80,format=rgb24`,'-frames:v','1','-f','rawvideo','-'];
 return new Promise((resolve,reject)=>{const p=spawn(ffmpeg,args);let a=[];p.stdout.on('data',b=>a.push(b));p.on('error',reject);p.on('close',c=>c?reject(Error('Pixel read failed')):resolve(Buffer.concat(a)));});
}
const a=await pixel(0),b=await pixel(4),c=await pixel(12);
assert(a[0]>a[2]+100,'Dissolve begins with outgoing picture');
assert(b[0]>20&&b[2]>20,'Dissolve contains both pictures');
assert(c[2]>c[0]+100,'Dissolve reaches incoming picture');
const score=path.join(root,'score.wav');await createScore(score,6,[{start_ms:3000}]);
const s=await probe(score,ffprobe);assert.equal(s.streams[0].duration_ts,288000);
const voice=path.join(root,'voice.wav');
await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-f','lavfi','-i','sine=frequency=180:sample_rate=48000:duration=6','-ac','1','-c:a','pcm_s16le',voice],{cwd:root});
await verifyWav(voice,6,ffprobe);
await assert.rejects(()=>verifyWav(voice,7,ffprobe));
await mixAudio({voice,score,output:path.join(root,'mix.wav'),seconds:6,ffmpeg,root});
const mix=await probe(path.join(root,'mix.wav'),ffprobe);assert.equal(mix.streams[0].duration_ts,288000);
console.log('PASS: contiguous frames; actual dissolve pixels; light leak and labels; exact voice length; background mix. Test fixtures:',root);
// Exercise receipt, byte verification and interruption without an actual paid Muse request.
const media=await fs.readFile(path.join(root,'source0.mp4'));
let submissions=0,fail=false;
const server=http.createServer(async(req,res)=>{
 res.setHeader('Content-Type','application/json');
 if(req.url==='/api/status'){res.end(JSON.stringify({museConfigured:true,transport:'browser',accounts:[{id:1,authenticated:true}],busy:false}));return;}
 assert.equal(req.method,'POST');assert.equal(req.url,'/api/video');
 let body='';for await(const part of req)body+=part;
 const data=JSON.parse(body);assert.equal(data.accountId,1);assert.equal(data.model,'Omni 1.1 Flash');
 assert.equal(data.duration,10);assert.equal(data.sourceMode,'text');assert.equal(data.aspectRatio,'16:9');
 assert.match(data.batchId,/^[a-f0-9-]{36}$/i);assert(data.sceneId>=1&&data.sceneId<=10);
 submissions++;
 if(fail){res.statusCode=502;res.end(JSON.stringify({error:'TEST ambiguous provider response'}));return;}
 res.end(JSON.stringify({base64:media.toString('base64'),mimeType:'video/mp4',metadata:{width:320,height:180,duration:3}}));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const baseURL='http://127.0.0.1:'+server.address().port;
const p={fps:30,width:1920,height:1080,requested_model:'Omni 1.1 Flash',requested_resolution:'1080p',
 shots:[{...shots[0],prompt:'TEST ONLY synthetic red sample',chapter:'TEST ONLY'}]};
try{
 const good=path.join(root,'generation-good');
 await generate(p,{root:good,baseURL});await generate(p,{root:good,baseURL});
 assert.equal(submissions,1,'Completed media must not be submitted twice');
 fail=true;const bad=path.join(root,'generation-uncertain');
 await assert.rejects(()=>generate(p,{root:bad,baseURL}));
 await assert.rejects(()=>generate(p,{root:bad,baseURL}));assert.equal(submissions,2,'An ambiguous failure must not auto-resubmit');
 fail=false;await generate(p,{root:bad,baseURL,retryShot:1});assert.equal(submissions,3);
 console.log('PASS: Muse request contract, successful resume, ambiguous failure stop and explicit one-shot retry.');
}finally{server.close();server.closeAllConnections();}

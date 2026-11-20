import{test}from'node:test';import assert from'node:assert/strict';import{mkdtemp,rm}from'node:fs/promises';import path from'node:path';import os from'node:os';import{MuseAccounts}from'../muse-accounts.mjs';
const tick=()=>new Promise(r=>setImmediate(r));
test('a failed unsent parallel wave automatically drains through one logged-in lane in order, retaining prompt names',{timeout:10000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-auto-'));const calls=[];let running=0,peak=0,releaseFailure;
 const held=new Promise(r=>releaseFailure=r);
 const driver={maxConcurrency:6,queue:[],progress:()=>[],account:()=>({authenticated:true}),closePreparedPages:async()=>{},generateVideo:async data=>{
  calls.push(data);if(!data.singleLane){await held;throw Object.assign(new Error('MUSE_COMPOSER_NOT_READY: Worker failed before Enter'),{parallelFailure:true,notSubmitted:true})}
  running++;peak=Math.max(peak,running);await tick();running--;return {name:data.outputName};
 }};const pool=new MuseAccounts({profileRoot:root,createDriver:()=>driver});
 try{
  const outputs=Promise.all(Array.from({length:10},(_,i)=>pool.generateVideo({accountId:1,batchId:'batch',sceneId:i+1,prompt:'Prompt '+(i+1),outputName:'Name '+(i+1),submissionGroup:{id:'wave',size:6}},new AbortController().signal)));
  assert.equal(calls.length,6);releaseFailure();const result=await outputs;assert.equal(peak,1);assert.equal(pool.usage.size,0);assert.equal(pool.waiters.size,0);
  assert.deepEqual(result.map(r=>r.name),Array.from({length:10},(_,i)=>'Name '+(i+1)));assert.deepEqual(calls.filter(r=>r.singleLane).map(r=>r.sceneId),Array.from({length:10},(_,i)=>i+1));assert.ok(calls.filter(r=>r.singleLane).every(r=>!r.submissionGroup));assert.equal(pool.snapshot()[0].executionConcurrency,1);
 }finally{await rm(root,{recursive:true,force:true})}
});
test('an acknowledged or ambiguous request is never replayed; later scenes continue serially and cancellation removes only the queued scene',{timeout:10000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-no-replay-'));const calls=[];let finish;
 const driver={maxConcurrency:2,queue:[],progress:()=>[],account:()=>({authenticated:true}),closePreparedPages:async()=>{},generateVideo:async data=>{calls.push(data.sceneId);if(data.sceneId===1){await tick();throw Object.assign(new Error('MUSE_SUBMIT_NOT_ACKNOWLEDGED: unknown outcome'),{parallelFailure:true,notSubmitted:false})}if(data.sceneId===2)return new Promise(r=>finish=r);return {ok:true}}};
 const pool=new MuseAccounts({profileRoot:root,createDriver:()=>driver});
 try{
  const first=assert.rejects(pool.generateVideo({accountId:1,sceneId:1},new AbortController().signal),/NOT_ACKNOWLEDGED/);const second=pool.generateVideo({accountId:1,sceneId:2},new AbortController().signal);
  const c=new AbortController();const third=assert.rejects(pool.generateVideo({accountId:1,sceneId:3},c.signal));const fourth=pool.generateVideo({accountId:1,sceneId:4},new AbortController().signal);
  await first;assert.deepEqual(calls,[1,2]);c.abort();await third;finish({ok:true});await Promise.all([second,fourth]);assert.deepEqual(calls,[1,2,4]);assert.equal(pool.usage.size,0);
 }finally{await rm(root,{recursive:true,force:true})}
});

test('text enhancement owns the shared editor exclusively after existing generations finish',{timeout:10000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-exclusive-'));const calls=[];let finishVideo,finishText;
 const driver={maxConcurrency:2,parallelStrategy:'shared-conversation',queue:[],progress:()=>[],account:()=>({authenticated:true}),generateVideo:async data=>{calls.push('video'+data.sceneId);if(data.sceneId===1)return new Promise(r=>finishVideo=r);return {ok:true}},generateText:async()=>{calls.push('text');return new Promise(r=>finishText=r)}};
 const pool=new MuseAccounts({profileRoot:root,createDriver:()=>driver});
 try{const one=pool.generateVideo({accountId:1,sceneId:1},new AbortController().signal);const text=pool.generateText({accountId:1,sceneId:2},new AbortController().signal);const three=pool.generateVideo({accountId:1,sceneId:3},new AbortController().signal);assert.deepEqual(calls,['video1']);finishVideo({ok:true});await one;await tick();assert.deepEqual(calls,['video1','text']);finishText({text:'enhanced'});await Promise.all([text,three]);assert.deepEqual(calls,['video1','text','video3']);assert.equal(pool.usage.size,0);}finally{await rm(root,{recursive:true,force:true})}
});

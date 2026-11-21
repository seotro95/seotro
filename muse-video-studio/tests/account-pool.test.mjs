import {test} from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,rm,writeFile} from 'node:fs/promises';import path from 'node:path';import os from 'node:os';
import {MuseAccounts} from '../muse-accounts.mjs';
test('ten accounts admit sixty simultaneous jobs, enforce six per account and release a cancelled slot independently',async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-pool-'));const pending=new Map();const calls=[];
 const pool=await new MuseAccounts({profileRoot:root,createDriver:id=>({account:()=>({authenticated:true}),maxConcurrency:6,queue:[],progress:()=>[],generateVideo:(data,signal)=>new Promise((resolve,reject)=>{calls.push({id,...data});pending.set(data.sceneId,resolve);signal.addEventListener('abort',()=>reject(signal.reason),{once:true})})})}).load();
 try{
  await pool.importLabels(Array.from({length:40},(_,i)=>`owner${i+1}@example.invalid`));assert.equal(pool.snapshot().length,40);
  await assert.rejects(pool.importLabels(['same','SAME']),/ACCOUNT_LIST_INVALID/);await assert.rejects(pool.generateVideo({accountId:41},new AbortController().signal),/ACCOUNT_INVALID/);
  const controls=Array.from({length:60},()=>new AbortController());
  const settled=Promise.allSettled(controls.map((control,i)=>pool.generateVideo({accountId:Math.floor(i/6)+1,accountMode:'multiple',sceneId:i+1,prompt:`video ${i+1}`},control.signal)));
  assert.equal(calls.length,60);assert.equal(pool.usage.size,10);assert.ok(pool.snapshot().slice(0,10).every(a=>a.running===6&&a.executionConcurrency===6));assert.ok(calls.every(c=>c.accountId===1&&!c.singleLane));
  const queuedControl=new AbortController();const queued=pool.generateVideo({accountId:4,sceneId:61,accountMode:'multiple'},queuedControl.signal);assert.equal(pool.snapshot()[3].queued,1);const cancelledQueued=assert.rejects(queued);queuedControl.abort();await cancelledQueued;
  controls[18].abort();await new Promise(resolve=>setImmediate(resolve));assert.equal(pool.usage.get(4).count,5);assert.equal(pool.usage.get(5).count,6);
  const replacement=pool.generateVideo({accountId:4,sceneId:61,accountMode:'multiple'},new AbortController().signal);assert.equal(pool.usage.get(4).count,6);
  for(const [id,resolve] of pending)if(id!==19)resolve({base64:'Zml4dHVyZQ==',mimeType:'video/mp4'});
  const outputs=await settled;await replacement;assert.equal(outputs.filter(x=>x.status==='fulfilled').length,59);assert.equal(outputs[18].status,'rejected');assert.equal(pool.usage.size,0);
 }finally{await rm(root,{recursive:true,force:true})}
});
test('unavailable parallel conversations automatically prepare one lane without losing the requested count',async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-fallback-'));const calls=[];
 const driver={maxConcurrency:1,queue:[],account:()=>({authenticated:true}),progress:()=>[],setConcurrency:async count=>{if(count>1)throw new Error('MUSE_PARALLEL_UNVERIFIED: Shared chat only');return {executionConcurrency:1}},generateText:async data=>{calls.push(data);return {text:'ok'}}};const pool=new MuseAccounts({profileRoot:root,createDriver:()=>driver});
 try{
  const prepared=await pool.prepareSingle(new AbortController().signal,6,27);assert.equal(prepared.executionConcurrency,1);assert.equal(prepared.serialFallback,true);assert.equal(calls.length,0);assert.equal((await new MuseAccounts({profileRoot:root}).load()).preferredConcurrency,6);
  await pool.prepareSingle(new AbortController().signal,1,27);assert.equal(pool.concurrencyWarning,'');
  await pool.generateText({accountId:27,accountMode:'multiple'},new AbortController().signal);assert.equal(calls[0].singleLane,true);
  for(const count of [0,11,40,'6'])await assert.rejects(pool.prepareSingle(new AbortController().signal,count,27),/MUSE_CONCURRENCY_INVALID/);
  await writeFile(path.join(root,'single-concurrency.json'),'40');assert.equal((await new MuseAccounts({profileRoot:root}).load()).preferredConcurrency,10);
 }finally{await rm(root,{recursive:true,force:true})}
});
test('concurrent account preparation returns each account own lane count, never the last globally selected account',async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-account-lanes-'));const release=new Map(),counts=new Map([[1,1],[2,6],[3,2]]);const pool=new MuseAccounts({profileRoot:root,createDriver:id=>({maxConcurrency:counts.get(id),queue:[],account:()=>({authenticated:true}),progress:()=>[],ensureComposerReady:async()=>new Promise(r=>release.set(id,r))})});
 try{const jobs=[1,2,3].map(id=>pool.prepareSingle(new AbortController().signal,counts.get(id),id));for(const id of [2,1,3])release.get(id)();const results=await Promise.all(jobs);assert.deepEqual(results.map(row=>row.executionConcurrency),[1,6,2]);}finally{await rm(root,{recursive:true,force:true})}
});

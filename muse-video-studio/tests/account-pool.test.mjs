import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {MuseAccounts} from '../muse-accounts.mjs';

test('account pool isolates routing, enforces one lane per account and preserves the shared-account mode',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-pool-'));const pending=new Map();const sharedPending=[];const calls=[];
  const pool=await new MuseAccounts({profileRoot:root,createDriver:id=>({account:()=>({authenticated:true}),maxConcurrency:40,queue:[],progress:()=>[],close:async()=>{},generateImage:(data,signal)=>new Promise((resolve,reject)=>{calls.push({id,...data});if(data.singleLane)pending.set(id,resolve);else sharedPending.push(resolve);signal.addEventListener('abort',()=>reject(signal.reason),{once:true})})})}).load();
  try {
    const labels=Array.from({length:40},(_,i)=>`person${i+1}@example.invalid`);await pool.importLabels(labels);
    const restored=await new MuseAccounts({profileRoot:root}).load();assert.deepEqual(restored.labels,labels);
    await assert.rejects(pool.importLabels(['same','SAME']),/ACCOUNT_LIST_INVALID/);
    await assert.rejects(pool.importLabels(['email|password']),/ACCOUNT_LIST_INVALID/);
    assert.equal(pool.snapshot().length,40);
    const controls=Array.from({length:40},()=>new AbortController());
    const tasks=controls.map((control,i)=>pool.generateImage({accountId:i+1,accountMode:'multiple',prompt:`scene ${i+1}`},control.signal));
    const settled=Promise.allSettled(tasks);
    assert.equal(pool.usage.size,40);assert.equal(calls.length,40);
    assert.ok(calls.every(call=>call.accountId===1&&call.singleLane));
    await assert.rejects(pool.generateImage({accountId:5,accountMode:'multiple'},new AbortController().signal),/MUSE_ACCOUNT_BUSY/);
    await assert.rejects(pool.generateImage({accountId:1,accountMode:'single'},new AbortController().signal),/MUSE_ACCOUNT_BUSY/);
    controls[4].abort();for(const [id,resolve] of pending)if(id!==5)resolve({text:`account ${id}`});
    const results=await settled;assert.equal(results.filter(result=>result.status==='fulfilled').length,39);assert.equal(pool.usage.size,0);
    const shared=Array.from({length:40},()=>pool.generateImage({accountId:1,accountMode:'single'},new AbortController().signal));
    assert.equal(pool.usage.get(1).count,40);assert.ok(calls.slice(40).every(call=>call.id===1&&!call.singleLane));
    sharedPending.forEach(resolve=>resolve({}));await Promise.all(shared);assert.equal(pool.usage.size,0);
    assert.equal(pool.preferredConcurrency,2);pool.driver(1).setConcurrency=async count=>({executionConcurrency:count});await pool.setConcurrency(1,new AbortController().signal);const preference=await new MuseAccounts({profileRoot:root}).load();assert.equal(preference.preferredConcurrency,1);assert.equal((await preference.prepareSingle(new AbortController().signal)).executionConcurrency,1);
  } finally {await rm(root,{recursive:true,force:true})}
});

test('unsupported parallel conversations preserve the requested thirty lanes but allow a verified serial queue',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-shared-fallback-'));
  const driver={maxConcurrency:1,queue:[],account:()=>({authenticated:true}),progress:()=>[],setConcurrency:async()=>{throw new Error('MUSE_PARALLEL_UNVERIFIED: Shared chat only')},close:async()=>{}};
  const pool=new MuseAccounts({profileRoot:root,createDriver:()=>driver});
  try{
    const result=await pool.prepareSingle(new AbortController().signal,30);assert.equal(result.executionConcurrency,1);assert.equal(result.preferredConcurrency,30);assert.match(result.concurrencyWarning,/Shared chat/);
    const restored=await new MuseAccounts({profileRoot:root}).load();assert.equal(restored.preferredConcurrency,30);
    await pool.prepareSingle(new AbortController().signal,1);assert.equal(pool.concurrencyWarning,'');
    driver.setConcurrency=async()=>{throw Object.assign(new Error('MUSE_LOGIN_REQUIRED: Expired'),{status:401})};await assert.rejects(pool.prepareSingle(new AbortController().signal,40),/MUSE_LOGIN_REQUIRED/);
  }finally{await rm(root,{recursive:true,force:true})}
});

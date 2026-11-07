import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {MuseAccounts} from '../muse-accounts.mjs';

test('account pool isolates routing, enforces one lane per account and preserves the shared-account mode',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-pool-'));const pending=new Map();const sharedPending=[];const calls=[];
  const pool=await new MuseAccounts({profileRoot:root,createDriver:id=>({account:()=>({authenticated:true}),maxConcurrency:10,queue:[],progress:()=>[],close:async()=>{},generateImage:(data,signal)=>new Promise((resolve,reject)=>{calls.push({id,...data});if(data.singleLane)pending.set(id,resolve);else sharedPending.push(resolve);signal.addEventListener('abort',()=>reject(signal.reason),{once:true})})})}).load();
  try {
    const labels=Array.from({length:10},(_,i)=>`person${i+1}@example.invalid`);await pool.importLabels(labels);
    const restored=await new MuseAccounts({profileRoot:root}).load();assert.deepEqual(restored.labels,labels);
    await assert.rejects(pool.importLabels(['same','SAME']),/ACCOUNT_LIST_INVALID/);
    await assert.rejects(pool.importLabels(['email|password']),/ACCOUNT_LIST_INVALID/);
    assert.equal(pool.snapshot().length,10);
    const controls=Array.from({length:10},()=>new AbortController());
    const tasks=controls.map((control,i)=>pool.generateImage({accountId:i+1,accountMode:'multiple',prompt:`scene ${i+1}`},control.signal));
    const settled=Promise.allSettled(tasks);
    assert.equal(pool.usage.size,10);assert.equal(calls.length,10);
    assert.ok(calls.every(call=>call.accountId===1&&call.singleLane));
    await assert.rejects(pool.generateImage({accountId:5,accountMode:'multiple'},new AbortController().signal),/MUSE_ACCOUNT_BUSY/);
    await assert.rejects(pool.generateImage({accountId:1,accountMode:'single'},new AbortController().signal),/MUSE_ACCOUNT_BUSY/);
    controls[4].abort();for(const [id,resolve] of pending)if(id!==5)resolve({text:`account ${id}`});
    const results=await settled;assert.equal(results.filter(result=>result.status==='fulfilled').length,9);assert.equal(pool.usage.size,0);
    const shared=Array.from({length:10},()=>pool.generateImage({accountId:1,accountMode:'single'},new AbortController().signal));
    assert.equal(pool.usage.get(1).count,10);assert.ok(calls.slice(10).every(call=>call.id===1&&!call.singleLane));
    sharedPending.forEach(resolve=>resolve({}));await Promise.all(shared);assert.equal(pool.usage.size,0);
    assert.equal(pool.preferredConcurrency,2);pool.driver(1).setConcurrency=async count=>({executionConcurrency:count});await pool.setConcurrency(1,new AbortController().signal);const preference=await new MuseAccounts({profileRoot:root}).load();assert.equal(preference.preferredConcurrency,1);assert.equal((await preference.prepareSingle(new AbortController().signal)).executionConcurrency,1);
  } finally {await rm(root,{recursive:true,force:true})}
});

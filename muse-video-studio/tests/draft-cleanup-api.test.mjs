import{test}from'node:test';
import assert from'node:assert/strict';
import{mkdtemp,rm}from'node:fs/promises';
import os from'node:os';
import path from'node:path';
import{MuseAccounts}from'../muse-accounts.mjs';
import{startStudioServer}from'../server.mjs';
import{errorInfo}from'../src/core.ts';
async function until(fn){const end=Date.now()+3000;while(!fn()){if(Date.now()>end)throw Error('Draft cleanup fixture timed out');await new Promise(resolve=>setTimeout(resolve,10))}}
function fakePool(root,{clear,generate}={}){return new MuseAccounts({profileRoot:root,createDriver:id=>({maxConcurrency:6,queue:[],progress:()=>[],account:()=>({authenticated:true,sessionAuthenticated:true}),refreshActive:async()=>{},close:async()=>{},clearToolDraft:async(data,signal)=>clear?clear(id,data,signal):{cleared:true,acknowledged:false,message:'Exact old tool draft cleared'},generateVideo:async(data,signal)=>generate?generate(id,data,signal):{base64:'YWJj',mimeType:'video/mp4'}})})}

test('Cleanup reserves only its own account, remaps driver account and never submits a generation',{timeout:10000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-draft-account-')),calls=[];let releaseCleanup;let releaseVideo;
 const pool=fakePool(root,{clear:async(id,data)=>{calls.push({id,data});await new Promise(resolve=>releaseCleanup=resolve);return{cleared:false,acknowledged:true,message:'Already received'}},generate:async id=>{if(id===1)await new Promise(resolve=>releaseVideo=resolve);return{base64:'YWJj',mimeType:'video/mp4'}}});
 const control=new AbortController();let running,cleaning;
 try{
  running=pool.generateVideo({accountId:1,sceneId:1},control.signal);await until(()=>Boolean(releaseVideo));
  await assert.rejects(pool.clearToolDraft({accountId:1,prompt:'Exact target prompt',output:'video'},control.signal),/MUSE_CHAT_BUSY/);
  cleaning=pool.clearToolDraft({accountId:2,prompt:'Exact target prompt',output:'video'},control.signal);await until(()=>Boolean(releaseCleanup));
  assert.deepEqual(calls,[{id:2,data:{accountId:1,prompt:'Exact target prompt',output:'video'}}]);assert.equal(pool.usage.get(2).exclusive,true);
  await assert.rejects(pool.clearToolDraft({accountId:2,prompt:'Exact target prompt',output:'video'},control.signal),/MUSE_CHAT_BUSY/);
  assert.equal((await pool.generateVideo({accountId:3,sceneId:3},control.signal)).mimeType,'video/mp4','Other accounts must remain runnable');
  releaseCleanup();assert.equal((await cleaning).acknowledged,true);assert.equal(pool.usage.has(2),false);assert.equal(calls.length,1);
  releaseVideo();await running;assert.equal(pool.usage.size,0);
 }finally{releaseCleanup?.();releaseVideo?.();control.abort();await Promise.allSettled([running,cleaning].filter(Boolean));await pool.close();await rm(root,{recursive:true,force:true})}
});

test('HTTP cleanup validates exact inputs and excludes only the target account while other accounts render',{timeout:15000},async()=>{
 const old=process.env.MUSE_TRANSPORT;process.env.MUSE_TRANSPORT='browser';
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-draft-http-')),calls=[];let releaseCleanup,releaseVideo;
 const pool=fakePool(root,{clear:async(id,data)=>{calls.push({id,data});await new Promise(resolve=>releaseCleanup=resolve);return{cleared:true,acknowledged:false,message:'Cleared without Enter'}},generate:async id=>{if(id===1)await new Promise(resolve=>releaseVideo=resolve);return{base64:'YWJj',mimeType:'video/mp4'}}});
 const runtime=await startStudioServer({museDriver:pool,port:0});const post=(route,data)=>fetch(runtime.url+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const video={accountId:1,accountMode:'multiple',prompt:'A river.',model:'Omni 1.1 Flash',duration:4,aspectRatio:'16:9',resolution:'720p'};let running,cleaning;
 try{
  for(const data of [null,{prompt:'A river.',output:'video'},{accountId:41,prompt:'A river.',output:'video'},{accountId:2,prompt:'',output:'video'},{accountId:2,prompt:'A river.',output:'text'},{accountId:2,prompt:'A river.',output:'video',force:true}])assert.equal((await post('/api/account/clear-tool-draft',data)).status,400);
  assert.equal(calls.length,0);
  running=post('/api/video',video);await until(()=>Boolean(releaseVideo));
  assert.equal((await post('/api/account/clear-tool-draft',{accountId:1,prompt:video.prompt,output:'video'})).status,409);
  cleaning=post('/api/account/clear-tool-draft',{accountId:2,prompt:video.prompt,output:'video'});await until(()=>Boolean(releaseCleanup));
  const status=await(await fetch(runtime.url+'/api/status')).json();assert.equal(status.canClearToolDraft,true);assert.deepEqual(status.cleaningDraftAccounts,[2]);
  assert.equal((await post('/api/video',{...video,accountId:2})).status,409);assert.equal((await post('/api/account/prepare',{accountId:2,concurrency:6})).status,409);
  assert.equal((await post('/api/video',{...video,accountId:3})).status,200,'Cleanup must not set the global accountBusy flag');
  releaseCleanup();const response=await cleaning;assert.equal(response.status,200);const result=await response.json();assert.equal(result.cleared,true);assert.equal(result.acknowledged,false);assert.deepEqual(calls,[{id:2,data:{accountId:1,prompt:video.prompt,output:'video'}}]);
  assert.deepEqual((await(await fetch(runtime.url+'/api/status')).json()).cleaningDraftAccounts,[]);
  releaseVideo();assert.equal((await running).status,200);
 }finally{releaseCleanup?.();releaseVideo?.();await Promise.allSettled([running,cleaning].filter(Boolean));await runtime.close();await rm(root,{recursive:true,force:true});if(old===undefined)delete process.env.MUSE_TRANSPORT;else process.env.MUSE_TRANSPORT=old}
});

test('Draft-specific hints identify cleanup and acknowledged recovery instead of a generic connection fault',()=>{
 assert.match(errorInfo('MUSE_DRAFT_EXISTS: Ô Message ban đầu đang có bản nháp.').hint,/Dọn bản nháp tool/);
 assert.match(errorInfo('MUSE_DRAFT_ACKNOWLEDGED: already accepted').hint,/Nhận lại từ Muse/);
 assert.match(errorInfo('MUSE_DRAFT_UNCERTAIN: Enter attempted').hint,/Nhận lại từ Muse/);
});

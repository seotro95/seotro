import{test}from'node:test';import assert from'node:assert/strict';
import{readFile,mkdtemp,rm}from'node:fs/promises';import os from'node:os';import path from'node:path';
import{chromium}from'playwright-core';import{MuseBrowser}from'../muse-browser.mjs';import{MuseAccounts}from'../muse-accounts.mjs';import{createMuseFixture}from'./fixtures/muse.mjs';
const image=await readFile(new URL('../public/demo-image.png',import.meta.url)),clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
async function until(fn){const end=Date.now()+10000;while(!await fn()){if(Date.now()>end)throw Error('Saved batch state timed out');await new Promise(r=>setTimeout(r,30))}}
test('five separate native cards with late captions complete concurrently and can be recovered without Enter, a new chat, a generation request or a draft change',{timeout:45000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-saved-batch-'));const fixture=createMuseFixture({image,clip});Object.assign(fixture.state,{newChat:false,behavior:'video',hold:true,uniqueVideos:true,omitAttribution:true,labelReplies:true,separateCaptions:true,captionDelayMs:3300,lazyVideo:true});await new Promise(r=>fixture.server.listen(0,'127.0.0.1',r));
 const driver=new MuseBrowser({profileRoot:root,serviceURL:`http://127.0.0.1:${fixture.server.address().port}/`,launchOptions:{executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true},pollMs:40,timeoutMs:15000});const pool=new MuseAccounts({profileRoot:root,createDriver:()=>driver});const control=new AbortController();let all;
 try{
  await pool.connect(1);await driver.active.page.getByRole('button',{name:'Fixture login',exact:true}).click();await driver.refreshActive();await pool.prepareSingle(control.signal,5,1);
  const batchId=crypto.randomUUID(),submissionGroup={id:crypto.randomUUID(),size:5};const requests=Array.from({length:5},(_,i)=>({accountId:1,sceneId:i+1,batchId,submissionGroup,prompt:'Saved landscape '+(i+1),modelDisplayName:'Omni 1.1 Flash',durationSeconds:10,resolution:'1080p',aspectRatio:'16:9'}));
  all=Promise.all(requests.map(data=>pool.generateVideo(data,control.signal)));await until(()=>fixture.state.pending.size===5);assert.equal(fixture.state.chatMessages.length,1);assert.equal(fixture.state.peak,5);
  for(const release of [...fixture.state.pending.values()].reverse())release();const results=await all;assert.equal(results.length,5);assert.equal(driver.maxConcurrency,5,'Attribution must not lower working concurrency to one');
  const editor=driver.active.page.locator('#fixture-editor');await editor.fill('Keep this unrelated unsent draft');
  const before={messages:fixture.state.chatMessages.length,submitted:fixture.state.submitted.length,pages:driver.active.page.context().pages().length};
  const recovered=await Promise.all(requests.map(data=>pool.recoverMedia({...data,output:'video'},control.signal)));
  for(let i=0;i<5;i++)assert.equal(recovered[i].base64,results[i].base64,'Exact original file must return to its original scene');
  assert.equal(fixture.state.chatMessages.length,before.messages);assert.equal(fixture.state.submitted.length,before.submitted);assert.equal(driver.active.page.context().pages().length,before.pages);assert.equal(await editor.inputValue(),'Keep this unrelated unsent draft');assert.equal(pool.usage.size,0);
  await assert.rejects(pool.recoverMedia({...requests[0],prompt:'Changed prompt must not recover somebody else’s result',output:'video'},control.signal),/MUSE_RECOVER_HISTORY_MISSING/);
  assert.equal(fixture.state.submitted.length,5);assert.ok(driver.progress().filter(x=>x.phase==='done'&&x.observation?.recoveryOnly).every(x=>x.observation.messagesSent===0));
 }finally{control.abort();fixture.releaseAll();if(all)await all.catch(()=>{});await pool.close();fixture.server.closeAllConnections();await new Promise(r=>fixture.server.close(r));await rm(root,{recursive:true,force:true})}
});

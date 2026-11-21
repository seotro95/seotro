import{test}from'node:test';
import assert from'node:assert/strict';
import{readFile,mkdtemp,rm}from'node:fs/promises';
import os from'node:os';import path from'node:path';
import{chromium}from'playwright-core';
import{MuseBrowser}from'../muse-browser.mjs';import{MuseAccounts}from'../muse-accounts.mjs';
import{createMuseFixture}from'./fixtures/muse.mjs';
const image=await readFile(new URL('../public/demo-image.png',import.meta.url)),clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
async function setup(flags,driverOptions={}){
 const profile=await mkdtemp(path.join(os.tmpdir(),'muse-owned-draft-')),fixture=createMuseFixture({image,clip});
 Object.assign(fixture.state,{newChat:false,behavior:'video',uniqueVideos:true,prehydrationInput:true,richComposer:true,labelReplies:true,initialMode:'input'},flags);
 await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));
 const service=`http://127.0.0.1:${fixture.server.address().port}/`,driver=new MuseBrowser({profileRoot:profile,serviceURL:service,launchOptions:{executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true},pollMs:25,replyQuietMs:100,timeoutMs:12000,...driverOptions});
 const pool=new MuseAccounts({profileRoot:profile,createDriver:()=>driver}),control=new AbortController();
 await pool.connect(1);await driver.active.page.getByRole('button',{name:'Fixture login',exact:true}).click();await driver.refreshActive();
 const page=driver.active.page,loads=()=>fixture.state.pageLoads||0;
 return{profile,fixture,driver,pool,control,page,loads,async close(){control.abort();fixture.releaseAll();await pool.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(profile,{recursive:true,force:true})}};
}
const request=(sceneId,sourceClip,batchId,submissionGroup)=>({accountId:1,sceneId,batchId,submissionGroup,prompt:`CLIP ${String(sourceClip).padStart(3,'0')} — 10 seconds. MAIN TIMELINE SCENE ${String(sourceClip).padStart(3,'0')}.\nVISUAL: Distinct conceptual terrain model ${sourceClip}, no lettering.\nAUDIO: Video không có âm thanh, không có lời nói.\nEXCLUSIONS: Không có hình trẻ em.`,modelDisplayName:'Omni 1.1 Flash',durationSeconds:10,resolution:'1080p',aspectRatio:'16:9'});
async function draftSnapshot(page){return page.evaluate(()=>({fields:[...document.querySelectorAll('textarea,[contenteditable="true"]')].map(node=>({id:node.id,text:node.tagName==='TEXTAREA'?node.value:node.innerText,display:node.style.display})),files:[...document.querySelector('input[type=file]').files].map(file=>({name:file.name,size:file.size,type:file.type})),attachments:[...document.querySelectorAll('#attachments img')].map(node=>node.src),userTurns:document.querySelectorAll('[data-message-role="user"]').length}))}

for(const stale of ['prefix','full'])test(`Three six-video waves reuse the same hydrated conversation when a ${stale} tool draft returns in its placeholder`,{timeout:50000},async()=>{
 const s=await setup({resetComposerAfterTurn:true,stalePrehydration:stale,retainDraftAfterSubmit:stale==='full',sourceClipLabels:true,omitAttribution:true,separateCaptions:true,labelOnly:true,lazyVideo:true});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);const before=s.loads(),batchId=crypto.randomUUID();
  for(const wave of [0,1,2]){
   const group={id:crypto.randomUUID(),size:6},tasks=Array.from({length:6},(_,index)=>request(index+1,56+wave*6+index,batchId,group));
   const results=await Promise.allSettled(tasks.map(data=>s.pool.generateVideo(data,s.control.signal)));
   for(let index=0;index<6;index++){
    assert.equal(results[index].status,'fulfilled',results[index].reason?.message);
    const original=s.fixture.state.submitted.find(row=>row.prompt.includes(tasks[index].prompt));
    const bytes=Buffer.from(results[index].value.base64,'base64');assert.equal(bytes.readUInt32BE(bytes.length-4),original.id,'Every original CLIP must receive its own generated file');
   }
   assert.equal(s.fixture.state.chatMessages.length,wave+1);assert.equal(s.fixture.state.submitted.length,(wave+1)*6);
   if(wave===0)await s.page.evaluate(()=>window.history.pushState(null,'','/chat/accepted-tool-turn'));
  }
  const resets=await s.page.evaluate(()=>window.fixtureComposerResets);
  assert.equal(resets.length,3);assert.equal(resets[0].prehydrationValue,stale==='full'?s.fixture.state.chatMessages[0].prompt:'[');
  assert.equal(s.loads(),before,'Recovering an owned draft must not reload the Muse page');
  assert.equal(s.page.context().pages().length,1);assert.equal(s.driver.maxConcurrency,6);assert.equal(s.fixture.state.stops,0);
 }finally{await s.close()}
});

test('An unsent tool message left in a functional placeholder after cancellation can be replaced without submitting that old draft',{timeout:25000},async()=>{
 const s=await setup({initialMode:'functional'});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);const before=s.loads(),cancelled=new AbortController();
  const owned='[studio-request-owned-unsent] This exact tool message was entered but never submitted.';
  await s.driver.writeMessage(s.page,owned,cancelled.signal);cancelled.abort(Error('Cancelled before Enter'));
  assert.equal(await s.page.locator('[data-hatch-composer-prehydration-input]').inputValue(),owned);
  assert.equal(s.fixture.state.submitted.length,0);
  const batchId=crypto.randomUUID(),group={id:crypto.randomUUID(),size:6},tasks=Array.from({length:6},(_,index)=>request(index+1,56+index,batchId,group));
  const results=await Promise.allSettled(tasks.map(data=>s.pool.generateVideo(data,s.control.signal)));
  assert.ok(results.every(row=>row.status==='fulfilled'),results.filter(row=>row.status==='rejected').map(row=>row.reason.message).join('\n'));
  assert.equal(s.fixture.state.chatMessages.length,1);assert.equal(s.fixture.state.submitted.length,6);
  assert.equal(s.fixture.state.chatMessages[0].prompt.includes(owned),false);assert.equal(s.loads(),before);
 }finally{await s.close()}
});

for(const fresh of [true,false])test(`${fresh?'A fresh user placeholder draft':'A user-edited tool draft'} and its attachment are preserved exactly without Enter or reload`,{timeout:25000},async()=>{
 const s=await setup({initialMode:'functional'});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);
  const placeholder=s.page.locator('[data-hatch-composer-prehydration-input]');
  if(!fresh)await s.driver.writeMessage(s.page,'[owned-tool-text] Previously entered by the tool.',s.control.signal);
  await placeholder.fill(fresh?'[':'[owned-tool-text] User changed this exact text.');
  await s.page.locator('input[type=file]').setInputFiles({name:'user-reference.png',mimeType:'image/png',buffer:image});
  const before=await draftSnapshot(s.page),loads=s.loads();
  const batchId=crypto.randomUUID(),group={id:crypto.randomUUID(),size:6};
  const outcomes=await Promise.allSettled(Array.from({length:6},(_,index)=>s.pool.generateVideo(request(index+1,56+index,batchId,group),s.control.signal)));
  assert.ok(outcomes.every(row=>row.status==='rejected'&&/MUSE_DRAFT_EXISTS|MUSE_DRAFT_CHANGED/.test(row.reason.message)),outcomes.map(row=>row.reason?.message||row.status).join('\n'));
  assert.deepEqual(await draftSnapshot(s.page),before);assert.equal(s.loads(),loads);assert.equal(s.fixture.state.submitted.length,0);assert.equal(s.fixture.state.chatMessages?.length||0,0);assert.equal(s.fixture.state.initialEnterEvents||0,0);
 }finally{await s.close()}
});

test('A user retyping the exact former tool text without attachments revokes automatic ownership',{timeout:20000},async()=>{
 const s=await setup({initialMode:'functional'});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);
  const text='[studio-request-'+crypto.randomUUID()+'] Exact former tool text now retyped by the user.';
  await s.driver.writeMessage(s.page,text,s.control.signal);
  const editor=s.page.locator('[data-hatch-composer-prehydration-input]');
  await editor.evaluate(node=>node.addEventListener('input',event=>{window.fixtureUserRetypeTrusted=event.isTrusted},{once:true}));
  await editor.fill('');await editor.fill(text);
  assert.equal(await s.page.evaluate(()=>window.fixtureUserRetypeTrusted),true,'Use genuine browser input, not a synthetic DOM assignment');
  const before=await draftSnapshot(s.page),loads=s.loads();
  await assert.rejects(s.pool.generateVideo(request(1,56,crypto.randomUUID(),{id:crypto.randomUUID(),size:1}),s.control.signal),/MUSE_DRAFT_EXISTS|MUSE_DRAFT_CHANGED/);
  assert.deepEqual(await draftSnapshot(s.page),before);assert.equal(s.loads(),loads);assert.equal(s.fixture.state.submitted.length,0);
 }finally{await s.close()}
});

test('The exact old tool text in a fresh document has no automatic ownership',{timeout:20000},async()=>{
 const s=await setup({initialMode:'functional'});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);
  const text='[studio-request-'+crypto.randomUUID()+'] Same text belongs to a new document after reload.';
  await s.driver.writeMessage(s.page,text,s.control.signal);
  await s.page.reload();await s.page.locator('[data-hatch-composer-prehydration-input]').fill(text);
  const before=await draftSnapshot(s.page),loads=s.loads();
  await assert.rejects(s.pool.generateVideo(request(1,56,crypto.randomUUID(),{id:crypto.randomUUID(),size:1}),s.control.signal),/MUSE_DRAFT_EXISTS|MUSE_DRAFT_CHANGED/);
  assert.deepEqual(await draftSnapshot(s.page),before);assert.equal(s.loads(),loads,'There must be no second, automatic page reload');assert.equal(s.fixture.state.submitted.length,0);
 }finally{await s.close()}
});

test('An Enter attempt without an acknowledged user turn cannot clear its draft or issue another Enter',{timeout:20000},async()=>{
 const s=await setup({initialMode:'inert'},{submitTimeoutMs:350,timeoutMs:2500});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);
  const data=request(1,56,crypto.randomUUID(),{id:crypto.randomUUID(),size:1});
  await assert.rejects(s.pool.generateVideo(data,s.control.signal),/MUSE_SUBMIT_NOT_ACKNOWLEDGED/);
  assert.equal(s.fixture.state.initialEnterEvents,1);assert.equal(s.fixture.state.submitted.length,0);
  const before=await draftSnapshot(s.page),loads=s.loads();
  assert.equal(before.userTurns,0);assert.ok(before.fields.some(field=>field.text.includes('studio-batch-')));
  await assert.rejects(s.pool.generateVideo({...data,submissionGroup:{id:crypto.randomUUID(),size:1}},s.control.signal),/MUSE_DRAFT_UNCERTAIN/);
  assert.deepEqual(await draftSnapshot(s.page),before);assert.equal(s.loads(),loads);assert.equal(s.fixture.state.initialEnterEvents,1);assert.equal(s.fixture.state.submitted.length,0);
 }finally{await s.close()}
});

test('Trusted user clearing the field during the prefix pause stops the tool without refilling or Enter',{timeout:20000},async()=>{
 const s=await setup({initialMode:'functional'});
 try{
  await s.pool.prepareSingle(s.control.signal,6,1);
  const text='[studio-request-'+crypto.randomUUID()+'] Do not overwrite a user clearing this field.';
  const writing=s.driver.writeMessage(s.page,text,s.control.signal).then(()=>({error:null}),error=>({error:error.message}));
  await s.page.waitForFunction(()=>document.querySelector('[data-hatch-composer-prehydration-input]').value==='[',null,{polling:1});
  const editor=s.page.locator('[data-hatch-composer-prehydration-input]');
  await editor.evaluate(node=>node.addEventListener('input',event=>{window.fixtureUserClearTrusted=event.isTrusted},{once:true}));
  await editor.fill('');
  const result=await writing;
  assert.match(result.error||'',/MUSE_DRAFT_CHANGED|MUSE_DRAFT_EXISTS/);
  assert.equal(await s.page.evaluate(()=>window.fixtureUserClearTrusted),true);
  assert.equal(await editor.inputValue(),'','The tool must preserve the user-cleared empty field');
  assert.equal(s.fixture.state.submitted.length,0);assert.equal(s.fixture.state.chatMessages?.length||0,0);assert.equal(s.fixture.state.initialEnterEvents||0,0);
 }finally{await s.close()}
});

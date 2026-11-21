import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
import {chromium} from 'playwright-core';
import {MuseBrowser} from '../muse-browser.mjs';
import {legacyToolDraft,batchMessageHeader,videoGenerationPrompt,imageGenerationPrompt} from '../muse-drafts.mjs';
import {createMuseFixture} from './fixtures/muse.mjs';
const marker='studio-batch-12345678-1234-1234-1234-123456789012';
const scenes=['CLIP 057 — A quiet forest teaching model.','CLIP 058 — A measured low terrain model.'];
const videoData={modelDisplayName:'Omni 1.1 Flash',durationSeconds:10,aspectRatio:'16:9',resolution:'1080p',characterLock:false};
function envelope({output='video',common=true}={}){
 const builder=output==='video'?videoGenerationPrompt:imageGenerationPrompt;
 const data=output==='video'?videoData:{resolution:'2k',aspectRatio:'16:9',characterLock:false};
 const head=builder({...data,prompt:''}).split('\nScene:\n')[0];
 const tasks=scenes.map((scene,i)=>`[BEGIN_CLIP CLIP_${57+i}_12345678 MUSE_${String(i+1).repeat(32)}]\n${common?scene:builder({...data,prompt:scene})}\n[END_CLIP MUSE_${String(i+1).repeat(32)}]`).join('\n\n');
 // Production scene labels are always padded to three digits.
 return batchMessageHeader({marker,count:2,output,common:common?head:''})+tasks.replace(/CLIP_57_/g,'CLIP_057_').replace(/CLIP_58_/g,'CLIP_058_');
}
test('Legacy recovery accepts complete old batch and worker envelopes with exact original scene and canonical generation instructions',()=>{
 for(const output of ['video','image'])for(const common of [true,false]){const message=envelope({output,common});assert.equal(legacyToolDraft(message,scenes[1],output)?.marker,marker);assert.equal(legacyToolDraft(message.replace(/\n\n/g,'\n\n\n'),scenes[1],output)?.marker,marker);}
 const single=videoGenerationPrompt({...videoData,prompt:scenes[1]})+'\n\n[Request marker: studio-request-12345678-1234-1234-1234-123456789012. Do not include this marker in your reply.]';
 assert.equal(legacyToolDraft(single,scenes[1],'video')?.kind,'single');
 assert.equal(legacyToolDraft(single.replace('Requested duration: 10 seconds','Requested duration: 10 seconds; my private notes'),scenes[1],'video'),null);
});
test('A marker, changed instructions, foreign tokens, incomplete blocks and modified scene are not legacy ownership',()=>{
 const message=envelope();
 for(const invalid of ['[','MUSE_'+ '1'.repeat(32),message+'\nMy personal notes',message.replace('Create 2 independent','Create 3 independent'),message.replace('CLIP_058_12345678','CLIP_058_deadbeef'),message.replace('Requested duration: 10 seconds','Requested duration: 10 seconds; edited instructions'),message.replace(scenes[1],scenes[1]+' My notes'),message.replace('Do not just write a plan','My notes. Do not just write a plan')])assert.equal(legacyToolDraft(invalid,scenes[1],'video'),null,invalid.slice(0,90));
 assert.equal(legacyToolDraft(message,'An unrelated scene','video'),null);
 assert.equal(legacyToolDraft(message,scenes[1],'image'),null);
});
for(const acknowledged of [false,true])test(`Explicit legacy cleanup clears the exact old batch without Enter; acknowledged=${acknowledged}`,{timeout:25000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-legacy-draft-'));
 const image=await readFile(new URL('../public/demo-image.png',import.meta.url)),clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
 const fixture=createMuseFixture({image,clip});Object.assign(fixture.state,{newChat:false,prehydrationInput:true,initialMode:'functional',richComposer:true});await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));
 const driver=new MuseBrowser({profileRoot:root,serviceURL:`http://127.0.0.1:${fixture.server.address().port}/`,launchOptions:{executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true},pollMs:25});
 try{
  await driver.connect(1);const page=driver.active.page;await page.getByRole('button',{name:'Fixture login',exact:true}).click();await driver.refreshActive();const editor=page.locator('[data-hatch-composer-prehydration-input]'),message=envelope();
  await editor.fill(message);if(acknowledged)await page.evaluate(text=>{const user=document.createElement('div');user.dataset.messageItem='';user.dataset.messageRole='user';user.textContent=text;document.getElementById('history').appendChild(user)},message);
  const before=fixture.state.pageLoads;const result=await driver.clearToolDraft({prompt:scenes[1],output:'video'},new AbortController().signal);
  assert.equal(result.cleared,true);assert.equal(result.acknowledged,acknowledged);assert.equal(await editor.inputValue(),'');assert.equal(fixture.state.submitted.length,0);assert.equal(fixture.state.initialEnterEvents||0,0);assert.equal(fixture.state.pageLoads,before);
  await editor.fill(message);
  if(acknowledged){const previous=await driver.clearToolDraft({prompt:'An unrelated next scene.',output:'video'},new AbortController().signal);assert.equal(previous.cleared,true);assert.equal(previous.acknowledged,false);assert.equal(previous.previousAcknowledged,true);}
  else{await assert.rejects(driver.clearToolDraft({prompt:'An unrelated next scene.',output:'video'},new AbortController().signal),/MUSE_DRAFT_NOT_OWNED/);assert.equal(await editor.inputValue(),message);}
  await editor.fill(message+'\nPersonal changes');await assert.rejects(driver.clearToolDraft({prompt:scenes[1],output:'video'},new AbortController().signal),/MUSE_DRAFT_NOT_OWNED/);assert.equal(await editor.inputValue(),message+'\nPersonal changes');
  await editor.fill(message);await page.locator('input[type=file]').setInputFiles({name:'keep.png',mimeType:'image/png',buffer:image});await assert.rejects(driver.clearToolDraft({prompt:scenes[1],output:'video'},new AbortController().signal),/MUSE_DRAFT_CHANGED/);assert.equal(await editor.inputValue(),message);assert.equal(await page.locator('input[type=file]').evaluate(input=>input.files.length),1);assert.equal(fixture.state.submitted.length,0);
 }finally{await driver.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(root,{recursive:true,force:true})}
});

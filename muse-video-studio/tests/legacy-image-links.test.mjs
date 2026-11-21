import{test}from'node:test';
import assert from'node:assert/strict';
import{readFile,mkdtemp,rm}from'node:fs/promises';
import path from'node:path';
import os from'node:os';
import{chromium}from'playwright-core';
import{MuseBrowser}from'../muse-browser.mjs';
import{createMuseFixture}from'./fixtures/muse.mjs';

const image=await readFile(new URL('../public/demo-image.png',import.meta.url));
const clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
async function withDriver(flags,run,{timeoutMs=10000,filenameOnly=false}={}){
 const profile=await mkdtemp(path.join(os.tmpdir(),'muse-legacy-image-'));
 const fixture=createMuseFixture({image,clip});
 Object.assign(fixture.state,{behavior:'image',extensionlessImage:true,extensionlessLinkText:'View image',...flags});
 await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));
 const driver=new MuseBrowser({profileRoot:profile,serviceURL:`http://127.0.0.1:${fixture.server.address().port}/`,launchOptions:{executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true},pollMs:25,replyQuietMs:100,timeoutMs});
 const control=new AbortController();
 try{
  await driver.connect(1,{show:false});
  await driver.active.page.getByRole('button',{name:'Fixture login',exact:true}).click();await driver.refreshActive();
  // Exercise the actual default worker path, without MuseAccounts.prepareSingle
  // or useSharedConversation switching the driver to batched DOM inspection.
  assert.equal(driver.parallelStrategy,'workers');assert.equal(driver.maxConcurrency,1);
  if(filenameOnly)await driver.active.context.addInitScript(()=>{
   // Model a provider's extensionless URL labelled only by its download name.
   new MutationObserver(()=>{for(const link of document.querySelectorAll('a[href^="/asset-file?"]'))link.download='portrait.png'}).observe(document,{subtree:true,childList:true});
  });
  await run(driver,fixture,control.signal);
  assert.equal(driver.parallelStrategy,'workers');
  assert.ok(fixture.state.chatMessages.every(row=>row.prompt.includes('Request marker: studio-request-')&&!row.prompt.includes('[BEGIN_CLIP ')),'Requests must execute sendOneTurn rather than the shared batch path');
 }finally{control.abort();fixture.releaseAll();await driver.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(profile,{recursive:true,force:true})}
}
for(const name of ['View image','Open image'])test(`Default single worker receives two distinct extensionless files labelled ${name}`,{timeout:30000},()=>withDriver({extensionlessLinkText:name},async(driver,fixture,signal)=>{
 const batchId=crypto.randomUUID(),results=[];
 for(const sceneId of [1,2]){
  const prompt=`A photorealistic portrait of a distinct mature adult, original scene ${sceneId}.`;
  const result=await driver.generateImage({accountId:1,sceneId,batchId,prompt,aspectRatio:'16:9',resolution:'2k',characterLock:false},signal);
  const source=fixture.state.submitted.find(row=>row.prompt.includes(prompt));
  assert.equal(result.base64,fixture.state.outputs.get(source.id),'The actual generated file must match this prompt');
  assert.equal(result.mimeType,'image/png');assert.equal(result.metadata.width,640);assert.equal(result.metadata.height,360);
  results.push(result);
 }
 assert.notEqual(results[0].base64,results[1].base64);assert.equal(fixture.state.submitted.length,2);assert.equal(fixture.state.chatMessages.length,2);
 assert.ok(driver.progress().every(row=>row.observation?.replyScope==='conversation'));
}));

test('Default worker recognizes an image filename in download even when URL and visible text have no media hint',{timeout:30000},()=>withDriver({extensionlessLinkText:'Result'},async(driver,fixture,signal)=>{
 const result=await driver.generateImage({accountId:1,sceneId:1,batchId:crypto.randomUUID(),prompt:'A mature adult studio portrait with an opaque file URL.',aspectRatio:'16:9',resolution:'2k',characterLock:false},signal);
 assert.equal(result.base64,fixture.state.outputs.get(1));assert.equal(result.mimeType,'image/png');assert.equal(fixture.state.submitted.length,1);
},{filenameOnly:true}));

test('Default worker does not turn a ready message with no file into an image or generate a replacement',{timeout:15000},()=>withDriver({behavior:'reply',replyText:'Your image is ready. 2048 × 1152 pixels.'},async(driver,fixture,signal)=>{
 await assert.rejects(driver.generateImage({accountId:1,sceneId:1,batchId:crypto.randomUUID(),prompt:'A mature adult portrait.',aspectRatio:'16:9',resolution:'2k',characterLock:false},signal),/MUSE_TIMEOUT|MUSE_NO_IMAGE/);
 assert.equal(fixture.state.submitted.length,1);assert.equal(fixture.state.chatMessages.length,1);assert.equal(fixture.state.outputs.size,0);
 assert.equal(driver.progress().at(-1).observation.visibleImages,0);
},{timeoutMs:1200}));

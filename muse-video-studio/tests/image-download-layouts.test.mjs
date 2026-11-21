import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {chromium} from 'playwright-core';
import {MuseBrowser} from '../muse-browser.mjs';
import {MuseAccounts} from '../muse-accounts.mjs';
import {createMuseFixture} from './fixtures/muse.mjs';

const image=await readFile(new URL('../public/demo-image.png',import.meta.url));
const clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
for(const layout of ['view-image','view-image-before','view-image-after','button-before','button-after'])test(`Receive and recover two images from ${layout} without creating replacements`,{timeout:30000},async()=>{
 const profile=await mkdtemp(path.join(os.tmpdir(),'muse-image-layout-'));
 const fixture=createMuseFixture({image,clip});
 const button=layout.startsWith('button');
 Object.assign(fixture.state,{behavior:'image',newChat:false,labelReplies:true,
  nativeImageDownload:button,nativeDownloadButton:button,requireTrustedDownload:button,
  extensionlessImage:!button,extensionlessLinkText:'View image',
  separateCaptions:layout!=='view-image',labelBeforeMedia:layout.endsWith('before')});
 await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));
 const service=`http://127.0.0.1:${fixture.server.address().port}/`;
 const driver=new MuseBrowser({profileRoot:profile,serviceURL:service,
  launchOptions:{executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true},
  pollMs:25,replyQuietMs:80,timeoutMs:14000});
 const pool=new MuseAccounts({profileRoot:profile,createDriver:()=>driver});
 const control=new AbortController();
 try{
  await pool.connect(1);
  await driver.active.page.getByRole('button',{name:'Fixture login',exact:true}).click();
  await driver.refreshActive();await pool.prepareSingle(control.signal,2,1);
  const batchId=crypto.randomUUID(),submissionGroup={id:crypto.randomUUID(),size:2};
  const data=[1,2].map(sceneId=>({accountId:1,batchId,submissionGroup,sceneId,
   prompt:`Distinct mature adult portrait number ${sceneId}.`,aspectRatio:'16:9',resolution:'2k',characterLock:false}));
  const results=await Promise.all(data.map(row=>pool.generateImage(row,control.signal)));
  for(let i=0;i<results.length;i++){
   const source=fixture.state.submitted.find(row=>row.prompt.includes(data[i].prompt));
   assert.equal(results[i].base64,fixture.state.outputs.get(source.id));
   assert.equal(results[i].mimeType,'image/png');
   assert.ok(results[i].metadata.width>=128);assert.ok(results[i].metadata.height>=128);
  }
  assert.equal(fixture.state.chatMessages.length,1);assert.equal(fixture.state.submitted.length,2);
  await driver.active.page.locator('#fixture-editor').fill('Preserve this unsent draft');
  const recovered=await pool.recoverMedia({...data[1],output:'image'},control.signal);
  assert.equal(recovered.base64,results[1].base64);
  assert.equal(await driver.active.page.locator('#fixture-editor').inputValue(),'Preserve this unsent draft');
  assert.equal(fixture.state.chatMessages.length,1);assert.equal(fixture.state.submitted.length,2);
  assert.equal(driver.active.page.url(),service);
 }finally{control.abort();await pool.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(profile,{recursive:true,force:true})}
});

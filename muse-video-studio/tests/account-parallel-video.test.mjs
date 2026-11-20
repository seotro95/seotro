import {test} from 'node:test';import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';import path from 'node:path';import os from 'node:os';
import {chromium} from 'playwright-core';import {createMuseFixture} from './fixtures/muse.mjs';
import {MuseBrowser} from '../muse-browser.mjs';import {MuseAccounts} from '../muse-accounts.mjs';import {startStudioServer} from '../server.mjs';
const image=await readFile(new URL('../public/demo-image.png',import.meta.url));const clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
async function waitFor(predicate){const end=Date.now()+45000;while(!await predicate()){if(Date.now()>end)throw new Error('Six-video fixture timed out');await new Promise(resolve=>setTimeout(resolve,30))}}
test('one account submits six real browser-bridge video turns simultaneously in multiple-account mode; cancelling one preserves the other five (fixture)',{timeout:150000},async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-six-video-'));const fixture=createMuseFixture({image,clip});Object.assign(fixture.state,{behavior:'video',newChat:true,chatRoutes:true,sharedHistory:true,lazyVideo:true,videoSourceTag:true});
 await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));
 const serviceURL=`http://127.0.0.1:${fixture.server.address().port}/`;
 const pool=new MuseAccounts({profileRoot:root,createDriver:()=>new MuseBrowser({profileRoot:root,serviceURL,launchOptions:{executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true},pollMs:30,quietMs:50,timeoutMs:60000})});
 const runtime=await startStudioServer({museDriver:pool,port:0});
 try{
  await pool.connect(1);await pool.driver(1).active.page.getByRole('button',{name:'Fixture login',exact:true}).click();await pool.driver(1).refreshActive();
  const prepared=await fetch(runtime.url+'/api/account/prepare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accountId:1,concurrency:6})});assert.equal(prepared.status,200);assert.equal((await prepared.json()).executionConcurrency,6);assert.equal(fixture.state.submitted.length,0);
  fixture.state.hold=true;const batchId=crypto.randomUUID();const controls=Array.from({length:6},()=>new AbortController());
  const requests=controls.map((control,i)=>fetch(runtime.url+'/api/video',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accountId:1,accountMode:'multiple',batchId,sceneId:i+1,prompt:`Six-video scene ${i+1}`,model:'Omni 1.1 Flash',duration:4,resolution:'720p',aspectRatio:'16:9'}),signal:control.signal}).then(async response=>({status:response.status,body:await response.json()})));
  const settled=Promise.allSettled(requests);await waitFor(()=>fixture.state.pending.size===6);
  assert.equal(fixture.state.peak,6);assert.equal(new Set(fixture.state.submitted.map(row=>row.path)).size,6);assert.equal(pool.snapshot()[0].running,6);
  controls[2].abort();await waitFor(()=>fixture.state.stops===1);assert.equal(pool.snapshot()[0].running<=6,true);fixture.releaseAll();fixture.state.hold=false;
  const results=await settled;assert.equal(results.filter(r=>r.status==='fulfilled'&&r.value.status===200).length,5);assert.equal(results[2].status,'rejected');assert.equal(fixture.state.submitted.length,6);assert.equal(fixture.state.stops,1);assert.equal(pool.usage.size,0);
 }finally{fixture.releaseAll();await runtime.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(root,{recursive:true,force:true})}
});

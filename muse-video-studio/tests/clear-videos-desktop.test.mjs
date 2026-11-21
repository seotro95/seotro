import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdtemp,mkdir,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import os from 'node:os';
import {_electron} from 'playwright-core';
import {createMuseFixture} from './fixtures/muse.mjs';

const require=createRequire(import.meta.url),root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const image=await readFile(path.join(root,'public/demo-image.png')),clip=await readFile(path.join(root,'public/demo.mp4'));
async function until(fn){const end=Date.now()+30000;while(!await fn()){if(Date.now()>end)throw Error('Bulk video deletion did not reach the expected state');await new Promise(resolve=>setTimeout(resolve,40))}}
test('The Windows app deletes every stored video version, preserves images and scripts, and leaves downloaded files intact',{timeout:90000},async()=>{
 const profile=await mkdtemp(path.join(os.tmpdir(),'muse-clear-videos-'));
 const fixture=createMuseFixture({image,clip});await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));
 const service=`http://127.0.0.1:${fixture.server.address().port}/`;let desktop,studio,studioPort='0';
 const launch=async()=>{
  const portable=process.env.MUSE_PORTABLE_EXECUTABLE;
  desktop=await _electron.launch({executablePath:portable||require('electron'),args:[...(process.env.MUSE_ELECTRON_HEADLESS==='1'?['--ozone-platform=headless','--disable-gpu']:[]),...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX==='1'?['--no-sandbox']:[]),...(portable?[]:[path.join(root,'desktop/main.mjs')])],env:{...process.env,MUSE_DESKTOP_TEST:'1',MUSE_FIXTURE_URL:service,MUSE_DESKTOP_DATA:profile,MUSE_TRANSPORT:'browser',PORT:studioPort},timeout:30000});
  await desktop.firstWindow();await until(()=>{studio=desktop.context().pages().find(page=>page.url().startsWith('http://127.0.0.1:')&&!page.url().startsWith(service));return studio});studioPort=new URL(studio.url()).port;
 };
 const readSaved=()=>studio.evaluate(()=>new Promise((resolve,reject)=>{const open=indexedDB.open('muse-studio-media-v1',1);open.onsuccess=()=>{const db=open.result,request=db.transaction('results').objectStore('results').getAll();request.onsuccess=()=>{db.close();resolve(request.result)};request.onerror=()=>reject(request.error)};open.onerror=()=>reject(open.error)}));
 try{
  const downloads=path.join(profile,'existing-downloads');await mkdir(downloads);const downloaded=path.join(downloads,'Original video name.mp4');await writeFile(downloaded,clip);
  await launch();await until(async()=>await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).isEditable()&&await studio.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).isEnabled());
  await studio.evaluate(async({image,video})=>{
   const workspace=JSON.parse(localStorage.getItem('muse-workstation-v1'));
   workspace.settings={...workspace.settings,accountPlanMode:'expanded',accountMode:'single',singleAccountId:1,accountIds:[1],requestedConcurrency:2,slotCount:2,output:'video',syncOperations:false};
   workspace.scenes[0]={...workspace.scenes[0],prompt:'Keep the full first prompt.',outputName:'Giữ tên thứ nhất',syncSelected:false};
   workspace.scenes[1]={...workspace.scenes[1],prompt:'Keep the second prompt.',outputName:'Giữ tên thứ hai',syncSelected:false};
   workspace.scenes[299]={...workspace.scenes[299],prompt:'Keep the hidden prompt.',outputName:'Hidden saved name',syncSelected:false};
   localStorage.setItem('muse-workstation-v1',JSON.stringify(workspace));
   const db=await new Promise((resolve,reject)=>{const open=indexedDB.open('muse-studio-media-v1',1);open.onupgradeneeded=()=>open.result.createObjectStore('results',{keyPath:'id'});open.onsuccess=()=>resolve(open.result);open.onerror=()=>reject(open.error)});
   await new Promise((resolve,reject)=>{const tx=db.transaction('results','readwrite'),store=tx.objectStore('results');
    for(const [id,kind,sceneId,createdAt] of [['video-current','video',1,'2026-01-03'],['video-old-version','video',1,'2026-01-01'],['video-hidden-group','video',300,'2026-01-02'],['image-preserved','image',1,'2026-01-04']])store.put({id,batchId:id+'-batch',sceneId,prompt:workspace.scenes[sceneId-1].prompt,createdAt,persisted:true,settings:{...workspace.settings,output:kind},media:{kind,mimeType:kind==='video'?'video/mp4':'image/png',base64:kind==='video'?video:image,demo:false,outputName:workspace.scenes[sceneId-1].outputName,metadata:{width:640,height:360}}});
    tx.oncomplete=resolve;tx.onerror=tx.onabort=()=>reject(tx.error)});db.close();
  },{image:image.toString('base64'),video:clip.toString('base64')});
  await studio.reload();const button=studio.getByRole('region',{name:'Đồng bộ thao tác'}).getByRole('button',{name:'Xoá tất cả video đã tạo',exact:true});
  await until(async()=>await button.isEnabled());assert.equal(await studio.getByRole('button',{name:'Đồng bộ thao tác: TẮT',exact:true}).count(),1);
  await button.click();let modal=studio.getByRole('dialog',{name:'Xoá tất cả video đã tạo?',exact:true});await modal.waitFor();assert.match(await modal.innerText(),/3/);await modal.getByRole('button',{name:'Hủy',exact:true}).click();assert.equal((await readSaved()).length,4);
  await button.click();modal=studio.getByRole('dialog',{name:'Xoá tất cả video đã tạo?',exact:true});await modal.getByRole('button',{name:'Xác nhận xoá tất cả video',exact:true}).click();await until(async()=>await modal.count()===0);
  const remaining=await readSaved();assert.deepEqual(remaining.map(entry=>entry.id),['image-preserved']);assert.equal(remaining[0].media.base64,image.toString('base64'));assert.equal(await studio.locator('.scene-card video').count(),0);assert.equal(await button.isDisabled(),true);
  assert.equal(await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).inputValue(),'Keep the full first prompt.');
  const workspace=await studio.evaluate(()=>JSON.parse(localStorage.getItem('muse-workstation-v1')));assert.equal(workspace.scenes[0].outputName,'Giữ tên thứ nhất');assert.equal(workspace.scenes[299].prompt,'Keep the hidden prompt.');
  assert.deepEqual(await readFile(downloaded),clip);assert.equal(fixture.state.submitted.length,0);
  await desktop.close();desktop=null;await launch();await until(async()=>await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).isEditable());assert.deepEqual((await readSaved()).map(entry=>entry.id),['image-preserved']);assert.equal(await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).inputValue(),'Keep the full first prompt.');assert.deepEqual(await readFile(downloaded),clip);assert.equal(fixture.state.submitted.length,0);await studio.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();await until(async()=>await studio.locator('.generated-image').count()===1);
 }finally{await desktop?.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(profile,{recursive:true,force:true})}
});

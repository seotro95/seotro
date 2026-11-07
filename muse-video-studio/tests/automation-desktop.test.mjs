import {test} from 'node:test';
import assert from 'node:assert/strict';
import {_electron} from 'playwright-core';
import {createRequire} from 'node:module';
import {mkdtemp,readFile,rm,mkdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import {createMuseFixture} from './fixtures/muse.mjs';
const require=createRequire(import.meta.url);const root=path.resolve(import.meta.dirname,'..');
const image=await readFile(path.join(root,'public/demo-image.png'));const clip=await readFile(path.join(root,'public/demo.mp4'));
async function waitFor(predicate,label,timeout=45000){const end=Date.now()+timeout;while(!await predicate()){if(Date.now()>end)throw new Error('Timed out: '+label);await new Promise(resolve=>setTimeout(resolve,40))}}
async function freePort(){const server=http.createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const port=server.address().port;await new Promise(resolve=>server.close(resolve));return port}

test('external HTTP controls Studio, defaults to two real concurrent conversations, downloads exact bytes and clears persisted media without resetting file numbers (fixture)',{timeout:180000},async()=>{
  const profile=await mkdtemp(path.join(os.tmpdir(),'muse-auto-desktop-'));const fixture=createMuseFixture({image,clip});Object.assign(fixture.state,{behavior:'image',newChat:true,chatRoutes:true,sharedHistory:true,uniqueImages:true});
  await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));const service=`http://127.0.0.1:${fixture.server.address().port}/`;
  const executablePath=process.env.MUSE_PORTABLE_EXECUTABLE||require('electron');const args=[...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX==='1'?['--no-sandbox','--disable-gpu']:[]),...(!process.env.MUSE_PORTABLE_EXECUTABLE?[path.join(root,'desktop/main.mjs')]:[])];
  const env={...process.env,MUSE_DESKTOP_TEST:'1',MUSE_FIXTURE_URL:service,MUSE_DESKTOP_DATA:profile,MUSE_TRANSPORT:'browser',PORT:'0'};delete env.MUSE_TEST_PARALLEL;
  if(process.env.MUSE_PORTABLE_EXECUTABLE){env.PATH='/no-external-runtime';env.NODE_PATH='';delete env.PORT}
  let desktop;
  try{
    const launch=async()=>{desktop=await _electron.launch({executablePath,args,env,timeout:30000});await desktop.firstWindow();let studio,shell;await waitFor(()=>{const pages=desktop.context().pages();studio=pages.find(page=>page.url().startsWith('http://127.0.0.1:')&&!page.url().startsWith(service));shell=pages.find(page=>page.url().endsWith('/desktop/shell.html'));return studio&&shell},'Studio');return {studio,shell}};
    let {studio,shell}=await launch();
    await studio.getByRole('button',{name:'Đăng nhập Muse trong tool',exact:true}).click();let login;await waitFor(()=>{login=desktop.context().pages().find(page=>page.url()===service);return login},'login');
    await login.getByRole('button',{name:'Fixture login',exact:true}).click();await shell.getByRole('button',{name:'← Về Studio',exact:true}).click();await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,'verified');
    assert.equal(await studio.getByLabel('Số luồng:',{exact:true}).inputValue(),'2');
    const port=await freePort();const address=`http://127.0.0.1:${port}`;
    await studio.getByRole('button',{name:'Cổng API',exact:true}).click();const apiDialog=studio.getByRole('dialog',{name:'Cổng API cho công cụ bên ngoài',exact:true});await apiDialog.getByLabel('Cổng API',{exact:true}).fill(String(port));await apiDialog.getByRole('button',{name:'Bật / Áp dụng cổng',exact:true}).click();
    let key;await waitFor(async()=>{key=await apiDialog.getByLabel('Khóa API',{exact:true}).inputValue();return key.length===64&&await apiDialog.getByText('API đang mở',{exact:false}).count()>0},'API enabled');
    const call=(route,options={})=>fetch(address+route,{...options,headers:{Authorization:'Bearer '+key,...options.headers}});
    const jsonCall=(route,data,headers={})=>call(route,{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(data)});
    assert.equal((await fetch(address+'/v1/status')).status,401);assert.equal((await call('/v1/status',{headers:{Origin:'https://untrusted.example'}})).status,403);
    fixture.state.hold=true;
    const input={output:'image',prompts:['External scene one','External scene two','External scene three','External scene four']};
    const response=await jsonCall('/v1/batches',input,{'Idempotency-Key':'batch-images'});assert.equal(response.status,202);const batch=await response.json();
    await waitFor(()=>fixture.state.pending.size===2,'two held requests');assert.equal(fixture.state.submitted.length,2);assert.equal(fixture.state.peak,2);
    assert.equal(new Set(fixture.state.submitted.map(request=>request.path)).size,2);
    assert.equal(await studio.locator('.status-badge.running').count(),2);assert.equal(await studio.locator('.status-badge.queued').count(),2);
    const duplicate=await jsonCall('/v1/batches',input,{'Idempotency-Key':'batch-images'});assert.equal(duplicate.status,202);assert.equal((await duplicate.json()).batchId,batch.batchId);assert.equal(fixture.state.submitted.length,2);
    assert.equal((await call('/v1/media',{method:'DELETE',headers:{'Content-Type':'application/json'},body:'{"confirm":"DELETE_ALL_MEDIA"}'})).status,409);
    fixture.releaseAll();await waitFor(()=>fixture.state.submitted.length===4&&fixture.state.pending.size===2,'second wave of two');assert.equal(fixture.state.peak,2);fixture.releaseAll();fixture.state.hold=false;
    await waitFor(async()=>await studio.locator('.generated-image').count()===4,'four images');await waitFor(async()=>!(await(await call('/v1/status')).json()).busy,'idle');
    const library=(await(await call('/v1/media')).json()).media;assert.equal(library.length,4);const entry=library.find(entry=>entry.sceneId===1);assert.equal(entry.batchId,batch.batchId);
    const binary=await call(entry.download);assert.equal(binary.headers.get('content-type'),'image/png');const bytes=Buffer.from(await binary.arrayBuffer());
    const request=fixture.state.submitted.find(request=>request.prompt.includes('Scene:\nExternal scene one'));assert.equal(bytes.toString('base64'),fixture.state.outputs.get(request.id));
    const downloads=path.join(profile,'downloads');await mkdir(downloads);
    await desktop.evaluate(({session},directory)=>{globalThis.saved=[];session.fromPartition('persist:studio').on('will-download',(_event,item)=>{const name=item.getFilename();item.setSavePath(`${directory}/${name}`);item.once('done',(_event,state)=>globalThis.saved.push({name,state}))})},downloads);
    await studio.getByRole('button',{name:'Tải cảnh 1',exact:true}).click();await waitFor(async()=>await desktop.evaluate(()=>globalThis.saved.length)===1,'first download');const first=await desktop.evaluate(()=>globalThis.saved[0]);assert.match(first.name,/^image-000001-scene-01-/);
    await studio.getByRole('button',{name:'Xóa toàn bộ',exact:true}).click();const confirmation=studio.getByRole('dialog',{name:'Xóa toàn bộ ảnh/video đã lưu?',exact:true});await confirmation.getByRole('button',{name:'Hủy',exact:true}).click();assert.equal((await(await call('/v1/media')).json()).media.length,4);
    await studio.getByRole('button',{name:'Xóa toàn bộ',exact:true}).click();await confirmation.getByRole('button',{name:'Xác nhận xóa toàn bộ',exact:true}).click();await waitFor(async()=>(await(await call('/v1/media')).json()).media.length===0,'empty library');
    assert.equal(await studio.locator('.generated-image').count(),0);assert.equal((await readFile(path.join(downloads,first.name))).length,bytes.length);
    await studio.reload();await waitFor(async()=>{const response=await call('/v1/status');return response.status===200&&(await response.json()).media.length===0},'empty persisted library');
    const next=await jsonCall('/v1/batches',{output:'image',prompts:['New after clearing']},{'Idempotency-Key':'batch-new'});assert.equal(next.status,202);await waitFor(async()=>await studio.locator('.generated-image').count()===1,'new image');await waitFor(async()=>!(await(await call('/v1/status')).json()).busy,'new batch idle');
    await studio.getByRole('button',{name:'Tải cảnh 1',exact:true}).click();await waitFor(async()=>await desktop.evaluate(()=>globalThis.saved.length)===2,'continued download');assert.match((await desktop.evaluate(()=>globalThis.saved[1])).name,/^image-000002-scene-01-/);
    fixture.state.behavior='slow';const count=fixture.state.submitted.length;assert.equal((await jsonCall('/v1/batches',{output:'video',prompts:['Stop one','Stop two']},{'Idempotency-Key':'batch-stop'})).status,202);await waitFor(()=>fixture.state.submitted.length===count+2,'two stoppable requests');
    assert.equal((await jsonCall('/v1/stop',{sceneId:1})).status,200);await waitFor(()=>fixture.state.stops===1,'one Stop');assert.equal((await jsonCall('/v1/stop',{})).status,200);await waitFor(()=>fixture.state.stops===2,'second Stop');await waitFor(async()=>!(await(await call('/v1/status')).json()).busy,'cancelled batch idle');
    assert.equal((await call('/v1/media',{method:'DELETE',headers:{'Content-Type':'application/json'},body:'{"confirm":"DELETE_ALL_MEDIA"}'})).status,200);
    if(!process.env.MUSE_PORTABLE_EXECUTABLE)env.PORT=new URL(studio.url()).port;
    await desktop.close();desktop=null;({studio,shell}=await launch());await waitFor(async()=>{const response=await call('/v1/status');return response.status===200&&(await response.json()).media.length===0},'API restart');
    assert.equal(await studio.getByLabel('Số luồng:',{exact:true}).inputValue(),'2');
    await studio.getByRole('button',{name:'Cổng API',exact:true}).click();const reopened=studio.getByRole('dialog',{name:'Cổng API cho công cụ bên ngoài',exact:true});await waitFor(async()=>await reopened.getByLabel('Khóa API',{exact:true}).inputValue()===key,'saved API key');
    await reopened.getByRole('button',{name:'Đổi khóa API',exact:true}).click();await waitFor(async()=>await reopened.getByLabel('Khóa API',{exact:true}).inputValue()!==key,'rotated key');assert.equal((await call('/v1/status')).status,401);key=await reopened.getByLabel('Khóa API',{exact:true}).inputValue();assert.equal((await call('/v1/status')).status,200);
    await reopened.getByRole('button',{name:'Tắt cổng API',exact:true}).click();await waitFor(async()=>{try{await call('/v1/status');return false}catch{return true}},'API disabled');
  }finally{fixture.releaseAll();await desktop?.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(profile,{recursive:true,force:true})}
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {readFile,mkdtemp,writeFile,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {chromium,_electron} from 'playwright-core';
import {readPageAttachment} from '../muse-attachment.mjs';
import {MuseBrowser} from '../muse-browser.mjs';

const require=createRequire(import.meta.url),clip=await readFile(new URL('../public/demo.mp4',import.meta.url));
const action=(id,kind='image')=>({src:'muse-file-control:'+id,kind,nativeControl:true,nativeButton:true,nativeDownload:true,nativeId:id});
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(fn){const deadline=Date.now()+5000;while(!await fn()){if(Date.now()>deadline)throw Error('Test action did not start');await wait(20)}}
async function service(){
 const server=createServer((req,res)=>{
  if(req.url==='/direct.mp4'){res.writeHead(200,{'content-type':'video/mp4'});res.end(clip);return}
  res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
  res.end(`<!doctype html><button data-muse-studio-file-id="a">Download image A</button><button data-muse-studio-file-id="b">Download image B</button><script>
   window.expected={};window.clicks=[];
   for(const [id,color,delay] of [['a','blue',1000],['b','red',30]]){
    const canvas=document.createElement('canvas');canvas.width=canvas.height=256;const ctx=canvas.getContext('2d');ctx.fillStyle=color;ctx.fillRect(0,0,256,256);window.expected[id]=canvas.toDataURL('image/png').split(',')[1];
    document.querySelector('[data-muse-studio-file-id="'+id+'"]').onclick=event=>{event.preventDefault();window.clicks.push(id);setTimeout(()=>{const link=document.createElement('a');link.href='data:image/png;base64,'+window.expected[id];link.download=id+'.png';document.body.appendChild(link);link.click();link.remove()},delay)};
   }
  </script>`);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {url:`http://127.0.0.1:${server.address().port}/chat/owned`,async close(){server.closeAllConnections();await new Promise(resolve=>server.close(resolve))}};
}

for(const reason of ['timeout','cancel'])test(`Browser quarantines an image ${reason}, cancels its late file and requires a fresh document`,{timeout:20000},async()=>{
 const fixture=await service(),profile=await mkdtemp(path.join(os.tmpdir(),'muse-late-browser-'));
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||chromium.executablePath()}),page=await browser.newPage();
 try{
  await page.goto(fixture.url);const late=[];page.on('download',item=>late.push(item));
  const control=new AbortController();
  const first=readPageAttachment(page,action('a'),control.signal,{timeoutMs:reason==='timeout'?350:3000});
  const rejection=assert.rejects(first,reason==='timeout'?/MEDIA_ATTACHMENT_NOT_DELIVERED/:/Stop image action/);
  await until(()=>page.evaluate(()=>window.clicks.includes('a')));
  if(reason==='cancel')control.abort(Error('Stop image action'));
  await rejection;
  await assert.rejects(readPageAttachment(page,action('b'),new AbortController().signal),/MEDIA_ATTACHMENT_UNCERTAIN/);
  await assert.rejects(readPageAttachment(page,action('b','video'),new AbortController().signal),/MEDIA_ATTACHMENT_UNCERTAIN/);
  assert.deepEqual(await page.evaluate(()=>window.clicks),['a'],'Neither another image nor native video may click a control on the uncertain page');
  await until(()=>late.length===1);await until(async()=>{try{if(await late[0].failure())return true;await readFile(await late[0].path());return false}catch{return true}});
  const driver=new MuseBrowser({profileRoot:profile,serviceURL:fixture.url});
  const video=await driver.downloadMedia(page,{src:new URL('/direct.mp4',fixture.url).href,kind:'video'},'video',new AbortController().signal);
  assert.equal(video.base64,clip.toString('base64'),'Direct video receiving remains available while native captures are quarantined');
  await page.evaluate(()=>{location.hash='retained';history.pushState(null,'','?history-only=1#retained')});
  await assert.rejects(readPageAttachment(page,action('b'),new AbortController().signal),/MEDIA_ATTACHMENT_UNCERTAIN/);
  await page.reload();
  const second=await readPageAttachment(page,action('b'),new AbortController().signal,{timeoutMs:1500});
  assert.equal(second.base64,await page.evaluate(()=>window.expected.b));
  assert.deepEqual(await page.evaluate(()=>window.clicks),['b']);
 }finally{await browser.close();await fixture.close();await rm(profile,{recursive:true,force:true})}
});

test('A capture that expires before its click cannot click late or taint the next image',{timeout:15000},async()=>{
 const fixture=await service(),browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||chromium.executablePath()}),page=await browser.newPage();
 try{
  await page.goto(fixture.url);
  const slowFrame={page:()=>page,evaluate:async(...args)=>{await wait(500);return page.evaluate(...args)},locator:(...args)=>page.locator(...args)};
  await assert.rejects(readPageAttachment(slowFrame,action('a'),new AbortController().signal,{timeoutMs:100}),/MEDIA_ATTACHMENT_NOT_DELIVERED/);
  const result=await readPageAttachment(page,action('b'),new AbortController().signal,{timeoutMs:1500});
  assert.equal(result.base64,await page.evaluate(()=>window.expected.b));
  await wait(600);assert.deepEqual(await page.evaluate(()=>window.clicks),['b'],'An expired action must never click after its listener is removed');
 }finally{await browser.close();await fixture.close()}
});

test('Native Electron capture quarantines a late image and clears only on a full document load',{timeout:30000},async()=>{
 const fixture=await service(),root=await mkdtemp(path.join(os.tmpdir(),'muse-late-electron-'));
 const helper=new URL('../desktop/attachment-download.mjs',import.meta.url).href;
 const entry=path.join(root,'main.mjs');
 await writeFile(entry,`import{app,BrowserWindow}from'electron';import{captureSessionAttachment}from${JSON.stringify(helper)};
  app.setPath('userData',${JSON.stringify(path.join(root,'profile'))});app.whenReady().then(async()=>{
  const window=new BrowserWindow({show:true,webPreferences:{sandbox:true,contextIsolation:true,nodeIntegration:false}});
  globalThis.testWindow=window;globalThis.observed=[];
  window.webContents.session.on('will-download',(event,item)=>{const record={name:item.getFilename()};observed.push(record);setImmediate(()=>record.prevented=event.defaultPrevented)});
  globalThis.capture=async({id,kind='image',timeoutMs=3000})=>{try{return {ok:true,value:await captureSessionAttachment(window.webContents,onTrigger=>{if(onTrigger()===false)return Promise.reject(Error('Capture ended'));const selector='[data-muse-studio-file-id="'+id+'"]';return window.webContents.executeJavaScript('document.querySelector('+JSON.stringify(selector)+').click()')},new AbortController().signal,{kind,timeoutMs})}}catch(error){return {ok:false,error:error.message}}};
  await window.loadURL(${JSON.stringify(fixture.url)});});
 `);
 let desktop;
 try{
  // Test the real source helper in a minimal Electron process. Packaged Muse
  // flows are covered separately; this entry is not passed to the portable EXE.
  desktop=await _electron.launch({executablePath:require('electron'),args:[...(process.env.MUSE_ELECTRON_HEADLESS==='1'?['--ozone-platform=headless','--disable-gpu']:[]),...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX==='1'?['--no-sandbox']:[]),entry],env:{...process.env},timeout:20000});
  const page=await desktop.firstWindow();await page.waitForFunction(()=>Boolean(window.expected));
  const first=await desktop.evaluate(()=>globalThis.capture({id:'a',timeoutMs:350}));assert.equal(first.ok,false);assert.match(first.error,/MEDIA_ATTACHMENT_NOT_DELIVERED/);assert.match(first.error,/MEDIA_ATTACHMENT_UNCERTAIN/);
  for(const kind of ['image','video']){const next=await desktop.evaluate((_electron,kind)=>globalThis.capture({id:'b',kind}),kind);assert.equal(next.ok,false);assert.match(next.error,/MEDIA_ATTACHMENT_UNCERTAIN/)}
  assert.deepEqual(await page.evaluate(()=>window.clicks),['a']);
  await until(()=>desktop.evaluate(()=>globalThis.observed.length===1));
  await until(()=>desktop.evaluate(()=>globalThis.observed[0].prevented===true));
  await page.evaluate(()=>{location.hash='keep';history.pushState(null,'','?history-only=1#keep')});
  const history=await desktop.evaluate(()=>globalThis.capture({id:'b'}));assert.match(history.error,/MEDIA_ATTACHMENT_UNCERTAIN/);
  await page.reload();await page.waitForFunction(()=>Boolean(window.expected));
  const second=await desktop.evaluate(()=>globalThis.capture({id:'b'}));assert.equal(second.ok,true,second.error);assert.equal(second.value.base64,await page.evaluate(()=>window.expected.b));
  assert.deepEqual(await page.evaluate(()=>window.clicks),['b']);
 }finally{await desktop?.close();await fixture.close();await rm(root,{recursive:true,force:true})}
});

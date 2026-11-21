import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {chromium} from 'playwright-core';
import {MuseBrowser} from '../muse-browser.mjs';
import {readPageAttachment} from '../muse-attachment.mjs';

const image=await readFile(new URL('../public/demo-image.png',import.meta.url));
const signedPath='/generated/portrait.png?token=a%2Bb%2Fc&expires=2000000000&signature=KEEP%2BTHIS';

async function setup(){
  const profileRoot=await mkdtemp(path.join(os.tmpdir(),'muse-image-browser-download-'));
  const requests=[];
  const server=createServer((req,res)=>{
    if(req.url?.startsWith('/generated/')){
      requests.push({url:req.url,mode:req.headers['sec-fetch-mode'],destination:req.headers['sec-fetch-dest']});
      res.writeHead(200,{'content-type':'image/png','content-disposition':'attachment; filename="provider-portrait.png"'});
      res.end(image);return;
    }
    res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
    res.end('<!doctype html><div id="chat">Persistent Muse conversation</div><a id="file" data-muse-studio-file-id="owned-file">Download image</a>');
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin=`http://127.0.0.1:${server.address().port}`;
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||chromium.executablePath()});
  const page=await browser.newPage();
  await page.goto(origin+'/chat/owned-conversation');
  await page.locator('#file').evaluate((node,href)=>node.href=href,origin+signedPath);
  // The ordinary fetch path cannot access this file, while a browser download
  // still works. No mocked download event or generated replacement is used.
  await page.evaluate(()=>{const original=window.fetch;window.fetch=(input,...args)=>String(input).includes('/generated/')?Promise.reject(new TypeError('Failed to fetch')):original(input,...args)});
  const media={src:origin+signedPath,kind:'image',nativeControl:true,nativeId:'owned-file'};
  return {page,media,requests,profileRoot,async close(){await browser.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));await rm(profileRoot,{recursive:true,force:true})}};
}

test('Receive an owned same-origin image through its unchanged signed browser-download URL when fetch fails',{timeout:20000},async()=>{
  const fixture=await setup();
  try{
    const driver=new MuseBrowser({profileRoot:fixture.profileRoot,serviceURL:fixture.page.url()});
    const before=fixture.page.url();
    assert.equal(await fixture.page.locator('#file').getAttribute('download'),null);
    const result=await driver.downloadMedia(fixture.page,fixture.media,'image',new AbortController().signal);
    assert.equal(result.base64,image.toString('base64'),'The exact generated file must be decoded and returned');
    assert.equal(result.metadata.width,image.readUInt32BE(16));
    assert.equal(result.metadata.height,image.readUInt32BE(20));
    assert.equal(fixture.requests.length,1);
    assert.equal(fixture.requests[0].url,signedPath,'The signature, query and path must stay unchanged');
    assert.equal(fixture.requests[0].mode,'navigate');
    assert.equal(fixture.page.url(),before,'Receiving the image must preserve the chat route');
    assert.equal(await fixture.page.locator('#file').getAttribute('download'),null,'Temporary attributes must be restored');
    assert.equal(await fixture.page.locator('#file').getAttribute('href'),fixture.media.src);
  }finally{await fixture.close()}
});

test('Existing trusted image download handlers still run and their modified filename is preserved',{timeout:20000},async()=>{
  const fixture=await setup();
  try{
    await fixture.page.locator('#file').evaluate((node,base64)=>{node.onclick=event=>{
      event.preventDefault();window.downloadGestureTrusted=event.isTrusted;node.download='provider-filename.png';
      const bytes=Uint8Array.from(atob(base64),char=>char.charCodeAt(0));
      const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([bytes],{type:'image/png'}));link.download='existing-handler.png';document.body.appendChild(link);link.click();link.remove();
    }},image.toString('base64'));
    const result=await readPageAttachment(fixture.page,{...fixture.media,nativeDownload:true},new AbortController().signal,{timeoutMs:3000});
    assert.equal(result.base64,image.toString('base64'));
    assert.equal(await fixture.page.evaluate(()=>window.downloadGestureTrusted),true);
    assert.equal(await fixture.page.locator('#file').getAttribute('download'),'provider-filename.png');
    assert.equal(fixture.requests.length,0);
  }finally{await fixture.close()}
});

test('Image fallback does not execute script links or enable default video navigation',{timeout:20000},async()=>{
  const fixture=await setup();
  try{
    const initial=fixture.page.url();
    await fixture.page.locator('#file').evaluate(node=>node.href='javascript:window.unexpectedImageAction=true');
    await assert.rejects(readPageAttachment(fixture.page,{...fixture.media,src:'javascript:window.unexpectedImageAction=true',nativeDownload:true},new AbortController().signal,{timeoutMs:1000}),/MEDIA_ATTACHMENT_LINK_CHANGED/);
    assert.equal(await fixture.page.evaluate(()=>window.unexpectedImageAction),undefined);
    assert.equal(await fixture.page.locator('#file').getAttribute('download'),null);
    await fixture.page.locator('#file').evaluate((node,href)=>node.href=href,fixture.media.src);
    await assert.rejects(readPageAttachment(fixture.page,{...fixture.media,kind:'video',nativeDownload:true},new AbortController().signal,{timeoutMs:300}),/MEDIA_ATTACHMENT_NOT_DELIVERED/);
    assert.equal(fixture.requests.length,0);
    assert.equal(fixture.page.url(),initial);
    assert.equal(await fixture.page.locator('#file').getAttribute('download'),null);
  }finally{await fixture.close()}
});

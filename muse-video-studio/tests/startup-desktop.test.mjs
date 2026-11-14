import {test} from 'node:test';
import assert from 'node:assert/strict';
import {_electron} from 'playwright-core';
import {createRequire} from 'node:module';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const require=createRequire(import.meta.url);
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const portable=process.env.MUSE_PORTABLE_EXECUTABLE;
const args=[...(process.env.MUSE_ELECTRON_HEADLESS==='1'?['--ozone-platform=headless','--disable-gpu']:[]),...(portable?[]:[path.join(root,'desktop/main.mjs')])];
async function until(fn){
  const deadline=Date.now()+30000;
  while(!await fn()){
    if(Date.now()>deadline)throw new Error('Studio startup state did not settle');
    await new Promise(resolve=>setTimeout(resolve,30));
  }
}

test('Studio renders, survives load failure and renderer crash, and retries without losing the saved script',{timeout:120000},async()=>{
  const profile=await mkdtemp(path.join(os.tmpdir(),'muse-startup-test-'));let desktop;
  try{
    desktop=await _electron.launch({executablePath:portable||require('electron'),args,env:{...process.env,MUSE_DESKTOP_TEST:'1',MUSE_DESKTOP_DATA:profile,PORT:'0'},timeout:30000});
    await desktop.firstWindow();let shell,studio;
    await until(()=>{
      shell=desktop.context().pages().find(page=>page.url().endsWith('/desktop/shell.html'));
      studio=desktop.context().pages().find(page=>page.url().startsWith('http://127.0.0.1:'));
      return shell&&studio;
    });
    const state=()=>shell.evaluate(()=>window.studioDesktop.startup('status'));
    await until(async()=>(await state()).phase==='ready');
    assert.ok(await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).isVisible());
    await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Keep my existing script');
    await until(async()=>JSON.parse(await studio.evaluate(()=>localStorage.getItem('muse-workstation-v1'))).scenes[0].prompt==='Keep my existing script');
    await desktop.evaluate(async({webContents})=>{
      const page=webContents.getAllWebContents().find(w=>w.getURL().startsWith('http://127.0.0.1:'));
      await page.loadURL('http://127.0.0.1:1/').catch(()=>{});
    });
    await until(async()=>(await state()).code==='STUDIO_LOAD_FAILED');
    assert.ok(await shell.getByRole('heading',{name:'Chưa mở được Studio',exact:true}).isVisible());
    await shell.locator('#retry-studio').click();
    await until(async()=>(await state()).phase==='ready');
    assert.equal(await studio.getByLabel('Kịch bản cảnh 1',{exact:true}).inputValue(),'Keep my existing script');
    await desktop.evaluate(({webContents})=>{
      webContents.getAllWebContents().find(w=>w.getURL().startsWith('http://127.0.0.1:')).forcefullyCrashRenderer();
    });
    await until(async()=>(await state()).code==='STUDIO_RENDERER_EXITED');
    assert.ok(await shell.getByRole('button',{name:'Sao chép chẩn đoán Studio',exact:true}).isVisible());
    const report=await shell.evaluate(async()=>{await window.studioDesktop.startup('copy');return window.studioDesktop.startup('status')});
    assert.equal(report.code,'STUDIO_RENDERER_EXITED');
    const copied=await desktop.evaluate(({clipboard})=>clipboard.readText());
    assert.doesNotMatch(copied,/Keep my existing script|127\.0\.0\.1|token|cookie/i);
    await shell.locator('#reload-studio').click();
    await until(async()=>(await state()).phase==='ready');
    // Playwright retains its crashed flag for the old Page object after a real
    // renderer crash. Read the recovered renderer through Electron itself.
    assert.equal(await desktop.evaluate(async({webContents})=>{
      const recovered=webContents.getAllWebContents().find(w=>w.getURL().startsWith('http://127.0.0.1:'));
      return recovered.executeJavaScript('document.querySelector("textarea").value');
    }),'Keep my existing script');
    await shell.getByRole('button',{name:'← Về Studio',exact:true}).click();
    assert.equal(await desktop.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].contentView.children.length),1);
  }finally{await desktop?.close();await rm(profile,{recursive:true,force:true})}
});

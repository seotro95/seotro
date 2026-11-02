'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'melo-ui-'));
 const server=spawn(process.env.TEST_PYTHON||'python3',[path.join(__dirname,'browser_server.py'),'--root',root],{stdio:['ignore','pipe','inherit']});
 const port=await new Promise((resolve,reject)=>{const lines=createInterface({input:server.stdout});lines.once('line',line=>resolve(Number(line)));server.once('exit',code=>reject(new Error('Server exited '+code)));});
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({acceptDownloads:true});const errors=[];page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto('http://127.0.0.1:'+port);
  await page.getByText('v1.1.0',{exact:true}).waitFor();
  await page.locator('#load').click();await page.waitForFunction(()=>document.querySelector('#voice').options.length===2&&!document.querySelector('#voice').disabled);
  await page.locator('#style').selectOption('review');assert.equal(await page.locator('#speed').inputValue(),'1.1');
  const srt='1\r\n00:00:10,000 --> 00:00:12,000\r\nBonjour le monde.\r\n\r\n2\r\n00:00:15,000 --> 00:00:18,000\r\nBonsoir tout le monde.\r\n';
  await page.locator('#files').setInputFiles([
   {name:'First <script>.txt',mimeType:'text/plain',buffer:Buffer.from('Xin chào thế giới. Đây là một tệp TXT.')},
   {name:'SRT named as TXT.txt',mimeType:'text/plain',buffer:Buffer.concat([Buffer.from([255,254]),Buffer.from(srt,'utf16le')])}
  ]);
  await page.waitForFunction(()=>document.querySelectorAll('.file-row').length===2);
  assert.match(await page.locator('#file-list').innerText(),/SRT/);
  assert.match(await page.locator('#file-list').innerText(),/utf-16le/);
  assert.equal(await page.locator('#file-list script').count(),0);
  await page.locator('#voice').selectOption(['voice-a','voice-b']);
  await page.locator('#render-files').click();
  await page.waitForFunction(()=>document.querySelectorAll('.state-done').length===4,{},{timeout:20000});
  await page.locator('.job').first().getByRole('button',{name:'Nghe / tải',exact:true}).click();
  await page.locator('#player-panel').waitFor();
  const downloadPromise=page.waitForEvent('download');await page.locator('#player-downloads').getByRole('link',{name:'SRT',exact:true}).click();
  const download=await downloadPromise;const content=await fs.readFile(await download.path(),'utf8');
  assert.match(content,/00:00:00,000 -->/);assert(!content.includes('00:00:10,000'));
  await page.reload();await page.waitForFunction(()=>document.querySelectorAll('.state-done').length===4);
  await page.locator('#engine').selectOption('edge');await page.locator('#load').click();
  await page.waitForFunction(()=>document.querySelector('#language').options.length===4);
  await page.locator('#language').selectOption('ru-RU');
  assert.equal(await page.locator('#voice option').count(),2);
  await page.locator('#text').fill('Русский текст для синтетического теста.');await page.locator('#render').click();
  await page.waitForFunction(()=>document.querySelectorAll('.state-done').length===5,{},{timeout:15000});
  await page.locator('#text').fill('a'.repeat(1000000));await page.locator('#inspect').click();
  await page.waitForFunction(()=>document.querySelector('#document-info').textContent.includes('1.000.000'));
  assert.match(await page.locator('#char-count').innerText(),/1.000.000 \/ 1.000.000/);
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
  assert.deepEqual(errors,[]);
  console.log('Browser passed: multi-file UTF-8/UTF-16 import, content SRT detection, multi-voice batch, persisted history, real SRT export, online catalog UI, million-character editor, mobile layout. Audio was synthetic.');
 }finally{await browser.close();server.kill('SIGTERM');await new Promise(resolve=>server.once('exit',resolve));await fs.rm(root,{recursive:true,force:true});}
})().catch(error=>{console.error(error);console.log('::error title=Browser regression::'+String(error.message).replaceAll('%','%25').replaceAll('\n','%0A'));process.exitCode=1;});

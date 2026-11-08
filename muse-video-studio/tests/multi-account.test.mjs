import {test} from 'node:test';
import assert from 'node:assert/strict';
import {_electron} from 'playwright-core';
import {createRequire} from 'node:module';
import {mkdtemp,rm,readFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createMuseFixture} from './fixtures/muse.mjs';
const require=createRequire(import.meta.url);const root=path.resolve(import.meta.dirname,'..');
const image=await readFile(path.join(root,'public/demo-image.png'));const clip=await readFile(path.join(root,'public/demo.mp4'));
async function waitFor(predicate,label,timeout=45000){const end=Date.now()+timeout;while(!await predicate()){if(Date.now()>end)throw new Error('Timed out: '+label);await new Promise(resolve=>setTimeout(resolve,40))}}

test('ten isolated Muse sessions each submit one concurrent request; single-account mode and saved sessions remain available (fixture)',{timeout:180000},async()=>{
  const profile=await mkdtemp(path.join(os.tmpdir(),'muse-multi-'));
  const fixture=createMuseFixture({image,clip});Object.assign(fixture.state,{behavior:'image',newChat:false,sharedHistory:true,isolateAccounts:true,uniqueImages:true});
  await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));const service=`http://127.0.0.1:${fixture.server.address().port}/`;
  const executablePath=process.env.MUSE_PORTABLE_EXECUTABLE||require('electron');
  const args=['--password-store=basic',...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX==='1'?['--no-sandbox','--disable-gpu']:[]),...(!process.env.MUSE_PORTABLE_EXECUTABLE?[path.join(root,'desktop/main.mjs')]:[])];
  const env={...process.env,MUSE_DESKTOP_TEST:'1',MUSE_FIXTURE_URL:service,MUSE_DESKTOP_DATA:profile,MUSE_TRANSPORT:'browser',PORT:'0'};
  delete env.MUSE_TEST_PARALLEL;
  if(process.env.MUSE_PORTABLE_EXECUTABLE){env.PATH='/no-external-runtime';env.NODE_PATH='';delete env.PORT}
  let desktop;
  try {
    const launch=async()=>{desktop=await _electron.launch({executablePath,args,env,timeout:30000});await desktop.firstWindow();let studio,shell;await waitFor(()=>{const pages=desktop.context().pages();studio=pages.find(page=>page.url().startsWith('http://127.0.0.1:')&&!page.url().startsWith(service));shell=pages.find(page=>page.url().endsWith('/desktop/shell.html'));return studio&&shell},'Studio');return {studio,shell}};
    let {studio,shell}=await launch();
    assert.equal(await desktop.evaluate(({safeStorage})=>safeStorage.isAsyncEncryptionAvailable()),true,'Fixture must have a working encryption codec');
    await studio.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();
    const dialog=studio.getByRole('dialog',{name:'Quản lý tài khoản Muse',exact:true});
    const labels=Array.from({length:10},(_,i)=>`owner${i+1}@example.invalid`);
    await dialog.getByLabel('Danh sách tài khoản',{exact:true}).fill(labels.join('\n'));
    await dialog.getByRole('button',{name:'Lưu danh sách',exact:true}).click();
    await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[9].label===labels[9],'imported labels');
    assert.equal((await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts.filter(account=>account.authenticated).length,0,'Importing labels must never fake authentication');
    await dialog.getByRole('button',{name:'Hoàn tất',exact:true}).click();
    await studio.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');
    assert.equal(await studio.getByRole('button',{name:'TẠO 10 VIDEO',exact:true}).isEnabled(),false);
    await studio.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();
    for(let id=1;id<=10;id++){
      const before=new Set(desktop.context().pages());
      await dialog.getByRole('button',{name:`Đăng nhập Muse ${id}`,exact:true}).click();
      let login;await waitFor(()=>{login=desktop.context().pages().find(page=>page.url()===service&&!before.has(page));return login},'login '+id);
      assert.equal(await login.evaluate(()=>document.cookie.includes('fixture_identity=')),false,'A new account partition must not inherit another account cookie');
      assert.equal(await login.evaluate(()=>typeof window.museTransport),'undefined');
      await login.getByRole('button',{name:'Fixture login',exact:true}).click();
      await login.evaluate(id=>{document.cookie=`fixture_identity=${id}; Path=/; SameSite=Strict`;document.cookie='fixture_session=connected; Path=/; SameSite=Strict';sessionStorage.setItem('fixture_scope',`scope-${id}`)},id);
      await shell.getByRole('button',{name:'← Về Studio',exact:true}).click();
      await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[id-1].authenticated,'verified '+id);
    }
    await dialog.getByRole('button',{name:'Hoàn tất',exact:true}).click();
    await studio.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
    for(let id=1;id<=10;id++)await studio.getByLabel(`Kịch bản cảnh ${id}`,{exact:true}).fill(`Account ${id} landscape`);
    const warmLoads=fixture.state.pageLoads;
    fixture.state.hold=true;
    await studio.getByRole('button',{name:'TẠO 10 ẢNH',exact:true}).click();
    await waitFor(()=>fixture.state.pending.size===10,'ten independent held requests');
    assert.equal(fixture.state.pageLoads,warmLoads,'Warm multi-account requests must reuse the ten hydrated tabs without another navigation');
    assert.equal(desktop.context().pages().filter(page=>page.url().startsWith(service)).length,10,'Only one Muse page per account is needed');
    assert.equal(fixture.state.peak,10);assert.deepEqual(fixture.state.submitted.map(request=>Number(request.identity)).sort((a,b)=>a-b),[1,2,3,4,5,6,7,8,9,10]);
    assert.ok(fixture.state.submitted.every(request=>request.authenticated&&request.prompt.includes(`Scene:\nAccount ${request.identity} landscape`)));
    const active=await studio.evaluate(async()=>(await fetch('/api/status')).json());
    assert.equal(active.executionConcurrency,1,'The shared-account setting stays at one; ten accounts do not need New chat');
    assert.ok(active.accounts.slice(0,10).every(account=>account.running===1));
    const duplicate=await studio.evaluate(async()=>{const response=await fetch('/api/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accountId:4,accountMode:'multiple',prompt:'should not submit'})});return response.status});
    assert.ok([409,429].includes(duplicate));assert.equal(fixture.state.submitted.length,10);
    assert.equal(await studio.getByLabel('Chế độ tài khoản',{exact:true}).isEnabled(),false);
    fixture.releaseAll();fixture.state.hold=false;
    await waitFor(async()=>{const errors=await studio.locator('.scene-error pre').allTextContents();if(errors.length)throw new Error(errors.join('\n'));return await studio.locator('.generated-image').count()===10},'ten results');
    for(let id=1;id<=10;id++){
      const request=fixture.state.submitted.find(request=>Number(request.identity)===id);
      const bytes=await studio.getByTestId(`scene-${id}`).locator('.generated-image').evaluate(async element=>{const blob=await(await fetch(element.src)).blob();return new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(blob)})});
      assert.equal(bytes,fixture.state.outputs.get(request.id),'Each scene must receive its own account result');
    }
    await waitFor(async()=>await studio.getByLabel('Chế độ tài khoản',{exact:true}).isEnabled(),'batch finished');
    fixture.state.behavior='video';fixture.state.hold=true;fixture.state.peak=0;
    await studio.getByRole('button',{name:'Tạo video',exact:true}).click();
    await studio.getByRole('button',{name:'TẠO 10 VIDEO',exact:true}).click();
    await waitFor(()=>fixture.state.pending.size===10,'ten independent held video requests');
    assert.equal(fixture.state.peak,10);assert.deepEqual(fixture.state.submitted.slice(-10).map(request=>Number(request.identity)).sort((a,b)=>a-b),[1,2,3,4,5,6,7,8,9,10]);
    fixture.releaseAll();fixture.state.hold=false;
    await waitFor(async()=>await studio.locator('.scene-card video').count()===10,'ten account video results');
    await waitFor(async()=>await studio.getByLabel('Chế độ tài khoản',{exact:true}).isEnabled(),'video batch finished');
    await studio.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('single');
    await studio.getByLabel('Số luồng:',{exact:true}).selectOption('1');
    await waitFor(async()=>await studio.getByLabel('Số luồng:',{exact:true}).isEnabled(),'explicit serial compatibility choice');
    assert.equal(await studio.getByLabel('Số luồng:',{exact:true}).inputValue(),'1');
    await studio.getByLabel('Số ô',{exact:true}).selectOption('10');
    fixture.state.behavior='video';await studio.getByRole('button',{name:'Tạo video',exact:true}).click();
    await studio.getByLabel('Kịch bản cảnh 2',{exact:true}).fill('Single account video on scene 2');
    await studio.getByTestId('scene-2').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
    await waitFor(async()=>await studio.getByTestId('scene-2').locator('video').count()===1,'single-account video');
    assert.equal(fixture.state.submitted.at(-1).identity,'1','Single mode must route every scene to account 01');
    await waitFor(async()=>await studio.getByLabel('Chế độ tài khoản',{exact:true}).isEnabled(),'single job finished');
    await studio.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');
    await studio.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
    await mkdir(path.join(root,'test-results'),{recursive:true});await studio.screenshot({path:path.join(root,'test-results/multi-account-studio.png')});
    if(!process.env.MUSE_PORTABLE_EXECUTABLE)env.PORT=new URL(studio.url()).port;
    const vaultFile=await readFile(path.join(profile,'account-vault','session-10.bin'));assert.ok(vaultFile.length>0,'Verified sessions must have an encrypted snapshot before quitting');
    await desktop.close();desktop=null;
    ({studio,shell}=await launch());
    assert.equal(await studio.getByLabel('Chế độ tài khoản',{exact:true}).inputValue(),'multiple');
    // Opening the app restores all ten account sessions automatically. No
    // per-account check/login action should be needed on the second launch.
    try{await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts.slice(0,10).every(account=>account.authenticated),'ten persisted cookies',30000)}catch(error){const report=await studio.evaluate(async()=>(await fetch('/api/status')).json());throw new Error(error.message+' '+JSON.stringify({restoring:report.restoringSessions,accounts:report.accounts.slice(0,10).map(({id,state,authenticated,connectionMessage,persistenceMessage})=>({id,state,authenticated,connectionMessage,persistenceMessage}))}))}
    for(const page of desktop.context().pages().filter(page=>page.url().startsWith(service))){const scoped=await page.evaluate(()=>({identity:document.cookie.split('; ').find(value=>value.startsWith('fixture_identity='))?.split('=')[1],scope:sessionStorage.getItem('fixture_scope')}));assert.equal(scoped.scope,`scope-${scoped.identity}`)}
    const encrypted=await readFile(path.join(profile,'account-vault','session-10.bin'));assert.equal(encrypted.includes(Buffer.from('scope-10')),false);assert.equal(encrypted.includes(Buffer.from('connected')),false);
    const saved=await studio.evaluate(async()=>(await fetch('/api/status')).json());assert.deepEqual(saved.accounts.slice(0,10).map(account=>account.label),labels);
    assert.equal(fixture.state.submitted.length,21,'Checking saved sessions must not generate media');
    const beforeProxy=await desktop.evaluate(({session})=>session.fromPartition('persist:muse-02').resolveProxy('https://muse.ai'));
    const otherProxy=await desktop.evaluate(({session})=>session.fromPartition('persist:muse').resolveProxy('https://muse.ai'));
    await studio.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();await studio.getByRole('button',{name:'Proxy Muse 2',exact:true}).click();
    await studio.getByLabel('Bật proxy',{exact:true}).check();await studio.getByLabel('Địa chỉ proxy',{exact:true}).fill('http://127.0.0.1:18123');await studio.getByLabel('Thay tài khoản proxy',{exact:true}).check();await studio.getByLabel('Tên đăng nhập proxy',{exact:true}).fill('fixture-proxy-user');await studio.getByLabel('Mật khẩu proxy',{exact:true}).fill('fixture-proxy-secret');await studio.getByRole('button',{name:'Lưu proxy',exact:true}).click();
    await waitFor(async()=>await studio.getByRole('region',{name:'Proxy tài khoản 2',exact:true}).count()===0,'native proxy saved');
    assert.equal(await desktop.evaluate(({session})=>session.fromPartition('persist:muse-02').resolveProxy('https://muse.ai')),'PROXY 127.0.0.1:18123');
    assert.equal(await desktop.evaluate(({session})=>session.fromPartition('persist:muse').resolveProxy('https://muse.ai')),otherProxy);
    const proxyBytes=await readFile(path.join(profile,'account-vault','proxy-2.bin'));assert.equal(proxyBytes.includes(Buffer.from('fixture-proxy-secret')),false);
    await desktop.close();desktop=null;({studio,shell}=await launch());
    await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts.slice(0,10).every(account=>account.authenticated),'ten sessions after proxy update',60000);
    const proxySaved=await studio.evaluate(async()=>(await fetch('/api/status')).json());assert.equal(proxySaved.accounts[1].proxy.hasPassword,true);assert.equal(JSON.stringify(proxySaved).includes('fixture-proxy-secret'),false);assert.equal(await desktop.evaluate(({session})=>session.fromPartition('persist:muse-02').resolveProxy('https://muse.ai')),'PROXY 127.0.0.1:18123');
    await studio.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();await studio.getByRole('button',{name:'Proxy Muse 2',exact:true}).click();await studio.getByLabel('Bật proxy',{exact:true}).uncheck();await studio.getByRole('button',{name:'Lưu proxy',exact:true}).click();
    await waitFor(async()=>await studio.getByRole('region',{name:'Proxy tài khoản 2',exact:true}).count()===0,'native proxy disabled');assert.equal(await desktop.evaluate(({session})=>session.fromPartition('persist:muse-02').resolveProxy('https://muse.ai')),beforeProxy);

  } finally {fixture.releaseAll();await desktop?.close();fixture.server.closeAllConnections();await new Promise(resolve=>fixture.server.close(resolve));await rm(profile,{recursive:true,force:true})}
});

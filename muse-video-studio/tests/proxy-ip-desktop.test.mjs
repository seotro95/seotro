import {test} from 'node:test';import assert from 'node:assert/strict';import http from 'node:http';
import {_electron} from 'playwright-core';import {createRequire} from 'node:module';import {pathToFileURL,fileURLToPath} from 'node:url';
import {mkdtemp,rm} from 'node:fs/promises';import path from 'node:path';import os from 'node:os';
const require=createRequire(import.meta.url);
test('Electron measures separate exit IPs through two authenticated proxies without sending session cookies (fixture)',{timeout:60000},async()=>{
 const seen=[];const servers=[];const root=await mkdtemp(path.join(os.tmpdir(),'muse-proxy-ip-'));let desktop;
 try{
  for(const id of [1,2]){const server=http.createServer((req,res)=>{const auth='Basic '+Buffer.from(`user${id}:password${id}`).toString('base64');if(req.headers['proxy-authorization']!==auth){res.writeHead(407,{'Proxy-Authenticate':'Basic realm="Fixture"'});res.end();return}seen.push({id,cookie:req.headers.cookie,url:req.url});res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({ip:`203.0.113.${id}`}))});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));servers.push(server)}
  desktop=await _electron.launch({executablePath:require('electron'),args:[...(process.env.MUSE_ELECTRON_HEADLESS==='1'?['--ozone-platform=headless']:[]),...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX==='1'?['--no-sandbox','--disable-gpu']:[]),fileURLToPath(new URL('./fixtures/proxy-ip-app.cjs',import.meta.url)),'--user-data-dir='+root],timeout:30000});await desktop.firstWindow();
  const outputs=await desktop.evaluate(async({session,net},{module,ports})=>{
   const {requestProxyIP}=await globalThis.proxyIP;const results=[];
   for(const [index,port]of ports.entries()){const id=index+1;const scoped=session.fromPartition(`persist:proxy-ip-${id}`);await scoped.setProxy({mode:'fixed_servers',proxyRules:`http://127.0.0.1:${port}`});await scoped.cookies.set({url:'http://ip-check.fixture.invalid',name:'must-not-leak',value:'private-cookie'});results.push(await requestProxyIP({session:scoped,request:options=>net.request(options),url:'http://ip-check.fixture.invalid/ip',credentials:info=>info.isProxy&&info.host==='127.0.0.1'&&info.port===port?{username:`user${id}`,password:`password${id}`}:null}))}
   return results;
  },{module:pathToFileURL(path.resolve(import.meta.dirname,'../desktop/proxy-ip.mjs')).href,ports:servers.map(server=>server.address().port)});
  assert.deepEqual(outputs,['203.0.113.1','203.0.113.2']);assert.deepEqual(seen.map(r=>r.id),[1,2]);assert.ok(seen.every(row=>!row.cookie&&row.url==='http://ip-check.fixture.invalid/ip'));
 }finally{await desktop?.close();for(const server of servers){server.closeAllConnections();await new Promise(resolve=>server.close(resolve))}await rm(root,{recursive:true,force:true})}
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {AutomationServer} from '../desktop/automation-server.mjs';
async function freePort(){const server=http.createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const port=server.address().port;await new Promise(resolve=>server.close(resolve));return port}

test('MCP Streamable HTTP initializes, lists scoped tools, deduplicates paid actions and marks destructive operations',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-mcp-'));const calls=[];
  const api=await new AutomationServer({userData:root,version:'test',dispatch:async(action,data)=>{calls.push({action,data});if(action==='batch'||action==='run')return {batchId:'fixture-batch',sceneIds:[1,2]};if(action==='save-media')return {count:2,folder:'approved-folder'};if(action==='status')return {ready:true,slotCount:40};return {updated:true}}}).load();
  try{
    await api.configure({enabled:true,port:await freePort()});const url=api.snapshot().address;const key=api.snapshot().key;let id=0;
    const request=async(method,params)=>{const response=await fetch(url+'/mcp',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:++id,method,params})});assert.equal(response.status,200);return response.json()};
    assert.equal((await fetch(url+'/mcp')).status,401);
    const get=await fetch(url+'/mcp',{headers:{Authorization:'Bearer '+key}});assert.equal(get.status,405);assert.equal(get.headers.get('allow'),'POST');
    const init=await request('initialize',{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'fixture-client',version:'1'}});assert.equal(init.result.protocolVersion,'2025-11-25');assert.equal(init.result.serverInfo.name,'muse-ai-studio');assert.equal(JSON.stringify(init).includes(key),false);
    const notification=await fetch(url+'/mcp',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:'{"jsonrpc":"2.0","method":"notifications/initialized"}'});assert.equal(notification.status,202);assert.equal(await notification.text(),'');
    const tools=(await request('tools/list',{})).result.tools;assert.equal(tools.length,9);assert.equal(tools.find(tool=>tool.name==='studio_status').annotations.readOnlyHint,true);assert.equal(tools.find(tool=>tool.name==='studio_clear_library').annotations.destructiveHint,true);
    const call=(name,args={})=>request('tools/call',{name,arguments:args});
    assert.equal((await call('studio_status')).result.structuredContent.slotCount,40);
    const args={prompts:['One','Two'],requestId:'mcp-batch-one'};const first=await call('studio_create_batch',args);const second=await call('studio_create_batch',args);assert.deepEqual(first.result.structuredContent,second.result.structuredContent);assert.equal(calls.filter(call=>call.action==='batch').length,1);assert.equal(calls.find(call=>call.action==='batch').data.requestId,undefined);
    assert.equal((await call('studio_create_batch',{...args,prompts:['Changed']})).result.isError,true);
    assert.equal((await call('studio_clear_library',{})).result.isError,true);assert.equal(calls.filter(call=>call.action==='clear-media').length,0);
    assert.equal((await call('studio_clear_library',{confirm:'DELETE_ALL_MEDIA'})).result.isError,false);
    assert.equal((await call('studio_set_scene',{sceneId:40,prompt:'New prompt'})).result.isError,false);assert.equal(calls.at(-1).action,'set-scene');
    assert.equal((await call('studio_configure_layout',{slotCount:30,requestedConcurrency:30})).result.isError,false);
    assert.equal((await call('studio_run',{sceneIds:[40],requestId:'mcp-run-one'})).result.isError,false);await call('studio_run',{sceneIds:[40],requestId:'mcp-run-one'});assert.equal(calls.filter(call=>call.action==='run').length,1);
    assert.equal((await call('studio_save_results',{output:'video'})).result.structuredContent.folder,'approved-folder');
    assert.equal((await call('studio_configure_layout',{javascript:'not accepted'})).result.isError,true);
    assert.equal((await request('arbitrary/execute',{})).error.code,-32601);assert.equal((await call('execute_shell',{})).error.code,-32602);
  }finally{await api.close();await rm(root,{recursive:true,force:true})}
});

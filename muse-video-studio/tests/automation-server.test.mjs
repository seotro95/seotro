import {test} from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {AutomationServer} from '../desktop/automation-server.mjs';
async function freePort(){const server=http.createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const port=server.address().port;await new Promise(resolve=>server.close(resolve));return port}

test('local automation requires a key, binds loopback, deduplicates batches, serves bytes, rotates keys and persists on/off configuration',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-automation-'));let calls=0;let release;
  const dispatch=async(action,data)=>{if(action==='status')return {busy:false};if(action==='batch'){calls++;await new Promise(resolve=>release=resolve);return {batchId:'fixture-batch',sceneIds:[1,2]}}if(action==='media')return {base64:'aGVsbG8=',mimeType:'image/png'};if(action==='clear-media')return {deleted:2};return {stopping:true}};
  let api=await new AutomationServer({userData:root,dispatch,version:'test'}).load();
  try{
    assert.equal(api.snapshot().enabled,false);const port=await freePort();await api.configure({enabled:true,port});
    assert.equal(api.server.address().address,'127.0.0.1');const url=api.snapshot().address;let key=api.snapshot().key;
    const request=(route,options={})=>fetch(url+route,{...options,headers:{Authorization:'Bearer '+key,...options.headers}});
    assert.equal((await fetch(url+'/v1/status')).status,401);
    assert.equal((await request('/v1/status',{headers:{Origin:'https://untrusted.example'}})).status,403);
    const state=await(await request('/v1/status')).json();assert.equal(state.version,'test');assert.equal(JSON.stringify(state).includes(key),false);
    assert.equal((await request('/v1/status?token=not-accepted')).status,400);
    assert.equal((await request('/v1/media',{method:'DELETE',headers:{'Content-Type':'application/json'},body:'null'})).status,400);
    const batch={method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':'batch-1'},body:JSON.stringify({prompts:['a','b']})};
    const first=request('/v1/batches',batch);const second=request('/v1/batches',batch);
    while(!release)await new Promise(resolve=>setTimeout(resolve,10));assert.equal(calls,1);release();
    assert.deepEqual(await(await first).json(),await(await second).json());
    assert.equal((await request('/v1/batches',batch)).status,202);assert.equal(calls,1);
    assert.equal((await request('/v1/batches',{...batch,body:'{"prompts":["different"]}'})).status,409);
    const media=await request('/v1/media/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');assert.equal(media.headers.get('content-type'),'image/png');assert.equal(Buffer.from(await media.arrayBuffer()).toString(),'hello');
    assert.equal((await request('/v1/media',{method:'DELETE',headers:{'Content-Type':'application/json'},body:'{}'})).status,400);
    assert.equal((await request('/v1/media',{method:'DELETE',headers:{'Content-Type':'application/json'},body:'{"confirm":"DELETE_ALL_MEDIA"}'})).status,200);
    const configFile=api.file;api.file=path.join(root,'missing-directory','settings.json');await assert.rejects(api.rotate());assert.equal(api.snapshot().key,key,'A failed key write must preserve the previous working key');api.file=configFile;
    const old=key;await api.rotate();key=api.snapshot().key;assert.notEqual(key,old);
    assert.equal((await request('/v1/status',{headers:{Authorization:'Bearer '+old}})).status,401);
    await api.close();api=await new AutomationServer({userData:root,dispatch,version:'test'}).load();assert.equal(api.snapshot().listening,true);assert.equal(api.snapshot().key,key);
    assert.equal((await request('/v1/status')).status,200);await api.configure({enabled:false,port});
    api=await new AutomationServer({userData:root,dispatch,version:'test'}).load();assert.equal(api.snapshot().listening,false);
  }finally{await api.close();await rm(root,{recursive:true,force:true})}
});

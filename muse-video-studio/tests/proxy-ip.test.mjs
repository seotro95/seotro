import {test} from 'node:test';import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {AccountProxies} from '../desktop/account-proxy.mjs';
import {requestProxyIP} from '../desktop/proxy-ip.mjs';
test('IP checks use the exact configured session, reject DIRECT, clear old IP on edits and never expose credentials',async()=>{
 const sessions=new Map([1,2].map(id=>[id,{id,setProxy:async()=>{},closeAllConnections:async()=>{},resolveProxy:async()=>`PROXY proxy${id}.invalid:8000`}]));
 const calls=[];const manager=new AccountProxies({storage:{read:async()=>null,write:async()=>{}},sessionForAccount:id=>sessions.get(id),lookupIP:async(session,credentials)=>{calls.push(session.id);assert.deepEqual(credentials({isProxy:true,host:`proxy${session.id}.invalid`,port:8000}),{username:`u${session.id}`,password:`secret${session.id}`});return `203.0.113.${session.id}`}});
 for(const id of [1,2])await manager.configure(id,{enabled:true,server:`http://proxy${id}.invalid:8000`,username:`u${id}`,password:`secret${id}`});
 assert.equal((await manager.checkIP(1)).exitIP,'203.0.113.1');assert.equal((await manager.checkIP(2)).exitIP,'203.0.113.2');assert.deepEqual(calls,[1,2]);assert.ok(!JSON.stringify(manager.snapshot(1)).includes('secret1'));
 await manager.configure(1,{enabled:true,server:'http://proxy1.invalid:8000'});assert.equal(manager.snapshot(1).exitIP,undefined);
 sessions.get(1).resolveProxy=async()=> 'DIRECT';const failed=await manager.checkIP(1);assert.equal(failed.ipState,'error');assert.equal(failed.exitIP,'');assert.deepEqual(calls,[1,2]);
 await manager.configure(2,{enabled:false});await assert.rejects(manager.checkIP(2),/Bật và lưu proxy/);
});
test('network IP helper validates IPv4/IPv6, bounds response size, times out and cancels requests',async()=>{
 const run=async(payload,{stall=false,signal,timeoutMs=100}={})=>{
  let options;let aborted=false;const request=opts=>{options=opts;const req=new EventEmitter();req.setHeader=()=>{};req.abort=()=>{aborted=true};req.end=()=>{if(stall)return;queueMicrotask(()=>{const res=new EventEmitter();res.statusCode=200;req.emit('response',res);res.emit('data',Buffer.from(payload));res.emit('end')})};return req};
  const promise=requestProxyIP({session:'account-session',request,signal,timeoutMs});assert.equal(options.session,'account-session');assert.equal(options.useSessionCookies,false);assert.equal(options.credentials,undefined);return {promise,get aborted(){return aborted}};
 };
 assert.equal(await (await run('{"ip":"2001:db8::1"}')).promise,'2001:db8::1');assert.equal(await (await run('{"ip":"203.0.113.7"}')).promise,'203.0.113.7');
 await assert.rejects((await run('{"ip":"not-an-ip"}')).promise,/hợp lệ/);await assert.rejects((await run('a'.repeat(4097))).promise,/quá lớn/);
 const timed=await run('',{stall:true,timeoutMs:5});await assert.rejects(timed.promise,/Hết thời gian/);assert.equal(timed.aborted,true);
 const control=new AbortController();const cancelled=await run('',{stall:true,signal:control.signal});control.abort();await assert.rejects(cancelled.promise,/Đã dừng/);assert.equal(cancelled.aborted,true);
});

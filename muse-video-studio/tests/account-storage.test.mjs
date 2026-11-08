import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
import {randomBytes,createCipheriv,createDecipheriv} from 'node:crypto';
import {AccountStorage} from '../desktop/account-storage.mjs';
import {AccountProxies,normalizeProxy} from '../desktop/account-proxy.mjs';
const key=randomBytes(32);
const codec={isEncryptionAvailable:()=>true,encryptString:text=>{const iv=randomBytes(12);const cipher=createCipheriv('aes-256-gcm',key,iv);const bytes=Buffer.concat([cipher.update(text),cipher.final()]);return Buffer.concat([iv,cipher.getAuthTag(),bytes])},decryptString:bytes=>{const cipher=createDecipheriv('aes-256-gcm',key,bytes.subarray(0,12));cipher.setAuthTag(bytes.subarray(12,28));return Buffer.concat([cipher.update(bytes.subarray(28)),cipher.final()]).toString()}};

test('session-only cookies and scoped sessionStorage survive an encrypted save without overwriting fresher cookies',async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-vault-'));const vault=new AccountStorage({userData:root,codec,serviceURL:'https://muse.ai/'});
 const cookies=[{name:'session',value:'private-session-value',domain:'muse.ai',path:'/',secure:true,httpOnly:true,session:true,hostOnly:true},{name:'other',value:'foreign',domain:'other.invalid',path:'/'},{name:'expired',value:'old',domain:'muse.ai',path:'/',expirationDate:1}];
 const session={cookies:{get:async()=>cookies,flushStore:async()=>{}},flushStorageData:()=>{}};
 try{
   await vault.capture(2,session,{isClosed:()=>false,evaluate:async()=>({scope:'account-2-secret'})});
   const bytes=await readFile(vault.file(2,'session'));assert.equal(bytes.includes(Buffer.from('private-session-value')),false);assert.equal(bytes.includes(Buffer.from('account-2-secret')),false);
   assert.deepEqual(await vault.savedIds(),[2]);const restored=[];
   const restoredStorage=await vault.restore(2,{cookies:{get:async()=>[],set:async value=>restored.push(value)}});
   assert.deepEqual(restoredStorage,{scope:'account-2-secret'});assert.equal(restored.length,1);assert.equal(restored[0].value,'private-session-value');assert.equal(restored[0].expirationDate,undefined,'Do not extend a session cookie with an artificial expiry');
   restored.length=0;await vault.restore(2,{cookies:{get:async()=>[cookies[0]],set:async value=>restored.push(value)}});assert.equal(restored.length,0);
   const otherOrigin=new AccountStorage({userData:root,codec,serviceURL:'http://127.0.0.1:1234/'});assert.deepEqual(await otherOrigin.restore(2,{cookies:{get:async()=>[],set:async()=>{throw new Error('Do not restore tokens to another origin')}}}),{});
   assert.deepEqual(await vault.restore(3,{cookies:{get:async()=>[],set:async()=>{throw new Error('must not set another account')}}}),{});
   const unavailable=new AccountStorage({userData:root,codec:{isEncryptionAvailable:()=>false},serviceURL:'https://muse.ai/'});await assert.rejects(unavailable.write(3,'session',cookies),/SECURE_STORAGE_UNAVAILABLE/);
 }finally{await rm(root,{recursive:true,force:true})}
});

test('per-account proxy settings are optional, encrypted, independently applied and credentials only reach the matching proxy challenge',async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'muse-proxy-'));const vault=new AccountStorage({userData:root,codec,serviceURL:'https://muse.ai/'});const proxy=await new AccountProxies({storage:vault}).load();const calls=[];
 const session1={setProxy:async value=>calls.push([1,value]),closeAllConnections:async()=>{}};const session2={setProxy:async value=>calls.push([2,value]),closeAllConnections:async()=>{}};
 try{
   await proxy.apply(1,session1);await proxy.apply(2,session2);assert.deepEqual(calls[0],[1,{mode:'direct'}]);
   await proxy.configure(2,{enabled:true,server:'http://127.0.0.1:8123',username:'proxy-user',password:'proxy-password'});
   assert.equal(proxy.snapshot(1).enabled,false);assert.equal(proxy.snapshot(2).hasPassword,true);assert.equal(JSON.stringify(proxy.snapshot(2)).includes('proxy-password'),false);
   assert.equal((await readFile(vault.file(2,'proxy'))).includes(Buffer.from('proxy-password')),false);
   assert.deepEqual(proxy.credentials({session:session2},{isProxy:true,host:'127.0.0.1',port:8123}),{username:'proxy-user',password:'proxy-password'});
   for(const [contents,info]of [[{session:session1},{isProxy:true,host:'127.0.0.1',port:8123}],[{session:session2},{isProxy:false,host:'127.0.0.1',port:8123}],[{session:session2},{isProxy:true,host:'another.invalid',port:8123}]])assert.equal(proxy.credentials(contents,info),null);
   const reopened=await new AccountProxies({storage:vault}).load();assert.equal(reopened.snapshot(2).enabled,true);await reopened.configure(2,{enabled:true,server:'http://127.0.0.1:8123'});assert.equal(reopened.snapshot(2).hasPassword,true);
   await proxy.configure(2,{enabled:false});assert.equal(proxy.snapshot(2).enabled,false);assert.deepEqual(calls.at(-1),[2,{mode:'direct'}]);
   for(const server of ['http://user:password@proxy.invalid:80','https://proxy.invalid/path','file:///tmp/test'])assert.throws(()=>normalizeProxy({enabled:true,server}),/PROXY_INVALID/);
   assert.throws(()=>normalizeProxy({enabled:true,server:'socks5://proxy.invalid:1080',username:'name',password:'secret'}),/SOCKS5/);
   assert.equal(normalizeProxy({enabled:true,server:'socks5://proxy.invalid:1080'}).server,'socks5://proxy.invalid:1080');
 }finally{await rm(root,{recursive:true,force:true})}
});

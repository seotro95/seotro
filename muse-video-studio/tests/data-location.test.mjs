import {test} from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';import path from 'node:path';import os from 'node:os';
import {dataLocation,importData} from '../desktop/data-location.mjs';import {storageCodec} from '../desktop/storage-codec.mjs';
test('Windows encryption never calls the Linux backend API; DPAPI fallback remains encrypted',async()=>{
 let backendCalls=0;const crypto={isAsyncEncryptionAvailable:async()=>true,getSelectedStorageBackend:()=>{backendCalls++;throw new Error('Linux only')},encryptStringAsync:async value=>Buffer.from('encrypted:'+value),decryptStringAsync:async bytes=>({result:bytes.toString().slice(10)})};
 const codec=await storageCodec(crypto,'win32');assert.equal(codec.isEncryptionAvailable(),true);assert.equal(codec.getSelectedStorageBackend(),undefined);assert.equal(backendCalls,0);assert.equal(await codec.decryptString(await codec.encryptString('fixture')),'fixture');
 const fallback=await storageCodec({...crypto,isAsyncEncryptionAvailable:async()=>false,isEncryptionAvailable:()=>true,encryptString:value=>Buffer.from('DPAPI:'+value),decryptString:bytes=>bytes.toString().slice(6)},'win32');assert.equal(fallback.isEncryptionAvailable(),true);assert.equal((await fallback.encryptString('fixture')).toString(),'DPAPI:fixture');
});
test('Windows data survives changing program directories; importing all old profiles preserves original data and uses a separate destination',async()=>{
 const tmp=await mkdtemp(path.join(os.tmpdir(),'muse-location-'));const first=path.join(tmp,'program-1');const localData=path.join(tmp,'local');const legacy=path.join(first,'.data/muse-desktop');
 try{
  for(let id=1;id<=10;id++){const folder=path.join(legacy,'Partitions',`muse-${id}`);await mkdir(folder,{recursive:true});await writeFile(path.join(folder,'Cookies'),`fixture-cookie-${id}`)}await writeFile(path.join(legacy,'studio-port'),'18788');
  const location=dataLocation({root:first,platform:'win32',isPackaged:true,localData});
  for(let id=1;id<=10;id++)assert.equal(await readFile(path.join(location.directory,'Partitions',`muse-${id}`,'Cookies'),'utf8'),`fixture-cookie-${id}`);
  const next=dataLocation({root:path.join(tmp,'program-2'),platform:'win32',isPackaged:true,localData});assert.equal(next.directory,location.directory);
  await assert.rejects(importData(location,next.directory,location.directory),/DATA_IMPORT_INVALID/);
  const imported=await importData(location,first,location.directory);assert.notEqual(imported,location.directory);assert.equal(await readFile(path.join(imported,'studio-port'),'utf8'),'18788');assert.equal(await readFile(path.join(legacy,'Partitions','muse-10','Cookies'),'utf8'),'fixture-cookie-10');
  const reopened=dataLocation({root:path.join(tmp,'program-3'),platform:'win32',isPackaged:true,localData});assert.equal(reopened.directory,imported);
 }finally{await rm(tmp,{recursive:true,force:true})}
});

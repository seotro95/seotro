import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { FolderExports } from '../desktop/folder-export.mjs';

test('folder exports remember the chosen root and never overwrite existing files or folders',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-folder-test-'));
  const userData=path.join(root,'profile');const destination=path.join(root,'exports');
  await mkdir(userData);await mkdir(destination);
  let chosen=0;const opened=[];
  const make=()=>new FolderExports({userData,chooseDirectory:async()=>{chosen++;return destination},openDirectory:async directory=>{opened.push(directory)}});
  const manager=make();
  const bytes=Uint8Array.from([137,80,78,71,13,10,26,10]).buffer;
  const metadata={kind:'image',count:2,first:'000001',last:'000002',namespace:'a'.repeat(32)};
  const filename=number=>`image-${String(number).padStart(6,'0')}-scene-01-${metadata.namespace}.png`;
  try{
    await manager.ensureDirectory();const task=await manager.begin(metadata);
    await assert.rejects(manager.write({id:task.id,name:'../outside.png',bytes}));
    const duplicate=await Promise.allSettled([manager.write({id:task.id,name:filename(1),bytes}),manager.write({id:task.id,name:filename(1),bytes})]);
    assert.equal(duplicate.filter(result=>result.status==='fulfilled').length,1);
    await assert.rejects(manager.finish(task.id),/chưa lưu đủ/);
    await manager.write({id:task.id,name:filename(2),bytes});
    const saved=await manager.finish(task.id);
    assert.equal((await readdir(saved.directory)).length,2);
    assert.deepEqual(await readFile(path.join(saved.directory,filename(1))),Buffer.from(bytes));
    const next=make();await next.ensureDirectory();assert.equal(chosen,1);
    const same=await next.begin(metadata);
    assert.notEqual(same.name,task.name);
    next.abort(same.id);
    assert.equal((await readdir(saved.directory)).length,2);
    assert.equal(opened.length,1);
  }finally{await rm(root,{recursive:true,force:true})}
});

test('cancelled directory selection creates no export and accepts no renderer-supplied path',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'muse-folder-cancel-'));
  try{
    const manager=new FolderExports({userData:root,chooseDirectory:async()=>null,openDirectory:async()=>{}});
    assert.deepEqual(await manager.ensureDirectory(),{cancelled:true});
    await assert.rejects(manager.begin({kind:'image',count:1,first:'1',last:'1',namespace:'a'.repeat(32),directory:'/tmp/not-granted'}));
    assert.equal((await readdir(root)).length,0);
  }finally{await rm(root,{recursive:true,force:true})}
});

import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';

const image=readFileSync(new URL('../../public/demo-image.png',import.meta.url)).toString('base64');

test('recovery opens without reading the existing media store and retains workspace and stored results',async({page})=>{
  await page.goto('/');
  await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toBeEditable();
  await page.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Keep my saved prompt');
  await expect.poll(()=>page.evaluate(()=>JSON.parse(localStorage.getItem('muse-workstation-v1')!).scenes[0].prompt)).toBe('Keep my saved prompt');
  await page.evaluate(async(base64)=>{
    const db=await new Promise<IDBDatabase>((resolve,reject)=>{const req=indexedDB.open('muse-studio-media-v1',1);req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error)});
    await new Promise<void>((resolve,reject)=>{
      const tx=db.transaction('results','readwrite');
      tx.objectStore('results').put({id:'existing-media',sceneId:1,prompt:'Keep my saved prompt',createdAt:new Date().toISOString(),persisted:true,media:{kind:'image',base64,mimeType:'image/png',demo:false}});
      tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);
    });db.close();
  },image);
  await page.addInitScript(()=>{
    if(new URLSearchParams(location.search).get('recovery')!=='1')return;
    (window as any).mediaOpenAttempts=0;
    const original=IDBFactory.prototype.open;
    IDBFactory.prototype.open=function(...args:Parameters<IDBFactory['open']>){
      if(args[0]==='muse-studio-media-v1'){(window as any).mediaOpenAttempts++;throw new Error('Media restore is unavailable in this test');}
      return original.apply(this,args);
    };
  });
  await page.goto('/?recovery=1');
  await expect(page.getByText('Chế độ khôi phục Studio',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toHaveValue('Keep my saved prompt');
  await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toBeEditable();
  await expect(page.getByRole('button',{name:'Xóa toàn bộ',exact:true})).toBeDisabled();
  expect(await page.evaluate(()=>(window as any).mediaOpenAttempts)).toBe(0);
  await page.goto('/');
  await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toHaveValue('Keep my saved prompt');
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
  await expect(page.locator('.history-entry')).toHaveCount(1);
  const saved=await page.evaluate(async()=>{
    const db=await new Promise<IDBDatabase>(resolve=>{const r=indexedDB.open('muse-studio-media-v1',1);r.onsuccess=()=>resolve(r.result)});
    const result=await new Promise<any>(resolve=>{const r=db.transaction('results').objectStore('results').get('existing-media');r.onsuccess=()=>resolve(r.result)});db.close();return result;
  });
  expect(saved.media.base64).toBe(image);
});

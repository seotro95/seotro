import{test,expect}from'@playwright/test';
import type{Page}from'@playwright/test';
import{readFile}from'node:fs/promises';

const video=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');
const image=await readFile(new URL('../../public/demo-image.png',import.meta.url));
const clearName='Xoá tất cả video đã tạo';
const confirmName='Xác nhận xoá tất cả video';
const accounts=[{id:1,state:'ready',authenticated:true,sessionAuthenticated:true,executionConcurrency:2}];
async function records(page:Page){return page.evaluate(()=>new Promise<any[]>((resolve,reject)=>{const open=indexedDB.open('muse-studio-media-v1',1);open.onsuccess=()=>{const request=open.result.transaction('results').objectStore('results').getAll();request.onsuccess=()=>{open.result.close();resolve(request.result)};request.onerror=()=>reject(request.error)}}));}
async function seed(page:Page){
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,canRecoverMedia:true,executionConcurrency:2,accounts}}));
 await page.goto('/');await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toBeEditable();
 await page.evaluate(async({video,image})=>{
  const workspace=JSON.parse(localStorage.getItem('muse-workstation-v1')!);
  const settings={...workspace.settings,slotCount:2,requestedConcurrency:2,accountMode:'single',accountPlanMode:'expanded',singleAccountId:1,output:'video',syncOperations:false,r2v:false};
  const scenes=Array.from({length:400},(_,i)=>({prompt:`Keep prompt ${i+1}`,outputName:`name ${i+1}`,enabled:true,syncSelected:false}));
  localStorage.setItem('muse-workstation-v1',JSON.stringify({version:1,settings,scenes}));
  const db=await new Promise<IDBDatabase>((resolve,reject)=>{const open=indexedDB.open('muse-studio-media-v1',1);open.onupgradeneeded=()=>open.result.createObjectStore('results',{keyPath:'id'});open.onsuccess=()=>resolve(open.result);open.onerror=()=>reject(open.error)});
  await new Promise<void>((resolve,reject)=>{const tx=db.transaction('results','readwrite'),store=tx.objectStore('results');for(const [id,sceneId,kind,createdAt]of [['video-current',1,'video','2026-11-21T10:00:00Z'],['video-old',1,'video','2026-11-21T09:00:00Z'],['video-hidden',300,'video','2026-11-21T08:00:00Z'],['image-kept',1,'image','2026-11-21T10:00:00Z']]as const)store.put({id,batchId:id,sceneId,prompt:`Keep prompt ${sceneId}`,createdAt,persisted:true,settings:{...settings,output:kind},media:{kind,base64:kind==='video'?video:image,mimeType:kind==='video'?'video/mp4':'image/png',demo:false,outputName:`name ${sceneId}`}});tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error)});db.close();
  const queuedb=await new Promise<IDBDatabase>((resolve,reject)=>{const open=indexedDB.open('muse-studio-script-queue-v1',1);open.onupgradeneeded=()=>open.result.createObjectStore('queue');open.onsuccess=()=>resolve(open.result);open.onerror=()=>reject(open.error)});
  await new Promise<void>((resolve,reject)=>{const tx=queuedb.transaction('queue','readwrite'),store=tx.objectStore('queue');const entries=[{id:'q-video',index:1,prompt:'Archived video prompt',outputName:'old video',selected:true,state:'done',savedId:'video-old'},{id:'q-image',index:2,prompt:'Archived image prompt',outputName:'kept image',selected:true,state:'done',savedId:'image-kept'},{id:'q-hidden',index:3,prompt:'Hidden video prompt',outputName:'hidden video',selected:false,state:'done',savedId:'video-hidden'},{id:'q-pending',index:4,prompt:'Never automatically run this prompt',outputName:'future output',selected:false,state:'pending'}];store.put({kind:'order',ids:['queue-file']},'order');store.put({kind:'file',id:'queue-file',name:'mixed-results.txt',selected:true,entryIds:entries.map(row=>row.id)},'file:queue-file');for(const entry of entries)store.put({kind:'entry',...entry},'entry:'+entry.id);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error)});queuedb.close();
 },{video,image:image.toString('base64')});
 await page.reload();await expect(page.getByRole('button',{name:clearName,exact:true})).toBeEnabled();
 await expect(page.locator('.scene-card video')).toHaveCount(1);
}

test('Clear all videos covers old versions and hidden slots with sync off; cancel preserves files, confirm preserves images, prompts and queue history',async({page})=>{
 let generated=0;await page.route('**/api/video',route=>{generated++;return route.fulfill({status:500,json:{error:'No generation expected'}})});await seed(page);
 const chosen=page.waitForEvent('filechooser');await page.getByTestId('scene-2').locator('.select-image').click();await(await chosen).setFiles({name:'reference.png',mimeType:'image/png',buffer:image});await expect(page.getByTestId('scene-2').locator('.scene-image img')).toHaveCount(1);const referenceURL=await page.getByTestId('scene-2').locator('.scene-image img').getAttribute('src');
 const queue=page.getByRole('region',{name:'Hàng chờ TXT SRT'});
 const queueBefore=await page.evaluate(()=>new Promise<any[]>((resolve,reject)=>{const open=indexedDB.open('muse-studio-script-queue-v1',1);open.onsuccess=()=>{const request=open.result.transaction('queue').objectStore('queue').getAll();request.onsuccess=()=>{open.result.close();resolve(request.result)};request.onerror=()=>reject(request.error)}}));
 const workspaceBefore=await page.evaluate(()=>localStorage.getItem('muse-workstation-v1'));
 await expect(page.getByRole('button',{name:'Đồng bộ thao tác: TẮT',exact:true})).toBeVisible();await expect(page.getByLabel('Chọn đồng bộ cảnh 1',{exact:true})).not.toBeChecked();
 await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
 await expect(page.getByTestId('scene-1').locator('.status-badge')).toContainText('Hoàn tất');
 const imageURL=await page.getByTestId('scene-1').locator('.generated-image').getAttribute('src');await page.evaluate(()=>{(window as any).revokedURLs=[];const original=URL.revokeObjectURL;URL.revokeObjectURL=url=>{(window as any).revokedURLs.push(url);original(url)}});
 await page.getByRole('button',{name:clearName,exact:true}).click();const dialog=page.getByRole('dialog',{name:clearName+'?'});await expect(dialog).toContainText('Sẽ xoá 3 kết quả video');await expect(dialog).toContainText('kể cả ô đang ẩn');await dialog.getByRole('button',{name:'Hủy',exact:true}).click();expect((await records(page)).filter(row=>row.media.kind==='video')).toHaveLength(3);
 await page.getByRole('button',{name:clearName,exact:true}).click();await page.getByRole('button',{name:confirmName,exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('button',{name:clearName,exact:true})).toBeDisabled();
 const remaining=await records(page);expect(remaining.map(row=>row.id)).toEqual(['image-kept']);expect(remaining[0].media.base64).toBe(image.toString('base64'));
 await expect(page.getByTestId('scene-2').locator('.scene-image img')).toHaveAttribute('src',referenceURL!);const revoked=await page.evaluate(()=>(window as any).revokedURLs);expect(revoked).not.toContain(referenceURL);expect(revoked).not.toContain(imageURL);expect(revoked).toHaveLength(3);
 await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toHaveValue('Keep prompt 1');await expect(page.getByLabel('Tên tệp cảnh 1',{exact:true})).toHaveValue('name 1');await expect(page.getByTestId('scene-1').locator('.status-badge')).toContainText('Hoàn tất');await expect(page.getByRole('button',{name:'Xem ảnh cảnh 1',exact:true})).toHaveCount(1);
 await expect(queue).toContainText('1 xong · 0 lỗi/dừng · 2 đã xoá/không còn kết quả');await queue.locator('summary').first().click();await expect(queue.locator('.queue-entry').filter({hasText:'old video'})).toContainText('Đã xoá/không còn kết quả');
 await page.evaluate(()=>{(window as any).exportedNames=[];(window as any).showDirectoryPicker=async()=>({getDirectoryHandle:async(name:string,options?:{create?:boolean})=>{if(!options?.create)throw new DOMException('Missing directory','NotFoundError');return{name,getFileHandle:async(filename:string)=>({createWritable:async()=>({write:async()=>{(window as any).exportedNames.push(filename)},close:async()=>{}})})}}})});
 await page.getByRole('button',{name:'Tải kết quả đã chọn',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Bỏ qua 1 kết quả'})).toHaveCount(1);expect(await page.evaluate(()=>(window as any).exportedNames)).toEqual(['kept image.png']);
 const queueAfter=await page.evaluate(()=>new Promise<any[]>((resolve,reject)=>{const open=indexedDB.open('muse-studio-script-queue-v1',1);open.onsuccess=()=>{const request=open.result.transaction('queue').objectStore('queue').getAll();request.onsuccess=()=>{open.result.close();resolve(request.result)};request.onerror=()=>reject(request.error)}}));expect(queueAfter).toEqual(queueBefore);
 await page.reload();await expect(queue).toContainText('2 đã xoá/không còn kết quả');await expect(page.getByRole('button',{name:clearName,exact:true})).toBeDisabled();expect(generated).toBe(0);
 await page.getByRole('button',{name:'Tạo video',exact:true}).click();await page.getByLabel('Số ô',{exact:true}).selectOption('400');await expect(page.getByLabel('Kịch bản cảnh 300',{exact:true})).toHaveValue('Keep prompt 300');await expect(page.getByLabel('Tên tệp cảnh 300',{exact:true})).toHaveValue('name 300');await expect(page.locator('.scene-card video')).toHaveCount(0);
 const after=await page.evaluate(()=>JSON.parse(localStorage.getItem('muse-workstation-v1')!));const before=JSON.parse(workspaceBefore!);expect(after.scenes).toEqual(before.scenes);expect(after.settings.syncOperations).toBe(false);
});

test('An aborted storage transaction leaves current videos, image results and history visible',async({page})=>{
 await seed(page);const source=await page.locator('.scene-card video').getAttribute('src');
 await page.evaluate(()=>{const original=IDBCursor.prototype.delete;IDBCursor.prototype.delete=function(){const request=original.call(this);const source=this.source as IDBObjectStore;if(source.name==='results')request.addEventListener('success',()=>source.transaction.abort(),{once:true});return request};});
 await page.getByRole('button',{name:clearName,exact:true}).click();await page.getByRole('button',{name:confirmName,exact:true}).click();await expect(page.getByRole('button',{name:confirmName,exact:true})).toBeEnabled();await expect(page.getByRole('dialog')).toHaveCount(1);expect((await records(page)).filter(row=>row.media.kind==='video')).toHaveLength(3);await expect(page.locator('.scene-card video')).toHaveAttribute('src',source!);await expect(page.getByRole('dialog')).toContainText('Sẽ xoá 3 kết quả video');
});

test('Clear videos is disabled throughout preparation, generation and recovery',async({page})=>{
 await seed(page);let releasePrepare!:()=>void,releaseVideo!:()=>void,releaseRecovery!:()=>void;
 const prepared=new Promise<void>(resolve=>releasePrepare=resolve),rendered=new Promise<void>(resolve=>releaseVideo=resolve),recovered=new Promise<void>(resolve=>releaseRecovery=resolve);
 let starts=0,recoveries=0;
 await page.route('**/api/account/prepare',async route=>{await prepared;await route.fulfill({json:{executionConcurrency:2,accounts}})});
 await page.route('**/api/video',async route=>{starts++;await rendered;await route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 await page.route('**/api/media/recover',async route=>{recoveries++;await recovered;await route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 try{
  await page.getByTestId('scene-2').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await expect(page.getByRole('button',{name:clearName,exact:true})).toBeDisabled();expect(starts).toBe(0);releasePrepare();await expect.poll(()=>starts).toBe(1);await expect(page.getByRole('button',{name:clearName,exact:true})).toBeDisabled();releaseVideo();await expect(page.getByRole('button',{name:clearName,exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();await expect.poll(()=>recoveries).toBe(0);
  // Explicit scene recovery remains available even when that scene has a result.
  await page.getByLabel('Kịch bản cảnh 2',{exact:true}).fill('A missing stored scene requiring recovery');await page.getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();await expect.poll(()=>recoveries).toBe(1);await expect(page.getByRole('button',{name:clearName,exact:true})).toBeDisabled();releaseRecovery();await expect(page.getByRole('button',{name:clearName,exact:true})).toBeEnabled();
 }finally{releasePrepare();releaseVideo();releaseRecovery()}
});

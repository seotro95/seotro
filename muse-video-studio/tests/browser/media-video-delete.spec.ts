import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';

const source=await readFile(new URL('../../src/media-library.ts',import.meta.url),'utf8');
const moduleSource=stripTypeScriptTypes(source,{mode:'strip'});
const media=(id:string,kind:'image'|'video',batchId:string,sceneId:number)=>({
 id,batchId,sceneId,prompt:'Keep the complete prompt '+id,createdAt:'2026-11-21T00:00:00.000Z',persisted:true,
 media:{kind,base64:'AQID',mimeType:kind==='image'?'image/png':'video/mp4',url:'blob:temporary-'+id,demo:false,outputName:'Tên gốc '+id},
 settings:{output:kind},referenceId:'preserved-reference-'+id,
});
const entries=[media('image-one','image','batch-a',1),media('video-old','video','batch-a',1),media('video-new','video','batch-a',1),media('video-hidden-other-batch','video','batch-b',300),media('image-two','image','batch-c',77)];

async function setup(page:any){
 await page.route('**/storage-delete-fixture',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><title>Isolated media storage test</title>'}));
 await page.route('**/media-library-under-test.mjs',route=>route.fulfill({contentType:'text/javascript',body:moduleSource}));
 await page.goto('/storage-delete-fixture');
 await page.evaluate(async values=>{
  const {saveMedia}=await import('/media-library-under-test.mjs');
  for(const entry of values)await saveMedia(entry);
  await new Promise<void>((resolve,reject)=>{const open=indexedDB.open('muse-studio-script-queue-v1',1);open.onupgradeneeded=()=>open.result.createObjectStore('queue');open.onsuccess=()=>{const tx=open.result.transaction('queue','readwrite');tx.objectStore('queue').put({kind:'entry',id:'completed-script',prompt:'Keep every word',outputName:'Tên video',state:'done',savedId:'video-hidden-other-batch',selected:true},'entry:completed-script');tx.oncomplete=()=>{open.result.close();resolve()};tx.onabort=()=>reject(tx.error)};open.onerror=()=>reject(open.error)});
 },entries);
}
async function records(page:any,name='muse-studio-media-v1',store='results'){
 return page.evaluate(({name,store})=>new Promise<any[]>((resolve,reject)=>{const open=indexedDB.open(name,1);open.onsuccess=()=>{const request=open.result.transaction(store,'readonly').objectStore(store).getAll();request.onsuccess=()=>{open.result.close();resolve(request.result)};request.onerror=()=>reject(request.error)};open.onerror=()=>reject(open.error)}),{name,store});
}

test('Delete all stored video versions across hidden scenes and batches only after commit; images and queue history survive',async({page})=>{
 await setup(page);
 const before=await records(page),queueBefore=await records(page,'muse-studio-script-queue-v1','queue');
 const result=await page.evaluate(async()=>{
  const {deleteVideoMedia}=await import('/media-library-under-test.mjs');
  const transaction=IDBDatabase.prototype.transaction,events:string[]=[];
  IDBDatabase.prototype.transaction=function(...args:any[]){const tx=transaction.apply(this,args as any);if(this.name==='muse-studio-media-v1'&&args[1]==='readwrite')tx.addEventListener('complete',()=>events.push('commit'));return tx};
  try{const ids=await deleteVideoMedia();events.push('resolved');return {ids,events}}finally{IDBDatabase.prototype.transaction=transaction}
 });
 expect(result.ids.sort()).toEqual(['video-old','video-new','video-hidden-other-batch'].sort());
 expect(result.events).toEqual(['commit','resolved']);
 expect(await records(page)).toEqual(before.filter(row=>row.media.kind==='image'));
 expect(await records(page,'muse-studio-script-queue-v1','queue')).toEqual(queueBefore);
 const again=await page.evaluate(async()=>(await import('/media-library-under-test.mjs')).deleteVideoMedia());
 expect(again).toEqual([]);expect(await records(page)).toEqual(before.filter(row=>row.media.kind==='image'));
});

test('Abort after a real video delete request succeeds rolls the entire purge back and rejects after abort',async({page})=>{
 await setup(page);const before=await records(page);
 const result=await page.evaluate(async()=>{
  const {deleteVideoMedia}=await import('/media-library-under-test.mjs');
  const originalDelete=IDBCursor.prototype.delete,transaction=IDBDatabase.prototype.transaction,events:string[]=[];let deletedBeforeAbort=false;
  IDBDatabase.prototype.transaction=function(...args:any[]){const tx=transaction.apply(this,args as any);if(this.name==='muse-studio-media-v1'&&args[1]==='readwrite')tx.addEventListener('abort',()=>events.push('abort'));return tx};
  IDBCursor.prototype.delete=function(){const request=originalDelete.call(this),store=this.source as IDBObjectStore;if(store.name==='results')request.addEventListener('success',()=>{deletedBeforeAbort=true;store.transaction.abort()},{once:true});return request};
  try{await deleteVideoMedia();return {rejected:false,deletedBeforeAbort,events}}catch(error){events.push('rejected');return {rejected:true,deletedBeforeAbort,events,message:String(error)}}finally{IDBCursor.prototype.delete=originalDelete;IDBDatabase.prototype.transaction=transaction}
 });
 expect(result.deletedBeforeAbort).toBe(true);expect(result.rejected).toBe(true);expect(result.events).toEqual(['abort','rejected']);
 expect(await records(page)).toEqual(before);
});

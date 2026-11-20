import{test}from'node:test';import assert from'node:assert/strict';import{prepareAccounts}from'../src/account-prepare.ts';
test('account preparation overlaps three accounts and waits for every started account before returning an error',async()=>{
 const started:number[]=[];const releases=new Map<number,()=>void>();let active=0,peak=0;
 const prepared=prepareAccounts(Array.from({length:10},(_,i)=>i+1),async id=>{started.push(id);active++;peak=Math.max(peak,active);await new Promise<void>(r=>releases.set(id,r));active--;return id*6});
 assert.deepEqual(started,[1,2,3]);assert.equal(active,3);
 while(releases.size){const wave=[...releases];releases.clear();for(const[,release]of wave)release();await new Promise(r=>setImmediate(r))}
 assert.deepEqual(await prepared,Array.from({length:10},(_,i)=>(i+1)*6));assert.equal(peak,3);
 let finish!:()=>void;let finished=false;const calls:number[]=[];
 const failed=prepareAccounts([1,2,3,4,5],async id=>{calls.push(id);if(id===1)throw Error('Preparation failed');await new Promise<void>(r=>finish=r);finished=true},2);const rejection=assert.rejects(failed,/Preparation failed/);await new Promise(r=>setImmediate(r));assert.deepEqual(calls,[1,2]);assert.equal(finished,false);finish();await rejection;assert.equal(finished,true);
});

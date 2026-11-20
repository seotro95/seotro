import{test}from'node:test';import assert from'node:assert/strict';import{MediaQueue}from'../media-queue.mjs';
test('sixty completed media results use six transfer/decoder slots; queued cancellation never starts a transfer',async()=>{
 const pool=new MediaQueue(6),started=[],releases=new Map();const controls=Array.from({length:60},()=>new AbortController());
 const jobs=controls.map((control,id)=>pool.run(async()=>{started.push(id);await new Promise(r=>releases.set(id,r));return id},control.signal));const all=Promise.allSettled(jobs);await new Promise(r=>setImmediate(r));assert.equal(started.length,6);assert.deepEqual(pool.snapshot(),{active:6,queued:54,limit:6});controls[59].abort(Error('Cancelled before download'));
 while(releases.size){const wave=[...releases];releases.clear();for(const[,release]of wave)release();await new Promise(r=>setImmediate(r));assert.ok(pool.active<=6)}
 const rows=await all;assert.equal(rows.filter(row=>row.status==='fulfilled').length,59);assert.equal(rows[59].status,'rejected');assert.ok(!started.includes(59));assert.deepEqual(pool.snapshot(),{active:0,queued:0,limit:6});
});

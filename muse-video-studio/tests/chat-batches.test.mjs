import{test}from'node:test';import assert from'node:assert/strict';import{ChatBatches}from'../chat-batches.mjs';
test('cancelling a collected scene does not poison later scenes in the same cohort',async()=>{
 const calls=[];const batches=new ChatBatches(async rows=>{calls.push(rows.map(row=>row.sceneId));rows.forEach(row=>row.resolve(row.sceneId))},{limit:()=>2,collectMs:5});
 const first=new AbortController();const options={prompt:'A river',output:'video',submissionGroup:{id:'same-cohort',size:2},onStage:()=>{}};const removed=assert.rejects(batches.add({...options,sceneId:1,signal:first.signal}));first.abort();await removed;const rows=await Promise.all([2,3].map(sceneId=>batches.add({...options,sceneId,signal:new AbortController().signal})));assert.deepEqual(rows,[2,3]);assert.deepEqual(calls,[[2,3]]);batches.cancelAll();assert.equal(batches.groups.size,0);
});

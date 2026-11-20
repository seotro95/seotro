import{test}from'node:test';import assert from'node:assert/strict';import{withinDeadline}from'../src/request-deadline.ts';import{RENDER_TIMEOUT_MS,LOCAL_RENDER_TIMEOUT_MS,UI_WAIT_LIMIT_MS}from'../limits.mjs';
test('a stalled transport ends at the deadline even if cancellation is ignored; it is never replayed',async()=>{
 assert.ok(RENDER_TIMEOUT_MS<LOCAL_RENDER_TIMEOUT_MS&&LOCAL_RENDER_TIMEOUT_MS<UI_WAIT_LIMIT_MS);assert.equal(UI_WAIT_LIMIT_MS,200000);let calls=0,cancelled=0;let late!:()=>void;
 await assert.rejects(withinDeadline(signal=>{calls++;signal.addEventListener('abort',()=>cancelled++);return new Promise<void>(resolve=>late=resolve)},undefined,30),/MUSE_WAIT_LIMIT/);assert.equal(calls,1);assert.equal(cancelled,1);late();await new Promise(r=>setImmediate(r));assert.equal(calls,1);
 const user=new AbortController();const waiting=withinDeadline(()=>new Promise<void>(()=>{}),user.signal,1000);user.abort(new DOMException('User stopped','AbortError'));await assert.rejects(waiting,error=>(error as Error).name==='AbortError');
});

import{test}from'node:test';import assert from'node:assert/strict';import{SubmitGroups}from'../submit-groups.mjs';
test('a submit wave sends nothing until every editor is ready, then releases every member together',async()=>{
 const groups=new SubmitGroups();const spec={id:crypto.randomUUID(),size:6};let count=0;const tokens=Array.from({length:6},(_,i)=>groups.register(spec,'batch',i+1,new AbortController().signal));const pending=tokens.slice(0,5).map(t=>t.ready().then(()=>count++));await new Promise(r=>setImmediate(r));assert.equal(count,0);pending.push(tokens[5].ready().then(()=>count++));await Promise.all(pending);assert.equal(count,6);groups.clear();
});
test('cancel before Enter removes only that member; preparation errors reject all remaining unsent members',async()=>{
 const groups=new SubmitGroups();let spec={id:crypto.randomUUID(),size:3};const c=new AbortController();const a=groups.register(spec,'batch',1,c.signal),b=groups.register(spec,'batch',2,new AbortController().signal),d=groups.register(spec,'batch',3,new AbortController().signal);const rejected=assert.rejects(a.ready());c.abort();await Promise.all([rejected,b.ready(),d.ready()]);
 spec={id:crypto.randomUUID(),size:2};const x=groups.register(spec,'batch',1,new AbortController().signal),y=groups.register(spec,'batch',2,new AbortController().signal);x.fail(new Error('Editor failed'));await assert.rejects(x.ready(),/Editor failed/);await assert.rejects(y.ready(),/Editor failed/);groups.clear();
});

import{test}from'node:test';import assert from'node:assert/strict';import{DEFAULT_SETTINGS,lanesForAccount,accountForScene,restoreWorkspace,createScenes}from'../src/core.ts';
test('fresh defaults and standard mode stay one lane per account even with stale larger limits or overrides',()=>{
 assert.equal(DEFAULT_SETTINGS.requestedConcurrency,1);
 const settings={...DEFAULT_SETTINGS,accountMode:'multiple' as const,accountPlanMode:'standard' as const,selectedAccountIds:Array.from({length:10},(_,i)=>i+1),requestedConcurrency:6,accountLaneOverrides:{'1':10}};
 assert.equal(settings.selectedAccountIds.reduce((sum,id)=>sum+lanesForAccount(settings,id),0),10);for(let i=1;i<=10;i++)assert.equal(accountForScene({id:i},settings),i);
 const expanded={...settings,accountPlanMode:'expanded' as const,accountLaneOverrides:{}};assert.equal(expanded.selectedAccountIds.reduce((sum,id)=>sum+lanesForAccount(expanded,id),0),60);assert.equal(accountForScene({id:60},expanded),10);
});
test('legacy expanded workspaces migrate to the expanded UI without losing prompts; legacy one-lane groups stay standard',()=>{
 const scenes=createScenes(60).map((scene,i)=>({...scene,prompt:'Retain '+(i+1)}));
 const expanded=restoreWorkspace(JSON.stringify({version:1,scenes,settings:{accountMode:'multiple',requestedConcurrency:6,slotCount:60,selectedAccountIds:[1,2,3,4,5,6,7,8,9,10]}}));assert.equal(expanded.settings.accountPlanMode,'expanded');assert.equal(expanded.scenes.length,60);assert.equal(expanded.scenes[59].prompt,'Retain 60');
 const standard=restoreWorkspace(JSON.stringify({version:1,scenes,settings:{accountMode:'multiple',requestedConcurrency:1,slotCount:10}}));assert.equal(standard.settings.accountPlanMode,'standard');assert.equal(lanesForAccount(standard.settings,1),1);assert.equal(standard.scenes[59].prompt,'Retain 60');
});

const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {parseTargetDuration,readTargetDuration,durationInputValue}=require('../static/duration.js');
test('clock and decimal-minute input give the same seconds',()=>{
  for(const input of ['10:00','00:10:00','10','10,0'])assert.equal(parseTargetDuration(input),600);
  assert.equal(parseTargetDuration('1.5'),90);
  assert.equal(parseTargetDuration('00:02.345'),2.345);
  assert.equal(parseTargetDuration('03:00:00'),10800);
  assert.equal(parseTargetDuration(''),null);
  assert.equal(durationInputValue(2.345),'00:02.345');
  assert.equal(durationInputValue(600),'10:00');
});
test('invalid clocks and nonpositive or over-limit durations fail',()=>{
  for(const input of ['0','-1','181','10:60','00:60:00','00:00','Infinity','nan','abc','0.0000001'])
    assert.throws(()=>parseTargetDuration(input),Error,input);
});
test('SRT ignores TXT duration and blank TXT keeps natural mode',()=>{
  global.document={getElementById:()=>({value:'10:00'})};
  assert.equal(readTargetDuration('target','txt'),600);
  assert.equal(readTargetDuration('target','srt'),null);
  global.document={getElementById:()=>({value:''})};
  assert.equal(readTargetDuration('target','txt'),null);
  delete global.document;
});
test('every speech entry point submits a target or strict subtitle timing',()=>{
  const base=path.join(__dirname,'..','static');
  const app=fs.readFileSync(path.join(base,'app.js'),'utf8');
  const workspace=fs.readFileSync(path.join(base,'workspace.js'),'utf8');
  const html=fs.readFileSync(path.join(base,'index.html'),'utf8');
  for(const id of ['target-duration','dub-target-duration','workspace-free-target-duration'])
    assert.ok(html.includes('id="'+id+'"'),id);
  assert.ok(app.includes("target_seconds:readTargetDuration('target-duration'"));
  assert.ok(app.includes("target_seconds:readTargetDuration('dub-target-duration'"));
  assert.ok(workspace.includes("target_seconds:readTargetDuration('workspace-free-target-duration'"));
  assert.ok(workspace.includes("input_format:$('workspace-free-input-format').value"));
  assert.ok(workspace.includes("durationInputValue(cues[cues.length-1].end)"));
});

import{test}from'node:test';
import assert from'node:assert/strict';
import{chromium}from'playwright-core';
import{inspectBatchDOM}from'../muse-batch-dom.mjs';

const rows=Array.from({length:5},(_,i)=>({fileToken:'MUSE_'+String(i+1).padStart(32,'0'),label:`CLIP_${String(i+1).padStart(3,'0')}_c7496c88`}));
const message=(body,role='assistant')=>`<div data-message-item data-message-role="${role}">${body}</div>`;
const video=id=>message(`<div class="native-video-card"><video src="https://example.invalid/render-${id}.mp4" preload="none"></video></div>`);
const caption=i=>message(`<p><strong>${rows[i].label}</strong> — ${rows[i].fileToken}</p><p>Done — the landscape of task ${i+1}.</p><p>1280 × 720 (720p), 10 seconds, 16:9, 24 fps.</p><p>It came back with audio, so I stripped it and verified the delivered file has video only.</p>`);
const start=message('[studio-batch-c7496c88-owned]', 'user');

test('five native media cards followed by separate CLIP completion messages map by their local captions, in completion order rather than scene order',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{
  const page=await browser.newPage();await page.setContent(start+message('I’ll send each one as it finishes.')+[4,3,2,1,0].map(i=>video(i+1)+caption(i)).join(''));
  const state=await page.evaluate(inspectBatchDOM,{marker:'studio-batch-c7496c88-owned',rows,acknowledged:true,output:'video'});
  assert.equal(state.replyCount,11);assert.equal(state.media.length,5);assert.equal(state.unclaimed,0);
  for(let i=0;i<5;i++)assert.equal(state.matches[rows[i].fileToken]?.src,`https://example.invalid/render-${i+1}.mp4`);
  await page.evaluate(html=>document.body.insertAdjacentHTML('beforeend',html),video('foreign')+message('<h3>CLIP_001_deadbeef</h3><p>Done — a result from another batch.</p>'));
  const late=await page.evaluate(inspectBatchDOM,{marker:'studio-batch-c7496c88-owned',rows,acknowledged:true,output:'video'});assert.equal(late.media.length,5,'A separate caption from another batch excludes its unlabelled native card as well');
 }finally{await browser.close()}
});

test('separate captions do not assign a list of unlabelled files by task order, cross user turns, or consume historical media',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{
  const page=await browser.newPage();
  await page.setContent(start+[0,1,2,3,4].map(i=>video(i+1)).join('')+[4,3,2,1,0].map(caption).join(''));
  let state=await page.evaluate(inspectBatchDOM,{marker:'studio-batch-c7496c88-owned',rows,acknowledged:true,output:'video'});
  assert.equal(Object.keys(state.matches).length,0,'A contiguous block of several unlabelled cards is ambiguous, even if five captions follow');
  await page.setContent(start+video(1)+message('Another user request','user')+caption(0));
  state=await page.evaluate(inspectBatchDOM,{marker:'studio-batch-c7496c88-owned',rows,acknowledged:true,output:'video'});assert.equal(Object.keys(state.matches).length,0);
  await page.setContent(start+video(1)+caption(0));
  state=await page.evaluate(inspectBatchDOM,{marker:'studio-batch-c7496c88-owned',rows,baseline:['https://example.invalid/render-1.mp4'],acknowledged:true,output:'video'});assert.equal(Object.keys(state.matches).length,0);
 }finally{await browser.close()}
});

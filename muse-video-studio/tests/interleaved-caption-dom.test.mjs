import{test}from'node:test';import assert from'node:assert/strict';import{chromium}from'playwright-core';import{inspectBatchDOM}from'../muse-batch-dom.mjs';
const rows=Array.from({length:5},(_,i)=>({fileToken:'MUSE_'+String(i+1).padStart(32,'0'),label:`CLIP_${String(i+1).padStart(3,'0')}_670689b3`}));
const message=(body,role='assistant')=>`<div data-message-item data-message-role="${role}">${body}</div>`;
const card=i=>message(`<video src="https://example.invalid/result-${i}.mp4" preload="none"></video>`);
const caption=i=>message(`<p><strong>${rows[i-1].label}</strong> — ${rows[i-1].fileToken}</p><p>Done — original landscape ${i}.</p><p>1280 × 720 (720p), 10 seconds, 16:9, 24 fps. It’s silent, as requested.</p>`);
const start=message('[studio-batch-670689b3-owned]','user');
const options={marker:'studio-batch-670689b3-owned',rows,acknowledged:true,output:'video'};
test('five media and thirteen replies: progress between card and caption must not strand scenes two and three',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{
  const page=await browser.newPage();await page.setContent(start+message('I’ll send each one as it finishes.')+card(3)+message('Two still running — I’ll send each one as it finishes.')+caption(3)+card(4)+caption(4)+card(5)+caption(5)+card(1)+caption(1)+card(2)+message('One still running — CLIP_002, the shallow depression — I’ll send it as soon as it finishes.')+caption(2));
  const state=await page.evaluate(inspectBatchDOM,options);assert.equal(state.replyCount,13);assert.equal(state.media.length,5);assert.equal(state.captionLinked,5);assert.equal(state.unclaimed,0);for(let i=1;i<=5;i++)assert.equal(state.matches[rows[i-1].fileToken]?.src,`https://example.invalid/result-${i}.mp4`);
 }finally{await browser.close()}
});

test('pending labels in a completion message do not replace its explicit completed section; media blocks and user boundaries stay ambiguous',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{
  const page=await browser.newPage();
  await page.setContent(start+card(3)+message(`<h3>${rows[2].label} — ${rows[2].fileToken}</h3><p>Done — the grass-covered bank.</p><p>Still running — ${rows[1].label} — ${rows[1].fileToken}. I’ll send it when ready.</p>`));
  let state=await page.evaluate(inspectBatchDOM,options);assert.equal(state.matches[rows[2].fileToken]?.src,'https://example.invalid/result-3.mp4');assert.equal(state.matches[rows[1].fileToken],undefined);
  await page.setContent(start+card(2)+message('One still running.')+card(3)+message('I’ll send each one.')+caption(2)+caption(3));state=await page.evaluate(inspectBatchDOM,options);assert.equal(Object.keys(state.matches).length,0,'Multiple unlabelled candidates cannot be zipped to the next labels');
  await page.setContent(start+card(2)+message('Another user turn','user')+message('One still running.')+caption(2));state=await page.evaluate(inspectBatchDOM,options);assert.equal(Object.keys(state.matches).length,0);
 }finally{await browser.close()}
});

import{test}from'node:test';import assert from'node:assert/strict';import{chromium}from'playwright-core';import{inspectBatchDOM}from'../muse-batch-dom.mjs';
const rows=Array.from({length:5},(_,i)=>({fileToken:'MUSE_'+String(i+1).padStart(32,'0'),label:`CLIP_${String(i+1).padStart(3,'0')}_1c6836bc`}));
const message=(body,role='assistant')=>`<div data-message-item data-message-role="${role}">${body}</div>`;
const media=i=>message(`<video src="https://example.invalid/generated-${i}.mp4" preload="none"></video>`);
const heading=(i,bullet=false)=>message(`<p>${bullet?'- ':''}${rows[i-1].label}:</p>`);
const start=message('[studio-batch-1c6836bc-owned]','user'),options={marker:'studio-batch-1c6836bc-owned',rows,acknowledged:true,output:'video'};
test('reported layout: five label-only headings precede native media; no Done keyword or UUID filename is required',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{const page=await browser.newPage();await page.setContent(start+message("Assistant message: Two more clips are ready. I’ll share each as it finishes.")+heading(2,true)+media(2)+heading(3)+media(3)+message("Three more clips are ready. The video tool doesn't expose exact model selection.")+heading(1)+media(1)+heading(4)+media(4)+heading(5)+media(5)+message(''));
  const state=await page.evaluate(inspectBatchDOM,options);assert.equal(state.media.length,5);assert.equal(state.unclaimed,0);assert.equal(state.captionLinked,5);for(let i=1;i<=5;i++)assert.equal(state.matches[rows[i-1].fileToken]?.src,`https://example.invalid/generated-${i}.mp4`);
 }finally{await browser.close()}
});
test('bare labels after media also resolve uniquely; ambiguous grouped files, pending labels and user boundaries never assign by scene order',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{const page=await browser.newPage();await page.setContent(start+[4,2,5,1,3].map(i=>media(i)+heading(i)).join(''));let state=await page.evaluate(inspectBatchDOM,options);for(let i=1;i<=5;i++)assert.equal(state.matches[rows[i-1].fileToken]?.src,`https://example.invalid/generated-${i}.mp4`);
  await page.setContent(start+media(2)+media(3)+heading(2)+heading(3));state=await page.evaluate(inspectBatchDOM,options);assert.equal(Object.keys(state.matches).length,0);
  await page.setContent(start+heading(2)+message('A new request','user')+media(2));state=await page.evaluate(inspectBatchDOM,options);assert.equal(Object.keys(state.matches).length,0);
  await page.setContent(start+message(`<p>${rows[1].label}: still generating, not ready yet.</p>`)+media(2));state=await page.evaluate(inspectBatchDOM,options);assert.equal(Object.keys(state.matches).length,0);
 }finally{await browser.close()}
});
test('a validated downloaded file cannot be reassigned when an older label scrolls out of the native DOM',{timeout:15000},async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{const page=await browser.newPage();await page.setContent(start+media(1)+heading(2));const state=await page.evaluate(inspectBatchDOM,{...options,bindings:{[rows[0].fileToken]:'https://example.invalid/generated-1.mp4'}});assert.equal(state.matches[rows[0].fileToken]?.src,'https://example.invalid/generated-1.mp4');assert.equal(state.matches[rows[1].fileToken],undefined);
 }finally{await browser.close()}
});

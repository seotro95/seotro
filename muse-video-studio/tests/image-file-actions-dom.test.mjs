import{test}from'node:test';
import assert from'node:assert/strict';
import{chromium}from'playwright-core';
import{inspectBatchDOM}from'../muse-batch-dom.mjs';

const rows=[1,2].map(i=>({fileToken:'MUSE_'+String(i).padStart(32,'0'),label:`CLIP_${String(i).padStart(3,'0')}_abcd1234`}));
const message=(body,role='assistant')=>`<div data-message-item data-message-role="${role}">${body}</div>`;
const marker='studio-image-file-actions';
const start=message(`[${marker}]`,'user');
const caption=i=>message(`<h3>${rows[i-1].label}</h3><p>Ready — the generated image.</p>`);
const options={marker,rows,acknowledged:true,output:'image'};
async function withPage(run){const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||chromium.executablePath(),headless:true});try{const page=await browser.newPage();await page.route('https://example.invalid/**',route=>route.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));await page.goto('https://example.invalid/');await run(page)}finally{await browser.close()}}

test('extensionless image links in separate native cards use their own neighbouring CLIP caption, never request order',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message('<a href="https://example.invalid/files/second">Open image</a>')+caption(2)+message('<a href="https://example.invalid/files/first" aria-label="View original image">Result</a>')+caption(1));
 const state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,2);assert.equal(state.unclaimed,0);assert.equal(state.captionLinked,2);
 assert.equal(state.matches[rows[0].fileToken]?.src,'https://example.invalid/files/first');
 assert.equal(state.matches[rows[1].fileToken]?.src,'https://example.invalid/files/second');
 assert.ok(state.matches[rows[0].fileToken]?.nativeControl);
}));

test('known native image-file actions and image-specific link labels are retained, unrelated extensionless citations are ignored',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message(`<h3>${rows[0].label}</h3><a href="sandbox:/generated/opaque-file">Result</a><a href="https://example.invalid/research/source">View source</a>`)+message(`<h3>${rows[1].label}</h3><a href="https://example.invalid/files/opaque" title="Mở hình ảnh">Result</a><a href="https://example.invalid/research/portrait">Read portrait reference</a>`));
 const state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,2);
 assert.equal(state.matches[rows[0].fileToken]?.src,'sandbox:/generated/opaque-file');
 assert.equal(state.matches[rows[1].fileToken]?.src,'https://example.invalid/files/opaque');
 assert.equal(state.matches[rows[0].fileToken]?.nativeDownload,true);
}));

test('separate image download-button cards map by forced caption assignment and retain the exact control identity',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message('<button id="second" aria-label="Download image">↓</button>')+caption(2)+message('<button id="first">Save image</button>')+caption(1));
 const state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,2);assert.equal(state.unclaimed,0);assert.equal(state.captionLinked,2);
 const ids=await page.evaluate(()=>Object.fromEntries(['first','second'].map(id=>[id,document.getElementById(id).dataset.museStudioFileId])));
 assert.equal(state.matches[rows[0].fileToken]?.nativeId,ids.first);
 assert.equal(state.matches[rows[1].fileToken]?.nativeId,ids.second);
 assert.equal(state.matches[rows[0].fileToken]?.nativeButton,true);
 assert.equal(state.matches[rows[1].fileToken]?.nativeButton,true);
}));

test('unlabelled image-action groups, foreign controls and user boundaries cannot produce a guessed match',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message('<button>Download image</button>')+message('<button>Download image</button>')+caption(2)+caption(1));
 let state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,2);assert.equal(Object.keys(state.matches).length,0);
 await page.setContent(start+caption(1)+message('<button aria-label="Download image CLIP_001_deadbeef">↓</button>')+message('<button>Download image</button>'));
 state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(Object.keys(state.matches).length,0,'A foreign native control is a label boundary, not a bridge to another image');
 await page.setContent(start+message('<button>Download image</button>')+message('Another request','user')+caption(1));
 state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(Object.keys(state.matches).length,0);
 await page.setContent(start+message('<a href="https://example.invalid/files/opaque">Result</a>')+caption(1));
 state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,0,'A generic extensionless citation gains no media semantics from proximity alone');
}));

test('image action labels do not admit executable links or turn unbound buttons into matched results',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message(`<h3>${rows[0].label}</h3><a href="javascript:window.unexpectedMediaAction=1">Open image</a>`));
 let state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,0,'Executable URLs are never media candidates');
 assert.equal(Object.keys(state.matches).length,0);
 assert.equal(state.unsupported.length,1);assert.equal(state.unsupported[0].scheme,'javascript:');
 assert.equal(state.unsupported[0].owner,rows[0].fileToken);
 assert.equal(await page.evaluate(()=>window.unexpectedMediaAction),undefined);
 await page.setContent(start+message('<button>Download image</button>'));
 state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,1,'A native button is only a candidate until its caption is known');
 assert.equal(Object.keys(state.matches).length,0,'No file action may run without a forced owner');
}));

test('image file-action discovery leaves video collection and matching unchanged',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message('<a href="https://example.invalid/files/opaque">Open image</a>')+message('<button>Download image</button>')+caption(1)+message(`<h3>${rows[1].label}</h3><video src="https://example.invalid/second.mp4"></video>`));
 const state=await page.evaluate(inspectBatchDOM,{...options,output:'video'});
 assert.equal(state.media.length,1);assert.equal(state.matches[rows[0].fileToken],undefined);
 assert.equal(state.matches[rows[1].fileToken]?.src,'https://example.invalid/second.mp4');
}));


test('an image filename in visible link text identifies an opaque file action under its own CLIP caption',{timeout:15000},()=>withPage(async page=>{
 await page.setContent(start+message('<a href="muse-file:/opaque-portrait-2">portrait-two.png</a>')+caption(2)+message('<a href="https://example.invalid/files/opaque-1">portrait-one.webp</a>')+caption(1));
 const state=await page.evaluate(inspectBatchDOM,options);
 assert.equal(state.media.length,2);assert.equal(state.unclaimed,0);
 assert.equal(state.matches[rows[0].fileToken]?.src,'https://example.invalid/files/opaque-1');
 assert.equal(state.matches[rows[1].fileToken]?.src,'muse-file:/opaque-portrait-2');
 assert.equal(state.matches[rows[1].fileToken]?.nativeDownload,true);
}));

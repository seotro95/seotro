import {test} from 'node:test';import assert from 'node:assert/strict';
import {parseScriptEntries} from '../src/script-import.ts';
import {accountLayout,accountForScene,DEFAULT_SETTINGS,restoreWorkspace,createScenes} from '../src/core.ts';
import {outputStem,uniqueOutputFilename,validOutputFilename} from '../output-names.mjs';
test('a dossier imports only render prompts named by the large heading and preserves multiline content',()=>{
 const file=`CHARACTER NOTES\n1. Reference policy is metadata.\n===\n[1] AIKO TANAKA — JDR001\nMa: JDR001-CHR01\nA. Fixed appearance:\n- Brown hair.\n1. PROMPT CHAN DUNG — AIKO TANAKA (front view):\nPortrait prompt, shoulders-up.\nKeep this second line.\n2. PROMPT TOAN THAN — AIKO TANAKA:\nFull-body prompt, head to toe.\n3. MO TA GIONG NOI:\nSoft female voice.\n4. TEN THONG NHAT: Aiko Tanaka\n===\n[2] KEIKO TANAKA — JDR003\n1. PROMPT CHAN DUNG — KEIKO:\nPortrait two.\n2. PROMPT TOAN THAN — KEIKO:\nFull body two.\n3. MO TA GIONG NOI:\nOlder female.`;
 const rows=parseScriptEntries(file);assert.equal(rows.length,4);assert.deepEqual(rows[0],{outputName:'AIKO TANAKA — JDR001 — CHAN DUNG',prompt:'Portrait prompt, shoulders-up.\nKeep this second line.'});
 assert.equal(rows[1].outputName,'AIKO TANAKA — JDR001 — TOAN THAN');assert.equal(rows[3].prompt,'Full body two.');assert.ok(rows.every(row=>!row.prompt.includes('MO TA')&&!row.prompt.includes('Soft female')));
});
test('TXT and SRT names are separate from prompts; unnamed subtitles retain all content',()=>{
 assert.deepEqual(parseScriptEntries('1. CẢNH MỞ ĐẦU\nA wide temple view.\n\n2. CẢNH KẾT\nA sunset view.'),[{outputName:'CẢNH MỞ ĐẦU',prompt:'A wide temple view.'},{outputName:'CẢNH KẾT',prompt:'A sunset view.'}]);
 assert.deepEqual(parseScriptEntries('1\n00:00:00,000 --> 00:00:10,000\nTên video: Núi đá.mp4\nPrompt: Slow camera move.\n\n2\n00:00:10,000 --> 00:00:20,000\nAn unnamed scene.'),[{outputName:'Núi đá',prompt:'Slow camera move.'},{prompt:'An unnamed scene.'}]);
 assert.deepEqual(parseScriptEntries('Ten anh: Canh 01.png\nPrompt: Whole prompt.'),[{outputName:'Canh 01',prompt:'Whole prompt.'}]);
 assert.deepEqual(parseScriptEntries('Name: test.png | Prompt: Whole prompt.'),[{outputName:'test',prompt:'Whole prompt.'}]);
});
test('Unicode names are Windows-safe and case-insensitive collisions receive deterministic suffixes',()=>{
 assert.equal(outputStem('Cảnh mở đầu.mp4'),'Cảnh mở đầu');assert.equal(outputStem('CON.mp4'),'_CON');
 const used=new Set<string>();assert.equal(uniqueOutputFilename('Aiko','png',used),'Aiko.png');assert.equal(uniqueOutputFilename('AIKO','png',used),'AIKO (2).png');
 for(const name of ['../x.png','x/y.png','x\\y.png','CON.png','NUL.mp4','a:stream.png','a .png'])assert.equal(validOutputFilename(name,name.endsWith('png')?'image':'video'),false,name);
 assert.equal(validOutputFilename('AIKO TANAKA — CHAN DUNG.png','image'),true);
});
test('10×6 assigns sixty slots, 40×10 assigns four hundred, and hidden names survive restore',()=>{
 const layout=accountLayout(Array.from({length:10},(_,i)=>i+1),6);assert.equal(layout.length,60);assert.deepEqual(layout.slice(54).map(x=>x.accountId),[10,10,10,10,10,10]);assert.equal(accountLayout(Array.from({length:40},(_,i)=>i+1),10).length,400);
 assert.deepEqual(accountLayout([3,27],2),[{id:1,accountId:3},{id:2,accountId:3},{id:3,accountId:27},{id:4,accountId:27}]);assert.equal(accountForScene({id:60},{...DEFAULT_SETTINGS,accountMode:'multiple',requestedConcurrency:6}),10);
 for(const [ids,count] of [[[41],6],[[1],11],[[],1],[[1,1],1]] as [number[],number][])assert.throws(()=>accountLayout(ids,count));
 const scenes=createScenes(400).map(scene=>({...scene,outputName:`File ${scene.id}`}));const saved=restoreWorkspace(JSON.stringify({version:1,scenes,settings:{...DEFAULT_SETTINGS,slotCount:6}}));assert.equal(saved.scenes[399].outputName,'File 400');assert.equal(saved.settings.slotCount,6);
});

test('expanded custom-account layouts do not acquire unrelated legacy accounts after reload',()=>{
 const settings={...DEFAULT_SETTINGS,accountMode:'multiple' as const,selectedAccountIds:[3,27],requestedConcurrency:6,slotCount:40};
 const restored=restoreWorkspace(JSON.stringify({version:1,settings,scenes:createScenes(400)}));
 for(const id of [1,7,13,20,40])assert.equal(accountForScene(restored.scenes[id-1],restored.settings),accountForScene({id},settings));
});

test('individual account lane choices generate exact variable groups and survive restore',()=>{
 const rows=accountLayout([1,2,3],6,{'1':2,'3':10});assert.equal(rows.length,18);assert.equal(rows.filter(r=>r.accountId===1).length,2);assert.equal(rows.filter(r=>r.accountId===2).length,6);assert.equal(rows.filter(r=>r.accountId===3).length,10);
 const restored=restoreWorkspace(JSON.stringify({version:1,scenes:createScenes(40),settings:{...DEFAULT_SETTINGS,accountMode:'multiple',accountLaneOverrides:{'1':2,'2':11,'41':6}}}));assert.deepEqual(restored.settings.accountLaneOverrides,{'1':2});
});


test('all ten compact or spaced bracket headings keep names and prompt order in TXT and SRT',()=>{
 const names=['nam','thái','nga','thang','hoang','thu','thao','tuan','phang','phu'];
 const sections=names.map((name,i)=>`${i%2?' ':''}[${i%3?'':' '}${i+1}${i%3?'':' '}]${i%2?'':' '}${name} \nPrompt line ${i+1}.\nKeep all content ${i+1}.`);
 const expected=names.map((name,i)=>({outputName:name,prompt:`Prompt line ${i+1}.\nKeep all content ${i+1}.`}));
 assert.deepEqual(parseScriptEntries('\uFEFF'+sections.join('\n').replace(/\n/g,'\r\n')),expected);
 const srt=sections.map((section,i)=>`${i+1}\n00:00:${String(i).padStart(2,'0')},000 --> 00:00:${String(i+1).padStart(2,'0')},000\n${section}`).join('\n\n');
 assert.deepEqual(parseScriptEntries(srt),expected.map(entry=>({...entry,prompt:entry.prompt.replaceAll('\n',' ')})));
});

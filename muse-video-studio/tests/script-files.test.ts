import{test}from'node:test';import assert from'node:assert/strict';import{readScriptFiles,parseScriptFiles}from'../src/script-files.ts';
const file=(name:string,text:string)=>({name,size:Buffer.byteLength(text),text:async()=>text});
test('mixed TXT and SRT files retain every independent cue, exact names and multiline TXT prompts in natural filename order',async()=>{
 const files=await readScriptFiles([file('prompt-10.txt','[1] hoang\nA final wide shot.\nKeep this second line.'),file('prompt-2.srt','1\n00:00:00,000 --> 00:00:10,000\nTên video: thái\nA shallow depression.\n\n2\n00:00:10,000 --> 00:00:20,000\nA prompt with no name.'),file('prompt-1.txt','[1] nam\nA rainforest edge.\n\n[2] nga\nA grass-covered bank.')]);
 assert.deepEqual(files.map(x=>x.name),['prompt-1.txt','prompt-2.srt','prompt-10.txt']);const groups=parseScriptFiles(files),entries=groups.flatMap(x=>x.entries);assert.equal(entries.length,5);assert.deepEqual(entries.map(x=>x.outputName),['nam','nga','thái',undefined,'hoang']);assert.equal(entries[4].prompt,'A final wide shot.\nKeep this second line.');assert.equal(entries[3].prompt,'A prompt with no name.');
});
test('invalid or unreadable files reject the whole selection rather than returning a partial import',async()=>{
 await assert.rejects(readScriptFiles([file('one.txt','One'),file('wrong.csv','Two')]),/Chỉ nhận/);
 await assert.rejects(readScriptFiles([file('one.txt','One'),{name:'two.srt',size:10,text:async()=>{throw Error('Read failed')}}]),/two.srt/);
 await assert.rejects(readScriptFiles([{name:'large.txt',size:17*1024*1024,text:async()=>''}]),/16 MB/);
 const sources=await readScriptFiles([file('one.txt',Array.from({length:401},(_,i)=>'Prompt '+i).join('\n'))]);assert.equal(parseScriptFiles(sources)[0].entries.length,401,'Overflow remains visible to the UI; no prompt is truncated in the file reader');
});

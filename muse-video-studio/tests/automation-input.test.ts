import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseAutomationBatch} from '../src/automation.ts';
import {DEFAULT_SETTINGS} from '../src/core.ts';
test('automation validates complete batches before editing Studio and accepts SRT, explicit account modes and image sources',()=>{
  const data=parseAutomationBatch({script:'1\n00:00:00,000 --> 00:00:04,000\nScene one\n\n2\n00:00:04,000 --> 00:00:08,000\nScene two',output:'image',settings:{accountMode:'multiple',imageResolution:'4k'}},DEFAULT_SETTINGS);
  assert.deepEqual(data.prompts,['Scene one','Scene two']);assert.deepEqual(data.ids,[1,2]);assert.equal(data.settings.accountMode,'multiple');assert.equal(data.settings.imageResolution,'4k');
  for(const invalid of [{prompts:[]},{prompts:Array(11).fill('a')},{prompts:['a','b'],sceneIds:[1,1]},{prompts:['a'],settings:{accountMode:'unknown'}},{prompts:['a'],settings:{mode:'fake'}},{prompts:['a'],settings:{token:'secret'}},{prompts:['a'],output:'video',settings:{videoInput:'image'}}])assert.throws(()=>parseAutomationBatch(invalid,DEFAULT_SETTINGS));
  const video=parseAutomationBatch({prompts:['Animate'],output:'video',settings:{videoInput:'image',model:'Veo 3.1 - Fast'},sourceMediaId:'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},DEFAULT_SETTINGS);assert.equal(video.settings.duration,8);
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {StudioStartup} from '../desktop/studio-startup.mjs';

test('a missing renderer handshake shows recovery; late ready and an explicit retry can recover',async()=>{
  const states=[];
  const startup=new StudioStartup({onChange:state=>states.push(state),timeout:15});
  try{
    startup.loading();
    await new Promise(resolve=>setTimeout(resolve,30));
    assert.equal(startup.snapshot().code,'STUDIO_TIMEOUT');
    startup.ready();assert.equal(startup.snapshot().phase,'ready');
    startup.fail('STUDIO_RENDERER_EXITED');startup.ready();
    assert.equal(startup.snapshot().code,'STUDIO_RENDERER_EXITED');
    startup.loading();startup.ready();
    await new Promise(resolve=>setTimeout(resolve,30));
    assert.equal(startup.snapshot().phase,'ready');
    assert.equal(states.filter(state=>state.code==='STUDIO_TIMEOUT').length,1);
  }finally{startup.dispose()}
});

test('navigation, preload failures and renderer crashes never expose private page details',()=>{
  const contents=new EventEmitter();
  const startup=new StudioStartup({onChange:()=>{}});startup.observe(contents);
  try{
    contents.emit('did-start-navigation',{},'http://127.0.0.1/',false,true);
    contents.emit('did-fail-load',{},-3,'aborted','private-token',true);
    contents.emit('did-fail-load',{},-2,'private-prompt','private-token',false);
    assert.equal(startup.snapshot().phase,'loading');
    contents.emit('did-fail-load',{},-2,'private-prompt','private-token',true);
    assert.equal(startup.snapshot().code,'STUDIO_LOAD_FAILED');
    contents.emit('preload-error',{},'C:/private-account',new Error('secret'));
    assert.equal(startup.snapshot().code,'STUDIO_PRELOAD_FAILED');
    startup.setStage('media-library');
    contents.emit('render-process-gone',{}, {reason:'crashed',exitCode:-1073741819,private:'secret'});
    assert.equal(startup.snapshot().code,'STUDIO_RENDERER_EXITED');
    assert.equal(startup.snapshot().lastExit.exitCodeHex,'0xC0000005');
    assert.doesNotMatch(JSON.stringify(startup.snapshot()),/private|secret|127\.0\.0\.1/);
    contents.emit('destroyed');
    for(const event of ['did-start-navigation','did-fail-load','preload-error','render-process-gone','destroyed'])assert.equal(contents.listenerCount(event),0);
  }finally{startup.dispose()}
});

test('out-of-memory exits retain the failing stage and exact numeric exit code across a recovery attempt',()=>{
  const contents=new EventEmitter();const startup=new StudioStartup({onChange:()=>{}});startup.observe(contents);
  try{
    startup.loading();startup.setStage('media-library');
    contents.emit('render-process-gone',{}, {reason:'oom',exitCode:0xC0000017});
    assert.equal(startup.snapshot().code,'STUDIO_RENDERER_OUT_OF_MEMORY');
    assert.deepEqual(startup.snapshot().lastExit,{reason:'oom',exitCode:0xC0000017,exitCodeHex:'0xC0000017',stage:'media-library'});
    startup.loading();startup.ready();
    assert.equal(startup.snapshot().lastExit.reason,'oom');
    startup.setStage('private-token');assert.notEqual(startup.snapshot().stage,'private-token');
    contents.emit('render-process-gone',{}, {reason:'private-token',exitCode:'secret'});
    assert.deepEqual(startup.snapshot().lastExit,{reason:'unknown',exitCode:null,exitCodeHex:null,stage:'navigation'});
  }finally{startup.dispose()}
});

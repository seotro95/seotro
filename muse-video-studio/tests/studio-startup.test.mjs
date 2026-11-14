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
    contents.emit('render-process-gone',{}, {reason:'crashed',private:'secret'});
    assert.equal(startup.snapshot().code,'STUDIO_RENDERER_EXITED');
    assert.doesNotMatch(JSON.stringify(startup.snapshot()),/private|secret|127\.0\.0\.1/);
    contents.emit('destroyed');
    for(const event of ['did-start-navigation','did-fail-load','preload-error','render-process-gone','destroyed'])assert.equal(contents.listenerCount(event),0);
  }finally{startup.dispose()}
});

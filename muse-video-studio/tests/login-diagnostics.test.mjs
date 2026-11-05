import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loginRecorder } from '../desktop/login-diagnostics.mjs';

test('login report keeps only status and public path labels, never OTP, email, query or cookie values', () => {
  const log = loginRecorder('https://muse.ai/');
  const headers = {};
  Object.defineProperty(headers,'Set-Cookie',{enumerable:true,get(){throw new Error('Cookie value must not be read');}});
  const details = { url:'https://muse.ai/api/auth/verify/246810?email=private@example.invalid&code=135791#private-fragment', method:'POST',resourceType:'xhr',statusCode:400,responseHeaders:headers };
  Object.defineProperty(details,'uploadData',{get(){throw new Error('OTP body must not be read');}});
  log.completed(details);
  const report=log.snapshot({version:'test',loginVisible:true,account:{state:'awaiting_code',authenticated:false}});
  assert.deepEqual(report.events.map(({route,status,setCookie})=>({route,status,setCookie})),[{route:'/api/auth/verify/[ẩn]',status:400,setCookie:true}]);
  const text=JSON.stringify(report);
  for(const secret of ['246810','135791','private@example.invalid','private-fragment','email=','code='])assert.equal(text.includes(secret),false);
});
test('report excludes other services, masks subdomains and bounds its in-memory history',()=>{
  const log=loginRecorder('https://muse.ai/');
  log.completed({url:'https://other.example/auth',method:'POST',statusCode:200,resourceType:'xhr'});
  for(let index=0;index<30;index++)log.completed({url:'https://private-id.muse.ai/api/auth/check?token=private',method:'POST',statusCode:401,resourceType:'xhr'});
  const report=log.snapshot({version:'test'});
  assert.equal(report.events.length,24);
  assert.ok(report.events.every(event=>event.origin==='*.muse.ai'));
  assert.equal(JSON.stringify(report).includes('private'),false);
});
test('network error messages are allowlisted rather than copying arbitrary error text',()=>{
  const log=loginRecorder('https://muse.ai/');
  log.failed({url:'https://muse.ai/auth/verify?token=private',method:'POST',error:'private email and secret',resourceType:'xhr'});
  log.failed({url:'https://muse.ai/auth/verify',method:'POST',error:'net::ERR_CONNECTION_RESET',resourceType:'xhr'});
  assert.deepEqual(log.snapshot({}).events.map(event=>event.error),['NETWORK_ERROR','net::ERR_CONNECTION_RESET']);
});

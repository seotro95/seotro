import {isIP} from 'node:net';
// net.request is injected so every request explicitly uses the account session.
// Do not use global fetch: it can reveal the computer's direct IP instead.
export function requestProxyIP({session,request,credentials,signal,url='https://api.ipify.org?format=json',timeoutMs=12000}) {
  return new Promise((resolve,reject)=>{
    let settled=false;let bytes=0;const chunks=[];let timer;
    const req=request({method:'GET',url,session,redirect:'error',useSessionCookies:false});
    const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);if(error){req.abort();reject(error)}else resolve(value)};
    const abort=()=>finish(new Error('Đã dừng kiểm tra IP proxy.'));
    req.on('login',(info,callback)=>{const auth=credentials?.(info);if(auth)callback(auth.username,auth.password);else{callback();finish(new Error('Proxy yêu cầu thông tin đăng nhập không phù hợp.'))}});
    req.on('error',()=>finish(new Error('Không kết nối được dịch vụ kiểm tra IP qua proxy này.')));
    req.on('response',response=>{
      if(response.statusCode!==200){finish(new Error(`Kiểm tra IP trả HTTP ${response.statusCode}.`));return}
      response.on('data',chunk=>{bytes+=chunk.length;if(bytes>4096)finish(new Error('Phản hồi kiểm tra IP quá lớn.'));else chunks.push(chunk)});
      response.on('error',()=>finish(new Error('Chưa nhận đủ phản hồi IP proxy.')));
      response.on('end',()=>{if(settled)return;try{const value=JSON.parse(Buffer.concat(chunks).toString()).ip;if(typeof value!=='string'||!isIP(value))throw new Error();finish(null,value)}catch{finish(new Error('Dịch vụ kiểm tra không trả địa chỉ IPv4/IPv6 hợp lệ.'))}});
    });
    timer=setTimeout(()=>finish(new Error('Hết thời gian kiểm tra IP proxy.')),timeoutMs);
    signal?.addEventListener('abort',abort,{once:true});
    if(signal?.aborted)abort();else{req.setHeader('Cache-Control','no-cache');req.end()}
  });
}

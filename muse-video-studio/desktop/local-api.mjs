import http from 'node:http';
import {MAX_SLOTS,LOCAL_RENDER_TIMEOUT_MS} from '../limits.mjs';

const endpoints=new Set(['/api/image','/api/video','/api/text','/api/media/recover']);
const codes=new Set(['ECONNREFUSED','ECONNRESET','ETIMEDOUT','EPIPE','ENETUNREACH','EHOSTUNREACH','ENOBUFS']);
const failure=(code,message)=>Object.assign(new Error(`${code}: ${message}`),{code});
// This is only the owned loopback Studio API. Muse continues to use its own
// Electron session/proxy. No global fetch dispatcher, proxy or five-minute
// response-header timeout may affect a long-running generation request here.
export class LocalApiClient {
  constructor({timeoutMs=LOCAL_RENDER_TIMEOUT_MS,maxResponseBytes=140*1024*1024}={}){
    this.timeoutMs=timeoutMs;this.maxResponseBytes=maxResponseBytes;
    this.agent=new http.Agent({keepAlive:true,maxSockets:MAX_SLOTS,maxFreeSockets:16,timeout:0,proxyEnv:{}});
  }
  request(baseURL,endpoint,data,signal){
    let base;try{base=new URL(baseURL)}catch{return Promise.reject(failure('MUSE_LOCAL_URL_INVALID','Địa chỉ Studio không hợp lệ.'))}
    if(base.protocol!=='http:'||base.hostname!=='127.0.0.1'||base.username||base.password||base.search||base.hash||!endpoints.has(endpoint))return Promise.reject(failure('MUSE_LOCAL_URL_INVALID','Chỉ gọi API tạo nội dung của Studio trên máy này.'));
    let body;try{body=JSON.stringify(data)}catch{return Promise.reject(failure('MUSE_LOCAL_BODY_INVALID','Dữ liệu yêu cầu không hợp lệ.'))}
    if(typeof body!=='string'||Buffer.byteLength(body)>12*1024*1024)return Promise.reject(failure('MUSE_LOCAL_BODY_INVALID','Yêu cầu vượt giới hạn 12 MB.'));
    signal?.throwIfAborted();
    return new Promise((resolve,reject)=>{
      let settled=false;let timer;
      const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);error?reject(error):resolve(value)};
      const req=http.request(new URL(endpoint,base),{method:'POST',agent:this.agent,headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),'Accept':'application/json'}},res=>{
        const chunks=[];let bytes=0;
        res.on('data',chunk=>{bytes+=chunk.length;if(bytes>this.maxResponseBytes){const error=failure('MUSE_LOCAL_RESPONSE_TOO_LARGE','Kết quả vượt giới hạn tải của Studio.');finish(error);req.destroy();return;}chunks.push(chunk)});
        res.on('aborted',()=>finish(failure('MUSE_LOCAL_CONNECTION_LOST','Kết nối nội bộ bị ngắt khi chờ kết quả (ECONNRESET). Kiểm tra lịch sử Muse trước khi gửi lại.')));
        res.on('error',error=>finish(failure('MUSE_LOCAL_CONNECTION_LOST',`Không đọc được phản hồi nội bộ (${codes.has(error.code)?error.code:'SOCKET_ERROR'}).`)));
        res.on('end',()=>{
          if(settled)return;let result;try{result=JSON.parse(Buffer.concat(chunks).toString('utf8'))}catch{finish(failure('MUSE_LOCAL_RESPONSE_INVALID',`Studio chưa trả phản hồi JSON hợp lệ (HTTP ${res.statusCode}).`));return;}
          finish(null,{ok:res.statusCode>=200&&res.statusCode<300,body:result});
        });
      });
      const abort=()=>{finish(signal.reason||failure('ABORTED','Đã dừng luồng.'));req.destroy()};
      req.on('error',error=>finish(failure('MUSE_LOCAL_CONNECTION_FAILED',`Không kết nối được máy chủ nội bộ (${codes.has(error.code)?error.code:'SOCKET_ERROR'}). Muse có thể đã nhận yêu cầu; tool không tự gửi trùng.`)));
      req.setTimeout(0);
      timer=setTimeout(()=>{finish(failure('MUSE_LOCAL_TIMEOUT','Hết thời gian chờ máy chủ nội bộ. Kiểm tra lịch sử Muse trước khi gửi lại.'));req.destroy()},this.timeoutMs);timer.unref?.();
      signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted){abort();return;}req.end(body);
    });
  }
  close(){this.agent.destroy()}
}

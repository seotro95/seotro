import {mcpResponse} from './mcp-protocol.mjs';
import http from 'node:http';
import { randomBytes, createHash, timingSafeEqual } from 'node:crypto';
import { readFile, writeFile, rename } from 'node:fs/promises';
import path from 'node:path';

const failure=(status,message)=>Object.assign(new Error(message),{status});
export class AutomationServer {
  constructor({userData,dispatch,version}) {
    this.file=path.join(userData,'automation.json');this.dispatch=dispatch;this.version=version;
    this.config={enabled:false,port:8790,key:randomBytes(32).toString('hex')};this.server=null;this.error='';this.idempotency=new Map();this.active=0;
  }
  async load() {
    try {const value=JSON.parse(await readFile(this.file,'utf8'));if(Number.isInteger(value.port)&&value.port>=1024&&value.port<=65535&&/^[a-f0-9]{64}$/.test(value.key))this.config={enabled:value.enabled===true,port:value.port,key:value.key};}catch{}
    if(this.config.enabled)try{await this.start()}catch(error){this.error=error.code==='EADDRINUSE'?'Cổng API đang được ứng dụng khác sử dụng. Chọn cổng khác rồi bật lại.':'Chưa mở được cổng API.';this.config.enabled=false;}
    return this;
  }
  snapshot(){return {...this.config,listening:Boolean(this.server?.listening),address:`http://127.0.0.1:${this.config.port}`,error:this.error};}
  async save(config=this.config){await writeFile(this.file+'.tmp',JSON.stringify(config),{mode:0o600});await rename(this.file+'.tmp',this.file);}
  async configure({enabled,port}) {
    if(typeof enabled!=='boolean'||!Number.isInteger(port)||port<1024||port>65535)throw failure(400,'Cổng API phải từ 1024 đến 65535.');
    await this.close();this.config={...this.config,enabled,port};this.error='';
    try{if(enabled)await this.start();await this.save();}catch(error){await this.close();this.config.enabled=false;this.error=error.code==='EADDRINUSE'?'Cổng đang được sử dụng. Chọn cổng khác.':'Không mở hoặc lưu được cấu hình API.';throw failure(409,this.error);}
    return this.snapshot();
  }
  async rotate(){const next={...this.config,key:randomBytes(32).toString('hex')};await this.save(next);this.config=next;this.idempotency.clear();return this.snapshot();}
  async start(){
    const server=http.createServer((req,res)=>void this.handle(req,res));
    server.requestTimeout=150000;server.headersTimeout=10000;server.maxHeadersCount=40;
    try{await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(this.config.port,'127.0.0.1',()=>{server.removeListener('error',reject);resolve()})});this.server=server;}catch(error){server.close();throw error;}
  }
  async close(){const server=this.server;this.server=null;if(server){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}}
  json(res,status,data){if(!res.destroyed){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(data));}}
  async body(req){let size=0;const chunks=[];for await(const chunk of req){size+=chunk.length;if(size>12*1024*1024)throw failure(413,'Yêu cầu tối đa 12 MB.');chunks.push(chunk)}if(!size)return {};try{const value=JSON.parse(Buffer.concat(chunks).toString());if(!value||typeof value!=='object'||Array.isArray(value))throw new Error();return value}catch{throw failure(400,'Cần một đối tượng JSON hợp lệ.')}}
  async invoke(action,data,key) {
    if(key===undefined||!['batch','run'].includes(action))return this.dispatch(action,data);
    if(typeof key!=='string'||!/^[-a-z0-9_.]{1,128}$/i.test(key))throw failure(400,'Idempotency-Key/requestId không hợp lệ.');
    const hash=createHash('sha256').update(action+JSON.stringify(data)).digest('hex');const previous=this.idempotency.get(key);
    if(previous&&previous.hash!==hash)throw failure(409,'Idempotency-Key/requestId đã dùng cho nội dung khác.');
    if(previous)return previous.promise;
    while(this.idempotency.size>=128){const oldest=[...this.idempotency].find(([,entry])=>entry.done);if(!oldest)throw failure(429,'Đợi các yêu cầu tạo bộ hiện tại.');this.idempotency.delete(oldest[0]);}
    const entry={hash,done:false,promise:null};entry.promise=Promise.resolve().then(()=>this.dispatch(action,data)).finally(()=>{entry.done=true});this.idempotency.set(key,entry);return entry.promise;
  }
  async handle(req,res){
    let acquired=false;
    try{
      if(!['127.0.0.1','::ffff:127.0.0.1','::1'].includes(req.socket.remoteAddress)||!['127.0.0.1','localhost'].includes((req.headers.host||'').split(':')[0])||req.headers.origin||req.headers['sec-fetch-site']==='cross-site')throw failure(403,'Cổng API chỉ nhận công cụ trên cùng máy tính.');
      const supplied=String(req.headers.authorization||'');
      const actual=createHash('sha256').update(supplied).digest();const expected=createHash('sha256').update('Bearer '+this.config.key).digest();
      if(!timingSafeEqual(actual,expected))throw failure(401,'Cần Authorization: Bearer <khóa API trong Studio>.');
      if(this.active>=8)throw failure(429,'Đã có nhiều yêu cầu API. Đợi rồi kiểm tra tiến độ.');
      this.active++;acquired=true;
      const url=new URL(req.url,'http://127.0.0.1');if(url.search)throw failure(400,'Không đặt khóa hoặc tham số trong URL.');
      const method=req.method;const route=url.pathname;
      if(route==='/mcp'){
        if(method!=='POST'){res.setHeader('Allow','POST');throw failure(405,'MCP sử dụng POST /mcp (Streamable HTTP).');}
        if(!req.headers['content-type']?.startsWith('application/json'))throw failure(415,'Dùng Content-Type: application/json.');
        const message=await this.body(req);const reply=await mcpResponse(message,{version:this.version,invoke:(action,data,key)=>this.invoke(action,data,key)});
        if(reply.body===null){res.writeHead(202,{'Cache-Control':'no-store'});res.end();}else this.json(res,reply.status,reply.body);return;
      }
      let action,data={};
      if(method==='GET'&&route==='/v1/status')action='status';
      else if(method==='GET'&&route==='/v1/media')action='media-list';
      else if(method==='GET'&&/^\/v1\/media\/[a-f0-9-]{36}$/i.test(route)){action='media';data={id:route.split('/').at(-1)};}
      else if(method==='POST'&&route==='/v1/batches'){action='batch';data=await this.body(req);}
      else if(method==='POST'&&route==='/v1/save'){action='save-media';data=await this.body(req);}
      else if(method==='POST'&&route==='/v1/stop'){action='stop';data=await this.body(req);}
      else if(method==='DELETE'&&route==='/v1/media'){data=await this.body(req);if(data.confirm!=='DELETE_ALL_MEDIA')throw failure(400,'Gửi confirm: DELETE_ALL_MEDIA để xóa thư viện tool.');action='clear-media';}
      else throw failure(404,'Endpoint không có. Xem API-AUTOMATION.md trong gói chương trình.');
      if(['POST','DELETE'].includes(method)&&!req.headers['content-type']?.startsWith('application/json'))throw failure(415,'Dùng Content-Type: application/json.');
      const promise=this.invoke(action,data,req.headers['idempotency-key']);
      const result=await promise;
      if(action==='media'){
        const extension={'image/png':'png','image/jpeg':'jpg','image/webp':'webp','video/mp4':'mp4','video/webm':'webm','video/quicktime':'mov'}[result.mimeType];
        if(!extension||typeof result.base64!=='string'||result.base64.length>210*1024*1024||!/^[-a-f0-9]{36}$/i.test(data.id))throw failure(502,'Dữ liệu media không hợp lệ.');
        const bytes=Buffer.from(result.base64,'base64');
        if(!res.destroyed){res.writeHead(200,{'Content-Type':result.mimeType,'Content-Length':bytes.length,'Content-Disposition':`attachment; filename="media-${data.id}.${extension}"`,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(bytes);}
      }else this.json(res,action==='batch'?202:200,{...result,...(action==='status'?{version:this.version}:{} )});
    }catch(error){this.json(res,Number.isInteger(error.status)?error.status:500,{error:typeof error.message==='string'?error.message.slice(0,1000):'API_ERROR'});}
    finally{if(acquired)this.active--;}
  }
}

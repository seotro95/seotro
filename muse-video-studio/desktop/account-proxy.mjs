const fail=message=>Object.assign(new Error('MUSE_PROXY_INVALID: '+message),{status:400});
export function normalizeProxy(data,previous){
  if(data?.enabled===false)return null;
  if(data?.enabled!==true||typeof data.server!=='string'||data.server.length>512)throw fail('Nhập địa chỉ proxy hợp lệ hoặc tắt proxy.');
  let url;try{url=new URL(data.server)}catch{throw fail('Dùng dạng http://host:port, https://host:port hoặc socks5://host:port.')}
  if(!['http:','https:','socks5:'].includes(url.protocol)||!url.hostname||url.username||url.password||!['','/'].includes(url.pathname)||url.search||url.hash)throw fail('Địa chỉ proxy không được chứa tài khoản, đường dẫn hoặc tham số.');
  const server=url.origin==='null'?`${url.protocol}//${url.host}`:url.origin;
  const same=previous?.server===server;
  const username=data.username===undefined&&same?previous.username:data.username||'';
  const password=data.password===undefined&&same?previous.password:data.password||'';
  if(typeof username!=='string'||typeof password!=='string'||username.length>512||password.length>1024||/[\r\n\x00]/.test(username+password))throw fail('Tài khoản proxy không hợp lệ.');
  if(url.protocol==='socks5:'&&(username||password))throw fail('Chromium không hỗ trợ SOCKS5 có mật khẩu. Dùng proxy HTTP/HTTPS nếu cần đăng nhập.');
  return {server,username,password};
}
export class AccountProxies {
  constructor({storage,inheritedProxy,sessionForAccount,lookupIP}){this.storage=storage;this.inheritedProxy=inheritedProxy;this.sessionForAccount=sessionForAccount;this.lookupIP=lookupIP;this.configs=new Map();this.sessions=new Map();this.ipStatus=new Map();this.checks=new Map()}
  async load(){for(let id=1;id<=40;id++){const data=await this.storage.read(id,'proxy');if(data?.server){try{this.configs.set(id,normalizeProxy({enabled:true,...data}))}catch{}}}return this}
  snapshot(id){const config=this.configs.get(id);return {supported:true,enabled:Boolean(config),server:config?.server||'',hasUsername:Boolean(config?.username),hasPassword:Boolean(config?.password),...this.ipStatus.get(id)}}
  async checkIP(id,signal){
    if(!this.configs.has(id))throw fail('Bật và lưu proxy của tài khoản trước khi kiểm tra IP.');
    if(this.checks.has(id))return this.checks.get(id);
    const config=this.configs.get(id);
    const task=(async()=>{
      this.ipStatus.set(id,{ipState:'checking',exitIP:'',ipError:'',ipCheckedAt:null});
      try{
        const session=this.sessions.get(id)||await this.sessionForAccount?.(id);
        if(!session||!this.lookupIP)throw new Error('Kiểm tra IP proxy cần bản desktop.');
        if(!this.sessions.has(id))await this.apply(id,session);
        const route=await session.resolveProxy('https://api.ipify.org?format=json');
        if(!route||route.split(';').some(value=>value.trim()==='DIRECT'))throw new Error('Proxy đang trả đường đi trực tiếp. Chưa xác nhận IP proxy.');
        const exitIP=await this.lookupIP(session,info=>this.credentials({session},info),signal);
        if(config!==this.configs.get(id))throw new Error('Proxy đã thay đổi trong lúc kiểm tra.');
        this.ipStatus.set(id,{ipState:'ready',exitIP,ipError:'',ipCheckedAt:new Date().toISOString()});
      }catch(error){if(config===this.configs.get(id))this.ipStatus.set(id,{ipState:'error',exitIP:'',ipError:error.message,ipCheckedAt:new Date().toISOString()});}
      return this.snapshot(id);
    })().finally(()=>this.checks.delete(id));this.checks.set(id,task);return task;
  }
  async apply(id,session){
    this.sessions.set(id,session);const server=this.configs.get(id)?.server||this.inheritedProxy;
    await session.setProxy(server?{mode:'fixed_servers',proxyRules:server,proxyBypassRules:'localhost;127.0.0.1'}:{mode:'direct'});
    await session.closeAllConnections();
  }
  async configure(id,data){
    const config=normalizeProxy(data,this.configs.get(id));
    await this.storage.write(id,'proxy',config||{enabled:false});
    if(config)this.configs.set(id,config);else this.configs.delete(id);
    this.ipStatus.delete(id);
    if(this.sessions.has(id))await this.apply(id,this.sessions.get(id));
    return this.snapshot(id);
  }
  credentials(contents,info){
    if(!info.isProxy)return null;
    const entry=[...this.sessions].find(([,session])=>session===contents?.session);const config=entry&&this.configs.get(entry[0]);
    if(!config||!config.username)return null;
    const url=new URL(config.server);const port=Number(url.port||(url.protocol==='https:'?443:1080));
    if(info.host!==url.hostname||Number(info.port)!==(url.protocol==='http:'&&!url.port?80:port))return null;
    return {username:config.username,password:config.password};
  }
}

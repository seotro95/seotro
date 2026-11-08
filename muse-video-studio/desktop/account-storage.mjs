import {mkdir,readFile,writeFile,rename,readdir} from 'node:fs/promises';
import path from 'node:path';

// The codec is Electron safeStorage (DPAPI on Windows). Never fall back to JSON
// for cookies, sessionStorage or proxy credentials when encryption is unavailable.
export class AccountStorage {
  constructor({userData,codec,serviceURL,allowBasic=false}) {
    this.directory=path.join(userData,'account-vault');this.userData=userData;this.codec=codec;
    this.origin=new URL(serviceURL).origin;this.hostname=new URL(serviceURL).hostname;this.allowBasic=allowBasic;this.writes=new Map();
    this.records=new Map();
  }
  available(){return this.codec.isEncryptionAvailable()&&(this.allowBasic||this.codec.getSelectedStorageBackend?.()!=='basic_text')}
  file(id,kind){if(!Number.isInteger(id)||id<1||id>40||!['session','proxy'].includes(kind))throw new Error('ACCOUNT_INVALID');return path.join(this.directory,`${kind}-${id}.bin`)}
  remember(id,value){if(value?.origin===this.origin)this.records.set(id,{savedAt:value.savedAt||null,hasSession:Boolean(value.cookies?.length||Object.keys(value.storage||{}).length)})}
  metadata(id){return this.records.get(id)||{savedAt:null,hasSession:false}}
  async read(id,kind){try{const value=JSON.parse(await this.codec.decryptString(await readFile(this.file(id,kind))));if(kind==='session')this.remember(id,value);return value}catch{return null}}
  async write(id,kind,value){
    if(!this.available())throw new Error('MUSE_SECURE_STORAGE_UNAVAILABLE: Không có kho mã hóa của hệ điều hành. Phiên Chromium vẫn được giữ; không lưu thông tin nhạy cảm dạng văn bản.');
    const file=this.file(id,kind);const previous=this.writes.get(file)||Promise.resolve();
    const task=previous.catch(()=>{}).then(async()=>{await mkdir(this.directory,{recursive:true,mode:0o700});await writeFile(file+'.tmp',await this.codec.encryptString(JSON.stringify(value)),{mode:0o600});await rename(file+'.tmp',file)});
    this.writes.set(file,task);try{await task}finally{if(this.writes.get(file)===task)this.writes.delete(file)}
  }
  allowedCookie(cookie){const domain=cookie.domain?.replace(/^\./,'');return domain===this.hostname||domain?.endsWith('.'+this.hostname)}
  async capture(id,session,page){
    const cookies=(await session.cookies.get({})).filter(cookie=>this.allowedCookie(cookie));
    let storage={};
    if(page&&!page.isClosed())storage=await page.evaluate(origin=>location.origin===origin?Object.fromEntries(Object.entries(sessionStorage)):null,this.origin).catch(()=>null);
    // Cookie-change saves cannot read a tab while navigating. Keep its last
    // encrypted storage snapshot, then replace it on the next verified save.
    if(storage===null||!page){const previous=await this.read(id,'session');storage=previous?.origin===this.origin?previous.storage||{}:{}}
    session.flushStorageData();await session.cookies.flushStore();
    const value={version:1,origin:this.origin,cookies,storage,savedAt:Date.now()};await this.write(id,'session',value);this.remember(id,value);
  }
  async restore(id,session){
    const saved=await this.read(id,'session');if(!saved||saved.version!==1||saved.origin!==this.origin)return {};
    for(const cookie of saved.cookies||[]){
      if(!this.allowedCookie(cookie)||(cookie.expirationDate&&cookie.expirationDate<=Date.now()/1000))continue;
      // A persistent Chromium cookie is newer than the shutdown snapshot.
      const current=await session.cookies.get({name:cookie.name,domain:cookie.domain,path:cookie.path});
      if(current.some(item=>item.name===cookie.name&&item.path===cookie.path&&item.domain===cookie.domain))continue;
      const {name,value,domain,path:cookiePath,secure,httpOnly,sameSite,expirationDate,hostOnly}=cookie;
      await session.cookies.set({url:`${secure?'https':'http'}://${domain.replace(/^\./,'')}${cookiePath||'/'}`,name,value,...(!hostOnly?{domain}:{}),path:cookiePath,secure,httpOnly,sameSite,...(expirationDate?{expirationDate}:{})}).catch(()=>{});
    }
    return saved.storage&&typeof saved.storage==='object'?saved.storage:{};
  }
  async savedIds(){
    const ids=new Set();
    for(const name of await readdir(path.join(this.userData,'Partitions')).catch(()=>[])){
      const match=/^muse(?:-(\d{2}))?$/.exec(name);if(match){const id=match[1]?Number(match[1]):1;if(id>=1&&id<=40)ids.add(id)}
    }
    for(const name of await readdir(this.directory).catch(()=>[])){const match=/^session-(\d+)\.bin$/.exec(name);if(match&&Number(match[1])<=40)ids.add(Number(match[1]))}
    return [...ids].sort((a,b)=>a-b);
  }
}

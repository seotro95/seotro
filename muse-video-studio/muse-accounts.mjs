import {MAX_SLOTS,isSlotCount} from './limits.mjs';
import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import path from 'node:path';
import { MuseBrowser } from './muse-browser.mjs';

const fail = (code, message, status = 409) => Object.assign(new Error(`${code}: ${message}`), { status });
export class MuseAccounts {
  constructor({ profileRoot, accountProfile, createDriver, preferredConcurrency = 2, onSelect = () => {}, proxyStatus, configureProxy, persistenceStatus,saveSessions }) {
    this.profileRoot = profileRoot; this.preferredConcurrency=preferredConcurrency;this.concurrencyWarning='';
    this.createDriver = createDriver || (id => new MuseBrowser({ profileRoot, ...(id === 1 ? {accountProfile} : { accountProfile: path.join(profileRoot, `slot-${String(id).padStart(2,'0')}`) }) }));
    this.onSelect = onSelect; this.selectedId = 1; this.singleId = 1; this.drivers = new Map(); this.usage = new Map(); this.labels = [];
    this.supportsMultiAccount = true; this.images = new Map();
    this.proxyStatus=proxyStatus;this.configureProxy=configureProxy;this.restoring=false;
    this.persistenceStatus=persistenceStatus;this.saveSessions=saveSessions;
  }
  async load() {
    try { this.labels = this.validateLabels(JSON.parse(await readFile(path.join(this.profileRoot,'account-labels.json'),'utf8'))); } catch {}
    try {const count=JSON.parse(await readFile(path.join(this.profileRoot,'single-concurrency.json'),'utf8'));if(isSlotCount(count))this.preferredConcurrency=count;}catch{}
    return this;
  }
  validateId(id) { if (!Number.isInteger(id) || id < 1 || id > MAX_SLOTS) throw fail('ACCOUNT_INVALID','Chọn tài khoản từ 1 đến 40.',400); }
  driver(id) { this.validateId(id); if (!this.drivers.has(id)) this.drivers.set(id,this.createDriver(id)); return this.drivers.get(id); }
  account(id) { return { ...this.driver(id).account(1), id, label: this.labels[id-1] || `Muse ${String(id).padStart(2,'0')}` }; }
  snapshot() { return Array.from({length:MAX_SLOTS},(_,i)=>{const id=i+1;const driver=this.drivers.get(id);return {...(driver?.snapshot?.()[0]||driver?.account(1)||{state:'disconnected',authenticated:false,sessionAuthenticated:false,checkedAt:null,balance:null}),id,label:this.labels[i]||`Muse ${String(id).padStart(2,'0')}`,active:Boolean(driver?.active),running:this.usage.get(id)?.count||0,persistence:this.persistenceStatus?.(id),proxy:this.proxyStatus?.(id)||{supported:false}}}); }
  async restoreSessions(ids){
    this.restoring=true;let next=0;
    try{await Promise.all(Array.from({length:Math.min(3,ids.length)},async()=>{while(next<ids.length){const id=ids[next++];try{await this.connect(id,{show:false})}catch{this.driver(id).account(1).state='check_failed'}}}))}finally{this.restoring=false}
  }
  async setProxy(id,data){this.validateId(id);if(!this.configureProxy)throw fail('MUSE_PROXY_UNSUPPORTED','Proxy từng tài khoản chỉ có trong bản desktop.',409);if(this.usage.size)throw fail('MUSE_CHAT_BUSY','Đợi hoặc dừng tác vụ trước khi đổi proxy.');return this.configureProxy(id,data)}
  get maxConcurrency() { return this.driver(this.singleId).maxConcurrency; }
  get queue() { return [...this.drivers.values()].flatMap(driver=>driver.queue); }
  progress() { return [...this.drivers].flatMap(([accountId,driver])=>driver.progress().map(stage=>({...stage,accountId}))); }
  async refreshActive(options) { await this.drivers.get(this.selectedId)?.refreshActive(options); }
  async select(id) { this.driver(id); this.selectedId=id; await this.onSelect(id); }
  async connect(id=1,options={}) {
    const driver=this.driver(id);
    if (options.show !== false) { await this.select(id); }
    return driver.connect(1,options);
  }
  async requestConcurrency(count) {
    if(!isSlotCount(count))throw fail('MUSE_CONCURRENCY_INVALID','Chọn từ 1 đến 40 luồng.',400);
    await mkdir(this.profileRoot,{recursive:true,mode:0o700});const file=path.join(this.profileRoot,'single-concurrency.json');await writeFile(file+'.tmp',JSON.stringify(count),{mode:0o600});await rename(file+'.tmp',file);this.preferredConcurrency=count;
  }
  async setConcurrency(count,signal,id=1) {
    this.validateId(id);this.singleId=id;
    await this.requestConcurrency(count);this.concurrencyWarning='';
    try{return {...await this.driver(id).setConcurrency(count,signal),preferredConcurrency:count};}
    catch(error){if(/MUSE_PARALLEL_UNVERIFIED|MUSE_NEW_CHAT_UNAVAILABLE|MUSE_COMPOSER_NOT_READY/.test(error.message))this.concurrencyWarning=error.message;throw error;}
  }
  async prepareSingle(signal,count=this.preferredConcurrency,id=1) {
    this.validateId(id);this.singleId=id;
    if(!isSlotCount(count))throw fail('MUSE_CONCURRENCY_INVALID','Chọn từ 1 đến 40 luồng.',400);
    if(this.driver(id).maxConcurrency===count){this.concurrencyWarning='';if(this.preferredConcurrency!==count)await this.requestConcurrency(count);return {executionConcurrency:this.maxConcurrency,preferredConcurrency:count,concurrencyWarning:''};}
    try{return await this.setConcurrency(count,signal,id)}catch(error){if(!this.concurrencyWarning)throw error;return {executionConcurrency:this.maxConcurrency,preferredConcurrency:count,concurrencyWarning:this.concurrencyWarning,message:'Muse chưa xác minh được hội thoại riêng. Các ô sẽ chạy theo số luồng đã xác minh, không trộn kết quả.'};}
  }
  async checkComposer(signal,id=1) { return this.driver(id).checkComposer(signal); }
  async closeAccount(id) { if (this.usage.has(id)) throw fail('MUSE_CHAT_BUSY','Tài khoản này đang có tác vụ.'); await this.driver(id).close(); }
  async close() { await Promise.allSettled([...this.drivers.values()].map(driver=>driver.close())); }
  async reopenLogin() { return this.driver(this.selectedId).reopenLogin(); }
  async openEmailLink(link) { return this.driver(this.selectedId).openEmailLink(link); }
  validateLabels(labels) {
    if (!Array.isArray(labels) || !labels.length || labels.length>MAX_SLOTS || labels.some(label=>typeof label!=='string' || !label.trim() || label.length>120 || /[\r\n\t|;:\x00-\x1f]/.test(label))) throw fail('ACCOUNT_LIST_INVALID','Nhập 1–40 email hoặc tên quản lý, mỗi dòng một tên; không nhập mật khẩu, mã hoặc token.',400);
    const values=labels.map(label=>label.trim());
    if (new Set(values.map(value=>value.toLowerCase())).size!==values.length) throw fail('ACCOUNT_LIST_INVALID','Danh sách có tên hoặc email trùng nhau.',400);
    return values;
  }
  async importLabels(labels) {
    const values=this.validateLabels(labels);
    await mkdir(this.profileRoot,{recursive:true,mode:0o700});
    const file=path.join(this.profileRoot,'account-labels.json');
    await writeFile(file+'.tmp',JSON.stringify(values),{mode:0o600}); await rename(file+'.tmp',file);
    this.labels=values; return this.snapshot();
  }
  async generate(method,data,signal) {
    const id=data.accountId; this.validateId(id);
    const multiple=data.accountMode==='multiple';
    const usage=this.usage.get(id);
    if (usage && (multiple || usage.multiple)) throw fail('MUSE_ACCOUNT_BUSY',`Muse ${id} đang chạy một luồng. Đợi hoặc dừng tác vụ đó trước.`);
    this.usage.set(id,{count:(usage?.count||0)+1,multiple});
    try {
      const result=await this.driver(id)[method]({...data,accountId:1,singleLane:multiple},signal);
      if (method==='generateImage' && result.fingerprint && data.batchId) {
        const previous=this.images.get(result.fingerprint);
        if (previous && previous.sceneId!==data.sceneId) throw fail('MUSE_DUPLICATE_MEDIA',`Ảnh trùng hoàn toàn với cảnh #${previous.sceneId}; chưa ghi nhận là kết quả mới.`);
        this.images.set(result.fingerprint,{sceneId:data.sceneId,batchId:data.batchId});
        while(this.images.size>160)this.images.delete(this.images.keys().next().value);
      }
      return result;
    } finally { const current=this.usage.get(id); if(current?.count>1)current.count--;else this.usage.delete(id); }
  }
  generateImage(data,signal) { return this.generate('generateImage',data,signal); }
  generateVideo(data,signal) { return this.generate('generateVideo',data,signal); }
  generateText(data,signal) { return this.generate('generateText',data,signal); }
}

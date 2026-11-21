import {MAX_ACCOUNTS,MAX_ACCOUNT_LANES,MAX_SLOTS,isSlotCount,isLaneCount} from './limits.mjs';
import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import path from 'node:path';
import { MuseBrowser } from './muse-browser.mjs';

const fail = (code, message, status = 409) => Object.assign(new Error(`${code}: ${message}`), { status });
export class MuseAccounts {
  constructor({ profileRoot, accountProfile, createDriver, preferredConcurrency = 6, onSelect = () => {}, proxyStatus, configureProxy, checkProxyIP, persistenceStatus,saveSessions }) {
    this.profileRoot = profileRoot; this.preferredConcurrency=preferredConcurrency;this.concurrencyWarning='';
    this.createDriver = createDriver || (id => new MuseBrowser({ profileRoot, ...(id === 1 ? {accountProfile} : { accountProfile: path.join(profileRoot, `slot-${String(id).padStart(2,'0')}`) }) }));
    this.shutdown=new AbortController();this.waiters=new Map();this.fallbacks=new Map();this.fallbackRequested=new Map();
    this.onSelect = onSelect; this.selectedId = 1; this.singleId = 1; this.drivers = new Map(); this.usage = new Map(); this.labels = [];
    this.supportsMultiAccount = true; this.images = new Map();
    this.checkProxyIP=checkProxyIP;this.proxyStatus=proxyStatus;this.configureProxy=configureProxy;this.restoring=false;
    this.persistenceStatus=persistenceStatus;this.saveSessions=saveSessions;
  }
  async load() {
    try { this.labels = this.validateLabels(JSON.parse(await readFile(path.join(this.profileRoot,'account-labels.json'),'utf8'))); } catch {}
    try {const count=JSON.parse(await readFile(path.join(this.profileRoot,'single-concurrency.json'),'utf8'));if(isSlotCount(count))this.preferredConcurrency=Math.min(MAX_ACCOUNT_LANES,count);}catch{}
    return this;
  }
  validateId(id) { if (!Number.isInteger(id) || id < 1 || id > MAX_ACCOUNTS) throw fail('ACCOUNT_INVALID','Chọn tài khoản từ 1 đến 40.',400); }
  driver(id) { this.validateId(id); if (!this.drivers.has(id)) this.drivers.set(id,this.createDriver(id)); return this.drivers.get(id); }
  account(id) { return { ...this.driver(id).account(1), id, label: this.labels[id-1] || `Muse ${String(id).padStart(2,'0')}` }; }
  snapshot() { return Array.from({length:MAX_ACCOUNTS},(_,i)=>{const id=i+1;const driver=this.drivers.get(id);return {...(driver?.snapshot?.()[0]||driver?.account(1)||{state:'disconnected',authenticated:false,sessionAuthenticated:false,checkedAt:null,balance:null}),id,label:this.labels[i]||`Muse ${String(id).padStart(2,'0')}`,executionConcurrency:driver?.maxConcurrency||1,concurrencyWarning:this.fallbacks.get(id)||'',queued:this.waiters.get(id)?.length||0,active:Boolean(driver?.active),running:this.usage.get(id)?.count||0,persistence:this.persistenceStatus?.(id),proxy:this.proxyStatus?.(id)||{supported:false}}}); }
  async restoreSessions(ids){
    this.restoring=true;let next=0;
    try{await Promise.all(Array.from({length:Math.min(3,ids.length)},async()=>{while(next<ids.length){const id=ids[next++];try{await this.connect(id,{show:false})}catch{this.driver(id).account(1).state='check_failed'}}}))}finally{this.restoring=false}
  }
  async setProxy(id,data){this.validateId(id);if(!this.configureProxy)throw fail('MUSE_PROXY_UNSUPPORTED','Proxy từng tài khoản chỉ có trong bản desktop.',409);if(this.usage.size)throw fail('MUSE_CHAT_BUSY','Đợi hoặc dừng tác vụ trước khi đổi proxy.');return this.configureProxy(id,data)}
  get maxConcurrency() { return this.driver(this.singleId).maxConcurrency; }
  get queue() { return [...this.drivers.values()].flatMap(driver=>driver.queue).concat([...this.waiters.values()].flat()); }
  progress() { return [...this.drivers].flatMap(([accountId,driver])=>driver.progress().map(stage=>({...stage,accountId}))).concat([...this.waiters].flatMap(([accountId,rows])=>rows.map(row=>({accountId,batchId:row.data.batchId||null,sceneId:row.data.sceneId||null,phase:this.fallbacks.has(accountId)?'waiting-serial':'waiting-slot',active:true,submitted:false,startedAt:row.createdAt})))); }
  async refreshActive(options) { await this.drivers.get(this.selectedId)?.refreshActive(options); }
  async select(id) { this.driver(id); this.selectedId=id; await this.onSelect(id); }
  async connect(id=1,options={}) {
    const driver=this.driver(id);
    if (options.show !== false) { await this.select(id); }
    return driver.connect(1,options);
  }
  async requestConcurrency(count) {
    if(!isLaneCount(count))throw fail('MUSE_CONCURRENCY_INVALID','Chọn từ 1 đến 10 ô mỗi tài khoản.',400);
    const saved=(this.preferenceSave||Promise.resolve()).catch(()=>{}).then(async()=>{await mkdir(this.profileRoot,{recursive:true,mode:0o700});const file=path.join(this.profileRoot,'single-concurrency.json');await writeFile(file+'.tmp',JSON.stringify(count),{mode:0o600});await rename(file+'.tmp',file);this.preferredConcurrency=count;});this.preferenceSave=saved;await saved;
  }
  async setConcurrency(count,signal,id=1,options={}) {
    this.validateId(id);this.singleId=id;
    await this.requestConcurrency(count);this.concurrencyWarning='';this.fallbacks.delete(id);this.fallbackRequested.delete(id);
    try{return {...await this.driver(id).setConcurrency(count,signal,options),preferredConcurrency:count};}
    catch(error){if(/MUSE_PARALLEL_UNVERIFIED|MUSE_NEW_CHAT_UNAVAILABLE|MUSE_COMPOSER_NOT_READY/.test(error.message))this.concurrencyWarning=error.message;throw error;}
  }
  rememberImage(data,result){if(!result.fingerprint||!data.batchId)return;const previous=this.images.get(result.fingerprint);if(previous&&previous.sceneId!==data.sceneId)throw fail('MUSE_DUPLICATE_MEDIA',`Ảnh trùng hoàn toàn với cảnh #${previous.sceneId}; chưa ghi nhận là kết quả mới.`);this.images.set(result.fingerprint,{sceneId:data.sceneId,batchId:data.batchId});while(this.images.size>160)this.images.delete(this.images.keys().next().value);}
  fallback(id,reason,count=this.driver(id).concurrencyProbe?.requested||this.preferredConcurrency){
    const message=`Muse ${id}: không chạy được song song, tự chuyển sang từng luồng một. Các ô và tên tệp được giữ.`;
    this.fallbacks.set(id,message);this.fallbackRequested.set(id,count);this.concurrencyWarning=message;this.driver(id).maxConcurrency=1;this.driver(id).parallelStrategy='workers';
    return message;
  }
  async prepareSingle(signal,count=this.preferredConcurrency,id=1,retryParallel=false) {
    this.validateId(id);this.singleId=id;
    if(!isLaneCount(count))throw fail('MUSE_CONCURRENCY_INVALID','Chọn từ 1 đến 10 ô mỗi tài khoản.',400);
    await this.driver(id).ensureComposerReady?.(signal);
    if(!retryParallel&&this.driver(id).parallelStrategy==='shared-conversation'&&this.driver(id).concurrencyProbe?.requested===count)return {executionConcurrency:this.driver(id).maxConcurrency,preferredConcurrency:count,parallelStrategy:'shared-conversation',concurrencyWarning:this.concurrencyWarning};
    if(!retryParallel&&count>1&&this.fallbacks.has(id)&&this.fallbackRequested.get(id)===count)return {executionConcurrency:1,preferredConcurrency:count,concurrencyWarning:this.fallbacks.get(id),serialFallback:true};
    if(this.driver(id).maxConcurrency===count&&this.driver(id).parallelReady!==false){this.concurrencyWarning='';this.fallbacks.delete(id);this.fallbackRequested.delete(id);if(this.preferredConcurrency!==count)await this.requestConcurrency(count);return {executionConcurrency:this.driver(id).maxConcurrency,preferredConcurrency:count,concurrencyWarning:''};}
    try{return await this.setConcurrency(count,signal,id,{allowSharedFastPath:!retryParallel})}catch(error){
      if(count===1||signal.aborted||!/MUSE_PARALLEL_|MUSE_NEW_CHAT_UNAVAILABLE|MUSE_COMPOSER_NOT_READY/.test(error.message))throw error;
      if(error.parallelReason==='MUSE_NEW_CHAT_UNAVAILABLE'&&this.driver(id).useSharedConversation){
        try{const result=await this.driver(id).useSharedConversation(count,signal);this.concurrencyWarning=result.executionConcurrency<count?`Muse ${id}: gửi tối đa 6 yêu cầu đồng thời trong cùng cuộc trò chuyện; các ô còn lại chờ.`:'';return {...result,preferredConcurrency:count,concurrencyWarning:this.concurrencyWarning}}catch(sharedError){if(signal.aborted)throw sharedError;}
      }
      await this.driver(id).setConcurrency(1,signal);
      return {executionConcurrency:1,preferredConcurrency:count,concurrencyWarning:this.fallback(id,error,count),serialFallback:true,message:this.fallbacks.get(id)};
    }
  }
  async checkComposer(signal,id=1) { return this.driver(id).checkComposer(signal); }
  async clearToolDraft(data,signal){
    signal=AbortSignal.any([signal,this.shutdown.signal]);signal.throwIfAborted();
    const id=data.accountId;this.validateId(id);const driver=this.driver(id);
    if(this.restoring||this.usage.has(id)||this.waiters.get(id)?.length||driver.reserved||driver.queue?.length||driver.workers?.size||driver.composerBusy||driver.sharedSignals?.size||driver.progress?.().some(stage=>stage.active))throw fail('MUSE_CHAT_BUSY','Tài khoản này đang có tác vụ. Đợi hoàn tất trước khi dọn bản nháp tool.');
    if(!driver.clearToolDraft)throw fail('MUSE_DRAFT_CLEANUP_UNAVAILABLE','Kết nối này chưa hỗ trợ dọn bản nháp tool.');
    const release=await this.acquire(id,{exclusive:true},signal);
    try{return await driver.clearToolDraft({...data,accountId:1},signal)}finally{release()}
  }
  async closeAccount(id) { if (this.usage.has(id)) throw fail('MUSE_CHAT_BUSY','Tài khoản này đang có tác vụ.'); await this.driver(id).close(); }
  async close() { this.shutdown.abort();for(const rows of this.waiters.values())for(const row of [...rows])row.cancel();await Promise.allSettled([...this.drivers.values()].map(driver=>driver.close())); }
  async reopenLogin() { return this.driver(this.selectedId).reopenLogin(); }
  async openEmailLink(link) { return this.driver(this.selectedId).openEmailLink(link); }
  validateLabels(labels) {
    if (!Array.isArray(labels) || !labels.length || labels.length>MAX_ACCOUNTS || labels.some(label=>typeof label!=='string' || !label.trim() || label.length>120 || /[\r\n\t|;:\x00-\x1f]/.test(label))) throw fail('ACCOUNT_LIST_INVALID','Nhập 1–40 email hoặc tên quản lý, mỗi dòng một tên; không nhập mật khẩu, mã hoặc token.',400);
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
  acquire(id,data,signal){
    signal.throwIfAborted();
    const release=()=>{const current=this.usage.get(id);if(current?.count>1)current.count--;else this.usage.delete(id);this.pump(id)};
    const capacity=()=>this.usage.get(id)?.exclusive?0:Math.min(MAX_ACCOUNT_LANES,this.driver(id).maxConcurrency||1);
    if(!(this.waiters.get(id)?.length)&&(!data.exclusive||!this.usage.has(id))&&(this.usage.get(id)?.count||0)<capacity()){this.usage.set(id,{count:(this.usage.get(id)?.count||0)+1,exclusive:Boolean(data.exclusive)});return release;}
    if((this.waiters.get(id)?.length||0)>=MAX_SLOTS)throw fail('MUSE_CONCURRENCY_LIMIT','Hàng chờ tài khoản đã có 400 ô.',429);
    return new Promise((resolve,reject)=>{
      const rows=this.waiters.get(id)||[];this.waiters.set(id,rows);
      const row={data,createdAt:Date.now(),start:()=>{signal.removeEventListener('abort',row.cancel);resolve(release)},cancel:()=>{const index=rows.indexOf(row);if(index>=0)rows.splice(index,1);signal.removeEventListener('abort',row.cancel);reject(signal.reason||fail('ABORTED','Đã đóng hàng chờ.'));if(!rows.length)this.waiters.delete(id)}};
      signal.addEventListener('abort',row.cancel,{once:true});rows.push(row);
      rows.sort((a,b)=>a.data.batchId===b.data.batchId?(a.data.sceneId||0)-(b.data.sceneId||0):a.createdAt-b.createdAt);this.pump(id);
    });
  }
  pump(id){
    const rows=this.waiters.get(id);const capacity=Math.min(MAX_ACCOUNT_LANES,this.driver(id).maxConcurrency||1);
    while(rows?.length&&!this.usage.get(id)?.exclusive&&(this.usage.get(id)?.count||0)<capacity){if(rows[0].data.exclusive&&this.usage.has(id))break;const row=rows.shift();this.usage.set(id,{count:(this.usage.get(id)?.count||0)+1,exclusive:Boolean(row.data.exclusive)});row.start();if(row.data.exclusive)break;}
    if(!rows?.length)this.waiters.delete(id);
  }
  async generate(method,data,signal) {
    signal=AbortSignal.any([signal,this.shutdown.signal]);signal.throwIfAborted();
    const id=data.accountId;this.validateId(id);let retried=false;const request={...data,exclusive:method==='generateText'&&this.driver(id).parallelStrategy==='shared-conversation'};let lease=this.acquire(id,request,signal);
    for(;;){
      const release=typeof lease==='function'?lease:await lease;let retry;
      try{
        const serial=this.fallbacks.has(id)||this.driver(id).maxConcurrency===1;
        if(this.fallbacks.has(id))await this.driver(id).closePreparedPages?.();
        const result=await this.driver(id)[method]({...data,accountId:1,singleLane:serial||this.driver(id).parallelStrategy==='shared-conversation',submissionGroup:serial?undefined:data.submissionGroup},signal);
        if(method==='generateImage')this.rememberImage(data,result);
        return result;
      }catch(error){
        if(signal.aborted)throw error;
        if(error.parallelFailure){this.fallback(id,error);}
        if(!retried&&error.parallelFailure&&(error.notSubmitted===true||error.safeSerialRetry===true)){
          retried=true;retry=this.acquire(id,request,signal);if(typeof retry!=='function')retry.catch(()=>{});
        }else throw error;
      }finally{release()}
      lease=retry;
    }
  }
  generateImage(data,signal) { return this.generate('generateImage',data,signal); }
  generateVideo(data,signal) { return this.generate('generateVideo',data,signal); }
  generateText(data,signal) { return this.generate('generateText',data,signal); }
  async recoverMedia(data,signal){
    signal=AbortSignal.any([signal,this.shutdown.signal]);signal.throwIfAborted();this.validateId(data.accountId);
    const release=await this.acquire(data.accountId,{...data,exclusive:true},signal);
    try{return await this.driver(data.accountId).recoverMedia({...data,accountId:1},signal)}finally{release()}
  }
}

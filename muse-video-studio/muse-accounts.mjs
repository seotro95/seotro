import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import path from 'node:path';
import { MuseBrowser } from './muse-browser.mjs';

const fail = (code, message, status = 409) => Object.assign(new Error(`${code}: ${message}`), { status });
export class MuseAccounts {
  constructor({ profileRoot, accountProfile, createDriver, onSelect = () => {} }) {
    this.profileRoot = profileRoot;
    this.createDriver = createDriver || (id => new MuseBrowser({ profileRoot, ...(id === 1 ? {accountProfile} : { accountProfile: path.join(profileRoot, `slot-${String(id).padStart(2,'0')}`) }) }));
    this.onSelect = onSelect; this.selectedId = 1; this.drivers = new Map(); this.usage = new Map(); this.labels = [];
    this.supportsMultiAccount = true; this.images = new Map();
  }
  async load() {
    try { this.labels = this.validateLabels(JSON.parse(await readFile(path.join(this.profileRoot,'account-labels.json'),'utf8'))); } catch {}
    return this;
  }
  validateId(id) { if (!Number.isInteger(id) || id < 1 || id > 10) throw fail('ACCOUNT_INVALID','Chọn tài khoản từ 1 đến 10.',400); }
  driver(id) { this.validateId(id); if (!this.drivers.has(id)) this.drivers.set(id,this.createDriver(id)); return this.drivers.get(id); }
  account(id) { return { ...this.driver(id).account(1), id, label: this.labels[id-1] || `Muse ${String(id).padStart(2,'0')}` }; }
  snapshot() { return Array.from({length:10},(_,i)=>({ ...this.account(i+1), active: Boolean(this.drivers.get(i+1)?.active), running: this.usage.get(i+1)?.count || 0 })); }
  get maxConcurrency() { return this.driver(1).maxConcurrency; }
  get queue() { return [...this.drivers.values()].flatMap(driver=>driver.queue); }
  progress() { return [...this.drivers].flatMap(([accountId,driver])=>driver.progress().map(stage=>({...stage,accountId}))); }
  async refreshActive(options) { await this.drivers.get(this.selectedId)?.refreshActive(options); }
  async select(id) { this.driver(id); this.selectedId=id; await this.onSelect(id); }
  async connect(id=1,options={}) {
    const driver=this.driver(id);
    if (options.show !== false) { await this.select(id); }
    return driver.connect(1,options);
  }
  async setConcurrency(count,signal) { return this.driver(1).setConcurrency(count,signal); }
  async checkComposer(signal,id=1) { return this.driver(id).checkComposer(signal); }
  async closeAccount(id) { if (this.usage.has(id)) throw fail('MUSE_CHAT_BUSY','Tài khoản này đang có tác vụ.'); await this.driver(id).close(); }
  async close() { await Promise.allSettled([...this.drivers.values()].map(driver=>driver.close())); }
  async reopenLogin() { return this.driver(this.selectedId).reopenLogin(); }
  async openEmailLink(link) { return this.driver(this.selectedId).openEmailLink(link); }
  validateLabels(labels) {
    if (!Array.isArray(labels) || !labels.length || labels.length>10 || labels.some(label=>typeof label!=='string' || !label.trim() || label.length>120 || /[\r\n\t|;:\x00-\x1f]/.test(label))) throw fail('ACCOUNT_LIST_INVALID','Nhập 1–10 email hoặc tên quản lý, mỗi dòng một tên; không nhập mật khẩu, mã hoặc token.',400);
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
    if (!multiple && id!==1) throw fail('ACCOUNT_INVALID','Chế độ một tài khoản chỉ dùng Muse 01.',400);
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

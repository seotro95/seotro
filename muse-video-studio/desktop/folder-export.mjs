import { mkdir, open, readFile, writeFile, stat, unlink } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export class FolderExports {
  constructor({ userData, chooseDirectory, openDirectory }) {
    this.config = path.join(userData, 'export-directory.json');
    this.choose = chooseDirectory; this.openDirectory = openDirectory;
    this.root = null; this.sessions = new Map(); this.choosing = null;
  }
  async ensureDirectory(change = false) {
    if (!change && !this.root) {
      try { const saved = JSON.parse(await readFile(this.config, 'utf8')); if (typeof saved.directory === 'string') this.root = saved.directory; } catch {}
    }
    if (!change && this.root && await stat(this.root).then(value => value.isDirectory()).catch(() => false)) return { cancelled: false, name: path.basename(this.root) };
    if (!this.choosing) this.choosing = (async () => {
      const selected = await this.choose(this.root);
      if (!selected) return { cancelled: true };
      if (!await stat(selected).then(value => value.isDirectory()).catch(() => false)) throw new Error('Thư mục lưu không tồn tại.');
      this.root = selected;
      await writeFile(this.config, JSON.stringify({ directory: selected }), { mode: 0o600 });
      return { cancelled: false, name: path.basename(selected) };
    })().finally(() => { this.choosing = null; });
    return this.choosing;
  }
  async begin(data) {
    if (!data || !['image','video'].includes(data.kind) || !/^[a-f0-9]{32}$/.test(data.namespace) || !/^\d{1,100}$/.test(data.first) || !/^\d{1,100}$/.test(data.last) || !Number.isInteger(data.count) || data.count < 1 || data.count > 10 || BigInt(data.last) - BigInt(data.first) + 1n !== BigInt(data.count)) throw new Error('Bộ tệp xuất không hợp lệ.');
    if (this.sessions.size >= 2 || !this.root) throw new Error('Chọn thư mục lưu và đợi lượt lưu hiện tại hoàn tất.');
    const label = `Muse-${data.kind === 'image' ? 'Images' : 'Videos'}-${data.count}-${data.first}-${data.last}-${data.namespace}`;
    let directory;
    for (let suffix = 0; suffix < 100; suffix++) {
      const candidate = path.join(this.root, label + (suffix ? `-${suffix+1}` : ''));
      try { await mkdir(candidate); directory = candidate; break; } catch (error) { if (error.code !== 'EEXIST') throw error; }
    }
    if (!directory) throw new Error('Chưa tạo được thư mục mới để giữ riêng bộ kết quả.');
    const id = randomUUID();
    this.sessions.set(id, { ...data, directory, files: new Set(), pending: new Set() });
    return { id, name: path.basename(directory) };
  }
  async write({ id, name, bytes } = {}) {
    const task = this.sessions.get(id);
    const match = typeof name === 'string' && name.match(/^(?:kiem-thu-)?(image|video)-(\d+)-scene-(0[1-9]|10)-([a-f0-9]{32})\.(png|mp4|webm|mov)$/);
    if (!task || !match || match[1] !== task.kind || match[4] !== task.namespace || (task.kind === 'image' && match[5] !== 'png') || BigInt(match[2]) < BigInt(task.first) || BigInt(match[2]) > BigInt(task.last) || !(bytes instanceof ArrayBuffer) || !bytes.byteLength || bytes.byteLength > 150 * 1024 * 1024 || task.files.has(name) || task.pending.has(name) || task.files.size + task.pending.size >= task.count) throw new Error('Tệp xuất không hợp lệ hoặc bị trùng.');
    task.pending.add(name);
    const filename = path.join(task.directory, name);
    let handle; let complete = false;
    try {
      handle = await open(filename, 'wx', 0o600);
      await handle.writeFile(Buffer.from(bytes)); complete = true; task.files.add(name);
    } finally {
      await handle?.close();
      if (handle && !complete) await unlink(filename).catch(() => {});
      task.pending.delete(name);
    }
  }
  async finish(id) {
    const task = this.sessions.get(id);
    if (!task || task.pending.size || task.files.size !== task.count) throw new Error('Bộ kết quả chưa lưu đủ tệp.');
    this.sessions.delete(id);
    await this.openDirectory(task.directory).catch(() => {});
    return { directory: task.directory, count: task.count };
  }
  abort(id) { this.sessions.delete(id); }
}

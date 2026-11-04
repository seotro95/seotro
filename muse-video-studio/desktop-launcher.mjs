import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const root = path.dirname(fileURLToPath(import.meta.url));
if (!existsSync(path.join(root, 'node_modules', 'electron', 'path.txt'))) {
  console.log('Dang cai runtime dang nhap tich hop. Lan dau can Internet; khong can cai Chrome.');
  const installer = spawn(process.execPath, [require.resolve('electron/install.js')], { stdio: 'inherit', env: { ...process.env, ELECTRON_GET_USE_PROXY: '1' } });
  const result = await new Promise((resolve, reject) => { installer.once('error', reject); installer.once('exit', resolve); });
  if (result !== 0) { process.exitCode = 1; throw new Error('Khong tai duoc Electron. Kiem tra mang roi chay lai start.bat.'); }
}
const executable = require('electron');
const child = spawn(executable, [path.join(root, 'desktop', 'main.mjs'), ...process.argv.slice(2)], { cwd: root, stdio: 'inherit', windowsHide: false });
child.once('error', error => { console.error(error.message); process.exitCode = 1; });
child.once('exit', code => { process.exitCode = code ?? 1; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));

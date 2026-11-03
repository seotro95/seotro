import { spawn } from 'node:child_process';
import path from 'node:path';

export function browserCommand(url, platform = process.platform, systemRoot = process.env.SystemRoot) {
  const target = new URL(url);
  if (target.protocol !== 'http:' || target.hostname !== '127.0.0.1' || target.username || target.password) throw new Error('Only the local workstation can be opened.');
  if (platform === 'win32') return [systemRoot ? path.win32.join(systemRoot, 'System32', 'rundll32.exe') : 'rundll32.exe', ['url.dll,FileProtocolHandler', target.href]];
  return platform === 'darwin' ? ['open', [target.href]] : ['xdg-open', [target.href]];
}

export function openBrowser(url) {
  const [command, args] = browserCommand(url);
  const child = spawn(command, args, { stdio: 'ignore', windowsHide: true });
  const fallback = () => console.log(`Khong mo duoc trinh duyet tu dong. Mo thu cong: ${url}`);
  child.once('error', fallback);
  child.once('exit', code => { if (code) fallback(); });
  child.unref();
}

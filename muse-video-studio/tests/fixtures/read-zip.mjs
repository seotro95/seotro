import { execFileSync } from 'node:child_process';

// Validate exported ZIPs with an independent, standard-library reader.
export function readZip(filename) {
  const output = execFileSync('python3', ['-c', `
import base64,json,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    assert z.testzip() is None
    assert all(not (info.flag_bits & 1) for info in z.infolist())
    print(json.dumps([{'name':info.filename,'base64':base64.b64encode(z.read(info)).decode()} for info in z.infolist()]))
`, filename], { maxBuffer: 50 * 1024 * 1024 });
  return JSON.parse(output.toString()).map(entry => ({ name: entry.name, bytes: Buffer.from(entry.base64, 'base64') }));
}

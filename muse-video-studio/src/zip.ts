type ZipFile = { name: string; blob: Blob };
const crcTable = Uint32Array.from({ length: 256 }, (_, index) => {
  let crc = index;
  for (let bit = 0; bit < 8; bit++) crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  return crc >>> 0;
});
async function crc32(blob: Blob) {
  const reader = blob.stream().getReader();
  let crc = 0xffffffff;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const byte of value) crc = crcTable[(crc ^ byte) & 255] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
  } finally { reader.releaseLock(); }
}

// Media is already compressed. Store the original files in a standard ZIP,
// reading CRCs in chunks instead of duplicating all media in one byte array.
export async function createZip(files: ZipFile[]): Promise<Blob> {
  const local: BlobPart[] = [];
  const central: BlobPart[] = [];
  const names = new Set<string>();
  const encoder = new TextEncoder();
  let offset = 0; let centralSize = 0;
  const now = new Date();
  const date = (Math.min(2107, Math.max(1980, now.getFullYear())) - 1980) << 9 | (now.getMonth() + 1) << 5 | now.getDate();
  const time = now.getHours() << 11 | now.getMinutes() << 5 | now.getSeconds() >> 1;
  if (files.length > 65535) throw new Error('Có quá nhiều tệp để tạo ZIP.');
  for (const file of files) {
    if (!/^[a-zA-Z0-9_-][a-zA-Z0-9._-]*$/.test(file.name) || names.has(file.name)) throw new Error('Tên tệp ZIP không hợp lệ hoặc bị trùng.');
    names.add(file.name);
    const name = encoder.encode(file.name);
    if (name.length > 65535 || file.blob.size >= 0xffffffff || offset + 30 + name.length + file.blob.size >= 0xffffffff) throw new Error('Bộ kết quả vượt giới hạn ZIP 4 GB.');
    const crc = await crc32(file.blob);
    const header = new Uint8Array(30); const h = new DataView(header.buffer);
    h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x800, true);
    h.setUint16(10, time, true); h.setUint16(12, date, true); h.setUint32(14, crc, true);
    h.setUint32(18, file.blob.size, true); h.setUint32(22, file.blob.size, true); h.setUint16(26, name.length, true);
    local.push(header, name, file.blob);
    const directory = new Uint8Array(46); const d = new DataView(directory.buffer);
    d.setUint32(0, 0x02014b50, true); d.setUint16(4, 20, true); d.setUint16(6, 20, true); d.setUint16(8, 0x800, true);
    d.setUint16(12, time, true); d.setUint16(14, date, true); d.setUint32(16, crc, true);
    d.setUint32(20, file.blob.size, true); d.setUint32(24, file.blob.size, true); d.setUint16(28, name.length, true); d.setUint32(42, offset, true);
    central.push(directory, name); centralSize += directory.length + name.length;
    offset += header.length + name.length + file.blob.size;
  }
  if (offset + centralSize >= 0xffffffff) throw new Error('Bộ kết quả vượt giới hạn ZIP 4 GB.');
  const end = new Uint8Array(22); const e = new DataView(end.buffer);
  e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true);
  e.setUint32(12, centralSize, true); e.setUint32(16, offset, true);
  return new Blob([...local, ...central, end], { type: 'application/zip' });
}

export type DownloadRange = { first: bigint; last: bigint; namespace: string };

// A read/write transaction reserves the entire range atomically, including
// across Studio tabs. Decimal strings keep numbering exact beyond 1,000 and
// Number.MAX_SAFE_INTEGER. The profile ID distinguishes fresh installations.
export async function reserveDownloadNumbers(count: number): Promise<DownloadRange> {
  if (!Number.isInteger(count) || count < 1 || count > 10) throw new Error('Mỗi lượt tải cần từ 1 đến 10 tệp.');
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('muse-studio-downloads-v1', 1);
    let abandoned = false;
    request.onupgradeneeded = () => request.result.createObjectStore('counters');
    request.onsuccess = () => { if (abandoned) request.result.close(); else resolve(request.result); };
    request.onerror = () => reject(new Error('Chưa đọc được bộ đếm tải trên máy. Thử tải lại sau khi kiểm tra quyền lưu dữ liệu.'));
    request.onblocked = () => { abandoned = true; reject(new Error('Bộ đếm tải đang bị khóa. Đóng cửa sổ tool cũ rồi thử lại.')); };
  });
  try {
    return await new Promise<DownloadRange>((resolve, reject) => {
      const tx = db.transaction('counters', 'readwrite');
      const store = tx.objectStore('counters');
      let range: DownloadRange | undefined;
      let failure: Error | undefined;
      tx.oncomplete = () => range ? resolve(range) : reject(new Error('Chưa cấp được số thứ tự tải.'));
      tx.onerror = tx.onabort = () => reject(failure || new Error('Chưa lưu được số thứ tự tải. Tool chưa tải tệp để tránh dùng lại số cũ.'));
      store.get('sequence').onsuccess = event => {
        try {
          const state = (event.target as IDBRequest).result ?? { last: '0', namespace: crypto.randomUUID().replaceAll('-', '') };
          if (typeof state.last !== 'string' || !/^(0|[1-9]\d*)$/.test(state.last) || typeof state.namespace !== 'string' || !/^[a-f0-9]{32}$/.test(state.namespace)) throw new Error('Bộ đếm tải không hợp lệ. Tool giữ dữ liệu và không tự đặt lại số để tránh trùng tệp.');
          const first = BigInt(state.last) + 1n; const last = first + BigInt(count) - 1n;
          range = { first, last, namespace: state.namespace };
          store.put({ last: String(last), namespace: state.namespace }, 'sequence');
        } catch (e) { failure = e instanceof Error ? e : new Error(String(e)); tx.abort(); }
      };
    });
  } finally { db.close(); }
}

export const formatDownloadNumber = (value: bigint) => String(value).padStart(6, '0');

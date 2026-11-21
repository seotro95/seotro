import type { MediaResult, Settings } from './core.ts';

export type SavedMedia = { batchId?: string; id: string; sceneId: number; prompt: string; createdAt: string; persisted: boolean; media: MediaResult; settings?: Settings; referenceId?: string };
type StoredMedia = Omit<SavedMedia, 'media'> & { media: Omit<MediaResult, 'url'> };

async function database() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('muse-studio-media-v1', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('results', { keyPath: 'id' });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Không mở được kho kết quả trên máy.'));
    request.onblocked = () => reject(new Error('Kho kết quả đang mở ở phiên bản khác. Đóng cửa sổ tool cũ rồi mở lại.'));
  });
}

async function write(action: (store: IDBObjectStore) => void) {
  const db = await database();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('results', 'readwrite');
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => reject(tx.error || new Error('Không lưu được kết quả trên máy.'));
      action(tx.objectStore('results'));
    });
  } finally { db.close(); }
}

export async function saveMedia(entry: SavedMedia) {
  const { url: _url, ...media } = entry.media;
  await write(store => store.put({ ...entry, persisted: true, media } satisfies StoredMedia));
}

export async function loadMedia(): Promise<SavedMedia[]> {
  const db = await database();
  try {
    const entries = await new Promise<StoredMedia[]>((resolve, reject) => {
      const request = db.transaction('results', 'readonly').objectStore('results').getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return entries.sort((a, b) => b.createdAt.localeCompare(a.createdAt)).map(entry => {
      const bytes = Uint8Array.from(atob(entry.media.base64), ch => ch.charCodeAt(0));
      return { ...entry, persisted: true, media: { ...entry.media, savedId: entry.id, url: URL.createObjectURL(new Blob([bytes], { type: entry.media.mimeType })) } };
    });
  } finally { db.close(); }
}

export const deleteMedia = (id: string) => write(store => store.delete(id));

export const clearMedia = () => write(store => store.clear());

// Delete every persisted video version, including batches and scene slots that
// are not currently visible. A single transaction keeps images and all videos
// intact if any delete fails; callers publish their new view only after commit.
export async function deleteVideoMedia(): Promise<string[]> {
  const db = await database();
  try {
    return await new Promise<string[]>((resolve, reject) => {
      const tx = db.transaction('results', 'readwrite');
      const deletedIds: string[] = [];
      let cursorError: unknown;
      tx.oncomplete = () => resolve(deletedIds);
      tx.onabort = () => reject(cursorError || tx.error || new Error('Không xóa được video trong thư viện tool. Chưa thay đổi kết quả đã lưu.'));
      const request = tx.objectStore('results').openCursor();
      request.onerror = () => { cursorError = request.error; };
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        try {
          const entry = cursor.value as StoredMedia;
          if (entry.media.kind === 'video') { cursor.delete(); deletedIds.push(entry.id); }
          cursor.continue();
        } catch (error) { cursorError = error; tx.abort(); }
      };
    });
  } finally { db.close(); }
}

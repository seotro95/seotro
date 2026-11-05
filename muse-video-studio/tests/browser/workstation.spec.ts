import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { mockFolderPicker, exportedFolders } from '../fixtures/folders.ts';
const video = (await readFile(new URL('../../public/demo.mp4', import.meta.url))).toString('base64');
const image = (await readFile(new URL('../../public/demo-image.png', import.meta.url))).toString('base64');
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aO1sAAAAASUVORK5CYII=', 'base64');
test.beforeEach(async ({ page }) => { await mockFolderPicker(page.context()); await page.goto('/'); });
async function configureAdapter(page: Page) {
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'adapter', accounts: [], busy: false, credit: null, gpu: null } }));
  await page.reload();
}

test('clicking an image opens a decoded in-app viewer without a blank popup',async({page})=>{
  await configureAdapter(page);
  await page.route('**/api/image',route=>route.fulfill({json:{base64:image,mimeType:'image/png'}}));
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
  await page.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  let popups=0;page.on('popup',()=>popups++);
  await page.getByRole('button',{name:'Xem ảnh cảnh 1',exact:true}).click();
  const viewer=page.getByRole('dialog',{name:'Xem ảnh cảnh 1',exact:true});
  await expect(viewer.getByAltText('Ảnh lớn cảnh 1',{exact:true})).toBeVisible();
  expect(await viewer.locator('img').evaluate((image:HTMLImageElement)=>[image.complete,image.naturalWidth>0,image.naturalHeight>0])).toEqual([true,true,true]);
  await viewer.getByRole('button',{name:'Kích thước gốc',exact:true}).click();
  await expect(viewer.locator('.viewer-canvas')).toHaveClass(/natural/);
  const download=page.waitForEvent('download');await viewer.getByRole('button',{name:'Tải ảnh đang xem',exact:true}).click();
  expect((await download).suggestedFilename()).toMatch(/^image-000001-scene-01-/);
  await page.keyboard.press('Escape');await expect(viewer).toHaveCount(0);
  expect(popups).toBe(0);
});

test('editing, importing, changing modes and exporting remain available while mixed jobs keep their own snapshots',async({page})=>{
  await configureAdapter(page);
  const requests:any[]=[];const pending=new Map<string,()=>Promise<void>>();
  await page.route('**/api/image',async route=>{
    const data=route.request().postDataJSON();requests.push({kind:'image',...data});
    const finish=()=>route.fulfill({json:{base64:image,mimeType:'image/png'}});
    if(data.sceneId===1)await new Promise<void>(resolve=>pending.set('image',async()=>{await finish();resolve()}));else await finish();
  });
  await page.route('**/api/video',async route=>{
    requests.push({kind:'video',...route.request().postDataJSON()});
    await new Promise<void>(resolve=>pending.set('video',async()=>{await route.fulfill({json:{base64:video,mimeType:'video/mp4'}});resolve()}));
  });
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
  await page.getByTestId('scene-3').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect(page.getByTestId('scene-3').locator('.generated-image')).toBeVisible();
  const original=await page.getByLabel('Kịch bản cảnh 1',{exact:true}).inputValue();
  await page.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect.poll(()=>pending.has('image')).toBe(true);
  await page.getByRole('button',{name:'Tạo video',exact:true}).click();
  await page.getByLabel('Chất lượng',{exact:true}).selectOption('1080p');
  await page.getByLabel('Kịch bản cảnh 2',{exact:true}).fill('A separate video while an image is running');
  await page.getByTestId('scene-2').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect.poll(()=>pending.has('video')).toBe(true);
  expect(requests.find(data=>data.kind==='image'&&data.sceneId===1).resolution).toBe('2k');
  expect(requests.find(data=>data.kind==='video').resolution).toBe('1080p');
  await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
  await page.getByLabel('Nội dung TXT / SRT').fill('New prompt one\nNew prompt two\nNew prompt three');
  await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
  await expect(page.locator('.status-badge.running')).toHaveCount(2);
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
  const history=page.getByTestId('scene-3').locator('.media-history');await history.locator('summary').click();
  await history.getByRole('button',{name:'Xem bản 1 cảnh 3',exact:true}).click();
  await page.getByRole('button',{name:'Tải tất cả (1/10)',exact:true}).click();
  await expect.poll(async()=>(await exportedFolders(page))[0]?.files.length).toBe(1);
  await expect(page.locator('.status-badge.running')).toHaveCount(2);
  await pending.get('video')!();await pending.get('image')!();
  await expect(page.locator('.status-badge.running')).toHaveCount(0);
  await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toHaveValue('New prompt one');
  expect(requests.find(data=>data.kind==='image'&&data.sceneId===1).prompt).toBe(original);
  await expect(page.getByTestId('scene-1').locator('.history-entry')).toHaveCount(1);
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toHaveCount(0);
});

test('AI Enhance can use another free scene while a video continues running',async({page})=>{
  await configureAdapter(page);
  let finishVideo:(()=>Promise<void>)|undefined;
  await page.route('**/api/video',async route=>{await new Promise<void>(resolve=>{finishVideo=async()=>{await route.fulfill({json:{base64:video,mimeType:'video/mp4'}});resolve()}})});
  await page.route('**/api/text',route=>route.fulfill({json:{text:'An enhanced second scene'}}));
  await page.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect.poll(()=>Boolean(finishVideo)).toBe(true);
  await page.getByTestId('scene-2').getByRole('button',{name:'AI Enhance',exact:true}).click();
  await expect(page.getByLabel('Kịch bản cảnh 2',{exact:true})).toHaveValue('An enhanced second scene');
  await expect(page.getByTestId('scene-1').locator('.status-badge')).toHaveText('Đang tạo');
  await finishVideo!();await expect(page.getByTestId('scene-1').locator('video')).toBeVisible();
});

test('an account waiting for an email code stays unverified and cannot submit paid generation requests',async({page})=>{
  const account={id:1,state:'awaiting_code',authenticated:false,sessionAuthenticated:false,active:true,connectionMessage:'Đang chờ xác nhận mã trên trang Muse. Tool giữ nguyên phiên.'};
  await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',embeddedLogin:true,accounts:[account]}}));
  const requests:string[]=[];
  page.on('request',request=>{if(/\/api\/(image|video|text)$/.test(request.url()))requests.push(request.url())});
  await page.reload();
  await expect(page.locator('.single-account-controls')).toContainText('Đang chờ mã xác nhận');
  await expect(page.getByRole('button',{name:'TẠO 10 VIDEO',exact:true})).toBeDisabled();
  await expect(page.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true})).toBeDisabled();
  expect(requests).toEqual([]);
});
async function seedDownloadSequence(page: Page, last: string) {
  await page.evaluate(last => new Promise<void>((resolve,reject) => {
    const request = indexedDB.open('muse-studio-downloads-v1',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('counters');
    request.onerror=()=>reject(request.error);
    request.onsuccess=()=>{
      const db=request.result; const tx=db.transaction('counters','readwrite');
      tx.objectStore('counters').put({last,namespace:'a'.repeat(32)},'sequence');
      tx.oncomplete=()=>{db.close();resolve()};tx.onerror=tx.onabort=()=>{db.close();reject(tx.error)};
    };
  }),last);
}

test('downloads reserve unique global numbers across image/video tabs, pass 1000 and preserve large integers exactly', async ({ page, context }) => {
  await configureAdapter(page);
  await page.route('**/api/image',route=>route.fulfill({json:{base64:image,mimeType:'image/png'}}));
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
  await page.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  const other=await context.newPage();
  await other.goto('/');await configureAdapter(other);
  await other.route('**/api/video',route=>route.fulfill({json:{base64:video,mimeType:'video/mp4'}}));
  await other.getByRole('button',{name:'Tạo video',exact:true}).click();
  await other.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
  await expect(other.getByTestId('scene-1').locator('video')).toBeVisible();
  await seedDownloadSequence(page,'999');
  const take=async (target:Page)=>{
    const event=target.waitForEvent('download');
    await target.getByRole('button',{name:'Tải cảnh 1',exact:true}).click();
    return await event;
  };
  const pair=await Promise.all([take(page),take(other)]);
  const numbers=pair.map(file=>Number(file.suggestedFilename().match(/^(?:image|video)-(\d+)-scene-/)![1])).sort((a,b)=>a-b);
  expect(numbers).toEqual([1000,1001]);
  expect(pair[0].suggestedFilename()).toMatch(/^image-00100[01]-scene-01-a{32}\.png$/);
  expect(pair[1].suggestedFilename()).toMatch(/^video-00100[01]-scene-01-a{32}\.mp4$/);
  await seedDownloadSequence(page,'9007199254740991');
  expect((await take(page)).suggestedFilename()).toBe(`image-9007199254740992-scene-01-${'a'.repeat(32)}.png`);
  expect((await take(page)).suggestedFilename()).toBe(`image-9007199254740993-scene-01-${'a'.repeat(32)}.png`);
});

for (const kind of ['image', 'video'] as const) {
  test(`one click saves all ten selected ${kind} results in a normal folder`, async ({ page }) => {
    await configureAdapter(page);
    const videoBytes = Buffer.concat([Buffer.from(video, 'base64'), Buffer.alloc(256 * 1024, 0x61)]);
    const colors = await page.evaluate(() => Array.from({ length: 10 }, (_, index) => {
      const canvas = document.createElement('canvas'); canvas.width=4; canvas.height=4;
      const ctx = canvas.getContext('2d')!; ctx.fillStyle=`rgb(${index * 20},30,70)`; ctx.fillRect(0,0,4,4);
      return canvas.toDataURL('image/webp').split(',')[1];
    }));
    await page.route(`**/api/${kind}`, route => {
      const id = route.request().postDataJSON().sceneId;
      return route.fulfill({ json: { base64: kind === 'image' ? colors[id - 1] : videoBytes.toString('base64'), mimeType: kind === 'image' ? 'image/webp' : 'video/mp4' } });
    });
    if (kind === 'image') await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
    await page.getByRole('button', { name: kind === 'image' ? 'TẠO 10 ẢNH' : 'TẠO 10 VIDEO', exact: true }).click();
    await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10');
    let downloads = 0; page.on('download', () => downloads++);
    await page.getByRole('button', { name: 'Tải tất cả (10/10)', exact: true }).click();
    await expect.poll(async()=> (await exportedFolders(page))[0]?.files.length).toBe(10);
    const folder=(await exportedFolders(page))[0];
    expect(folder.name).toMatch(kind==='image'?/^Muse-Images-10-000001-000010-[a-f0-9]{32}$/:/^Muse-Videos-10-000001-000010-[a-f0-9]{32}$/);
    const files=folder.files;
    const namespace = files[0].name.match(/-([a-f0-9]{32})\.[a-z0-9]+$/)![1];
    const expectedNames = (first: number) => Array.from({ length: 10 }, (_, index) => `${kind === 'image' ? 'image' : 'video'}-${String(first+index).padStart(6,'0')}-scene-${String(index+1).padStart(2,'0')}-${namespace}.${kind === 'image' ? 'png' : 'mp4'}`);
    expect(files.map((file: { name: string }) => file.name)).toEqual(expectedNames(1));
    for (const [index, file] of files.entries()) {
      if (kind === 'video') expect(file.bytes).toEqual(videoBytes);
      else {
        expect(file.bytes.subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));
        const equal = await page.evaluate(async ({ actual, source }) => {
          async function pixels(src: string) {
            const image = new Image(); await new Promise<void>((resolve,reject) => { image.onload=()=>resolve();image.onerror=reject;image.src=src; });
            const canvas = document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
            const ctx=canvas.getContext('2d')!;ctx.drawImage(image,0,0);
            return [image.naturalWidth,image.naturalHeight,...ctx.getImageData(0,0,image.naturalWidth,image.naturalHeight).data];
          }
          return JSON.stringify(await pixels('data:image/png;base64,'+actual))===JSON.stringify(await pixels('data:image/webp;base64,'+source));
        }, { actual: file.bytes.toString('base64'), source: colors[index] });
        expect(equal).toBe(true);
      }
    }
    await expect(page.getByRole('button', { name: 'Tải tất cả (10/10)', exact: true })).toBeEnabled();
    expect(downloads).toBe(0);
    const archiveNames = new Set([folder.name]);
    const mediaNames = new Set(files.map((file: { name: string }) => file.name));
    for (const first of [11,21]) {
      if (first === 21) await page.reload();
      const count=(await exportedFolders(page)).length;
      await page.getByRole('button', { name: 'Tải tất cả (10/10)', exact: true }).click();
      await expect.poll(async()=> (await exportedFolders(page))[count]?.files.length).toBe(10);
      const next=(await exportedFolders(page))[count];
      expect(archiveNames.has(next.name)).toBe(false); archiveNames.add(next.name);
      const exported = next.files;
      expect(exported.map((file: { name: string }) => file.name)).toEqual(expectedNames(first));
      for (const file of exported) { expect(mediaNames.has(file.name)).toBe(false); mediaNames.add(file.name); }
    }
    expect(mediaNames.size).toBe(30);
    expect(downloads).toBe(0);
  });
}

test('batch download includes only completed selected scenes and their real scene numbers', async ({ page }) => {
  await configureAdapter(page);
  await page.route('**/api/image', route => route.fulfill({ json: { base64: image, mimeType: 'image/png' } }));
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  for (const id of [2,7]) {
    await page.getByTestId(`scene-${id}`).getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
    await expect(page.getByTestId(`scene-${id}`).locator('.generated-image')).toBeVisible();
  }
  await page.getByRole('button', { name: 'Tải tất cả (2/10)', exact: true }).click();
  await expect.poll(async()=> (await exportedFolders(page))[0]?.files.length).toBe(2);
  const files=(await exportedFolders(page))[0].files;
  expect(files[0].name).toMatch(/^image-000001-scene-02-[a-f0-9]{32}\.png$/);
  expect(files[1].name).toMatch(/^image-000002-scene-07-[a-f0-9]{32}\.png$/);
});

test('each scene can start during another render; stopping one leaves the other running', async ({ page }) => {
  await configureAdapter(page);
  const pending = new Map<number, () => Promise<void>>();
  const calls: number[] = [];
  await page.route('**/api/video', async route => {
    const id = route.request().postDataJSON().sceneId;
    calls.push(id);
    await new Promise<void>(resolve => pending.set(id, async () => {
      await route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }).catch(() => {}); resolve();
    }));
  });
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect.poll(() => calls).toEqual([1]);
  await expect(page.getByTestId('scene-2').getByRole('button', { name: 'Tạo cảnh này', exact: true })).toBeEnabled();
  await page.getByTestId('scene-2').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect.poll(() => calls).toEqual([1, 2]);
  await page.getByRole('button', { name: 'Dừng cảnh 1', exact: true }).click();
  await expect(page.getByTestId('scene-1').locator('.status-badge')).toHaveText('Đã dừng');
  await expect(page.getByTestId('scene-2').locator('.status-badge')).toHaveText('Đang tạo');
  await pending.get(2)!();
  await expect(page.getByTestId('scene-2').locator('video')).toBeVisible();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible();
  await pending.get(1)!();
  expect(calls).toEqual([1, 2]);
});

test('cancelling one queued scene sends no request and does not cancel the rest', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', executionConcurrency: 1, accounts: [account] } }));
  const calls: number[] = [];
  let first: (() => Promise<void>) | undefined;
  await page.route('**/api/image', async route => {
    const id = route.request().postDataJSON().sceneId; calls.push(id);
    const finish = () => route.fulfill({ json: { base64: image, mimeType: 'image/png' } });
    if (id === 1) await new Promise<void>(resolve => { first = async () => { await finish(); resolve(); }; });
    else await finish();
  });
  await page.reload();
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
  await expect(page.locator('.status-badge.running')).toHaveCount(1);
  await expect(page.locator('.status-badge.queued')).toHaveCount(9);
  await page.getByRole('button', { name: 'Dừng cảnh 5', exact: true }).click();
  await expect(page.getByTestId('scene-5').locator('.status-badge')).toHaveText('Đã dừng');
  expect(calls).toEqual([1]);
  await first!();
  await expect(page.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true })).toBeVisible();
  await expect.poll(()=>calls).toEqual([1,2,3,4,6,7,8,9,10]);
  await expect(page.locator('.generated-image')).toHaveCount(9);
  await page.getByTestId('scene-5').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10');
  expect(calls.at(-1)).toBe(5);
});

test('parallel selection uses an explicit capability check and reports an unsupported shared conversation', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true };
  let lanes = 1; const checks: number[] = []; let renders = 0;
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', executionConcurrency: lanes, accounts: [account] } }));
  await page.route('**/api/account/concurrency', route => {
    const count = route.request().postDataJSON().concurrency; checks.push(count);
    if (count === 10) { lanes = 10; return route.fulfill({ json: { executionConcurrency: 10, message: 'Đã kiểm tra 10 địa chỉ hội thoại riêng. Chưa render nội dung.' } }); }
    lanes = 1; return route.fulfill({ status: 409, json: { error: 'MUSE_PARALLEL_UNVERIFIED: Không có hội thoại riêng.' } });
  });
  await page.route('**/api/image', route => { renders++; return route.abort(); });
  await page.reload();
  await page.getByLabel('Số luồng:', { exact: true }).selectOption('10');
  await expect(page.getByLabel('Số luồng:', { exact: true })).toHaveValue('10');
  await expect(page.locator('.composer-feedback')).toContainText('10 địa chỉ');
  await page.getByLabel('Số luồng:', { exact: true }).selectOption('2');
  await expect(page.getByLabel('Số luồng:', { exact: true })).toHaveValue('1');
  await expect(page.locator('.composer-feedback')).toContainText('Chưa xác minh');
  expect(checks).toEqual([10, 2]); expect(renders).toBe(0);
});

test('each scene retains previous images and videos across reload, lets users select/download/delete a specific result', async ({ page }) => {
  await configureAdapter(page);
  const colors = await page.evaluate(() => ['red','blue','green'].map(color => { const canvas = document.createElement('canvas'); canvas.width = 4; canvas.height = 4; const ctx = canvas.getContext('2d')!; ctx.fillStyle = color; ctx.fillRect(0,0,4,4); return canvas.toDataURL('image/png').split(',')[1]; }));
  let images = 0; let videos = 0;
  await page.route('**/api/image', route => route.fulfill({ json: { base64: colors[images++], mimeType: 'image/png' } }));
  await page.route('**/api/video', route => { videos++; return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  const scene = page.getByTestId('scene-1');
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('First red image');
  await scene.getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(scene.locator('.history-entry')).toHaveCount(1);
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('Second blue image');
  await scene.getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(scene.locator('.history-entry')).toHaveCount(2);
  await scene.screenshot({ path: 'test-results/scene-saved-history.png' });
  await scene.getByRole('button', { name: 'Xem bản 1 cảnh 1', exact: true }).click();
  const download = page.waitForEvent('download');
  await scene.getByRole('button', { name: 'Tải bản 1 cảnh 1', exact: true }).click();
  const file = await download;
  const bytes = await readFile((await file.path())!);
  expect(bytes.subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));
  const selectedPixel = () => scene.locator('.generated-image').evaluate((image: HTMLImageElement) => { const canvas = document.createElement('canvas'); canvas.width=4;canvas.height=4; const ctx=canvas.getContext('2d')!;ctx.drawImage(image,0,0);return [...ctx.getImageData(0,0,1,1).data]; });
  expect(await selectedPixel()).toEqual([255,0,0,255]);
  await page.reload();
  await expect(scene.locator('.history-entry')).toHaveCount(2);
  expect(await selectedPixel()).toEqual([0,0,255,255]);
  await page.getByRole('button', { name: 'Tạo video', exact: true }).click();
  await scene.getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(scene.locator('video')).toBeVisible();
  await page.reload();
  await expect(scene.locator('video')).toBeVisible();
  await expect(scene.locator('.history-entry')).toHaveCount(1);
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await expect(scene.locator('.history-entry')).toHaveCount(2);
  await scene.getByRole('button', { name: 'Xem bản 1 cảnh 1', exact: true }).click();
  expect(await selectedPixel()).toEqual([255,0,0,255]);
  await scene.getByRole('button', { name: 'Xóa bản 2 cảnh 1', exact: true }).click();
  await expect(scene.locator('.history-entry')).toHaveCount(1);
  await page.reload();
  await expect(scene.locator('.history-entry')).toHaveCount(1);
  await expect(scene.locator('.generated-image')).toHaveCount(0);
  await scene.locator('.media-history summary').click();
  await scene.getByRole('button', { name: 'Xem bản 1 cảnh 1', exact: true }).click();
  expect(await selectedPixel()).toEqual([255,0,0,255]);
  for (let id=2; id<=10; id++) await page.getByRole('checkbox', { name: `Bật cảnh ${id}`, exact: true }).uncheck();
  await page.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
  await expect(scene.locator('.history-entry')).toHaveCount(2);
  expect(images).toBe(3); expect(videos).toBe(1);
  expect(await selectedPixel()).toEqual([0,128,0,255]);
});

test('matches 10-slot layout on desktop and remains within mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1433, height: 1000 });
  await expect(page.locator('.scene-card')).toHaveCount(10);
  expect(await page.locator('.scene-grid').evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(5);
  await expect(page.getByLabel('Model AI')).toHaveValue('Omni 1.1 Flash');
  await page.screenshot({ path: 'test-results/desktop.png', fullPage: true });
  await page.getByLabel('Model AI').selectOption('Veo 3.1 - Fast');
  await expect(page.getByLabel('Thời lượng')).toHaveValue('8');
  await expect(page.getByLabel('Chất lượng')).toHaveValue('720p');
  await page.getByLabel('Chất lượng').selectOption('4k');
  await expect(page.getByLabel('Chất lượng')).toHaveValue('4k');
  await expect(page.getByLabel('Thời lượng')).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/mobile.png', fullPage: true });
});

test('imports SRT, rejects overflow, preserves raw text, and persists prompts', async ({ page }) => {
  await page.getByRole('button', { name: 'Nhập TXT / SRT' }).click();
  await page.getByLabel('Nội dung TXT / SRT').fill(Array.from({ length: 11 }, (_, i) => `Scene ${i}`).join('\n'));
  await expect(page.getByRole('button', { name: 'Nạp vào Studio', exact: true })).toBeDisabled();
  await page.getByLabel('Nội dung TXT / SRT').fill('1\n00:00:00,000 --> 00:00:04,000\nCảnh một\n\n2\n00:00:04,000 --> 00:00:08,000\nCảnh hai');
  await page.getByRole('button', { name: 'Nạp vào Studio', exact: true }).click();
  await expect(page.getByLabel('Kịch bản cảnh 1', { exact: true })).toHaveValue('Cảnh một');
  await expect(page.getByLabel('Kịch bản cảnh 3', { exact: true })).toHaveValue('');
  await page.reload();
  await expect(page.getByLabel('Kịch bản cảnh 2', { exact: true })).toHaveValue('Cảnh hai');
});

test('global image sync, per-scene override and manual reapply', async ({ page }) => {
  const upload = async (button: string, name: string) => {
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: button, exact: true }).click();
    await (await chooser).setFiles({ name, mimeType: 'image/png', buffer: png });
  };
  await upload('Tải ảnh nhân vật chung', 'global.png');
  await expect(page.locator('.scene-image')).toHaveCount(10);
  await upload('Đổi ảnh cảnh 1', 'private.png');
  await expect(page.getByTestId('scene-1').getByText('Ảnh riêng', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Áp dụng cho 10 cảnh' }).click();
  await expect(page.getByTestId('scene-1').getByText('Ảnh chung · đã đồng bộ')).toBeVisible();
  await page.getByRole('button', { name: 'Gỡ ảnh cảnh 2', exact: true }).click();
  await expect(page.getByTestId('scene-2').locator('.scene-image')).toHaveCount(0);
  await page.getByTestId('scene-2').getByRole('button', { name: 'Dùng ảnh chung' }).click();
  await expect(page.locator('.scene-image')).toHaveCount(10);
});

test('Muse contract sends accountId, settings, R2V and modifier; video plays and downloads', async ({ page }) => {
  await configureAdapter(page);
  let payload: Record<string, any> = {};
  await page.route('**/api/video', async route => { payload = route.request().postDataJSON(); await route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Tải ảnh nhân vật chung' }).click();
  await (await chooser).setFiles({ name: 'ref.png', mimeType: 'image/png', buffer: png });
  await expect(page.locator('.scene-image')).toHaveCount(10);
  await page.getByRole('button', { name: 'Tài khoản Muse', exact: true }).click();
  await page.getByLabel('Chỉ thị chất lượng toàn cục', { exact: false }).fill('cinematic lighting');
  await page.getByRole('button', { name: 'Hoàn tất', exact: true }).click();
  await page.getByTestId('scene-2').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-2').locator('video')).toBeVisible();
  expect(payload.accountId).toBe(1);
  expect(payload.prompt).toContain('cinematic lighting');
  expect(payload.image.mimeType).toBe('image/png');
  expect(payload.model).toBe('Omni 1.1 Flash');
  await expect.poll(async () => page.getByTestId('scene-2').locator('video').evaluate((v: HTMLVideoElement) => v.readyState)).toBeGreaterThan(0);
  expect(await page.getByTestId('scene-2').locator('video').evaluate((v: HTMLVideoElement) => v.duration)).toBeCloseTo(4, 0);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải cảnh 2', exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^video-000001-scene-02-[a-f0-9]{32}\.mp4$/);
  await page.getByLabel('Kịch bản cảnh 2', { exact: true }).fill('Changed prompt');
  await expect(page.getByTestId('scene-2').locator('video')).toHaveCount(0);
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
});

test('batch runs enabled scenes concurrently and keeps per-scene failures', async ({ page }) => {
  test.setTimeout(60000);
  await configureAdapter(page);
  const calls: number[] = []; let active = 0; let peak = 0;
  const barrier: (() => void)[] = [];
  await page.route('**/api/video', async route => {
    const id = route.request().postDataJSON().accountId; calls.push(id); const index = calls.length; active++; peak = Math.max(peak, active);
    await new Promise<void>(resolve => barrier.push(resolve)); active--;
    await route.fulfill(index === 2 ? { status: 429, json: { error: '429 quota exceeded' } } : { json: { base64: video, mimeType: 'video/mp4' } });
  });
  await page.getByRole('checkbox', { name: 'Bật cảnh 2', exact: true }).uncheck();
  await page.getByRole('button', { name: 'TẠO 10 VIDEO' }).click();
  await expect.poll(() => calls.length).toBe(9);
  await expect(page.locator('.status-badge.running')).toHaveCount(9);
  expect(peak).toBe(9);
  for (const release of barrier) release();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '8', { timeout: 20000 });
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible({ timeout: 10000 });
  expect(calls).toEqual(Array(9).fill(1)); expect(peak).toBe(9);
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '8');
  await expect(page.getByTestId('scene-3').getByText('Kiểm tra hạn mức', { exact: false })).toBeVisible();
  await page.getByTestId('scene-3').getByText('Mã lỗi gốc').click();
  await expect(page.getByTestId('scene-3').locator('pre')).toContainText('429 quota exceeded');
});

test('demo batch can be stopped and resumed; test clips are labelled', async ({ page }) => {
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.getByLabel('Kết nối tạo video', { exact: true }).selectOption('demo');
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1');
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible();
  await page.getByRole('button', { name: 'TẠO 10 VIDEO' }).click();
  await expect(page.locator('.status-badge.running')).toHaveCount(9);
  await page.getByRole('button', { name: 'Dừng tất cả luồng' }).click();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible();
  await expect(page.locator('.status-badge.queued')).toHaveCount(0);
  const count = await page.locator('.scene-card video').count();
  expect(count).toBeGreaterThan(0); expect(count).toBeLessThan(10);
  await expect(page.locator('.preview-label').first()).toHaveText('CLIP KIỂM THỬ');
  await page.getByRole('button', { name: 'TẠO 10 VIDEO' }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 15000 });
});

test('missing integration is explained before render and sends no doomed AI requests', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', request => { if (/\/api\/(video|text)$/.test(request.url())) requests.push(request.url()); });
  await expect(page.getByRole('region', { name: 'Cần kết nối tạo video' })).toContainText('Đăng nhập một tài khoản Muse');
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeDisabled();
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'AI Enhance' })).toBeDisabled();
  await expect(page.locator('video')).toHaveCount(0);
  await page.getByRole('button', { name: 'Kết nối tài khoản Muse', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Quản lý tài khoản Muse' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mở cửa sổ Muse', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Hoàn tất', exact: true }).click();
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await expect(page.locator('#provider-mode option')).toHaveCount(2);
  expect(await page.locator('#provider-mode option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))).toEqual(['muse', 'demo']);
  await expect(page.getByRole('button', { name: 'Kiểm tra render thực tế' })).toBeDisabled();
  expect(requests).toEqual([]);
});

test('Enhance uses the single Muse account; diagnostic never renders without explicit consent', async ({ page }) => {
  await configureAdapter(page);
  let textPayload: any; let renders = 0; let videoPayload: any;
  await page.route('**/api/text', async route => { textPayload = route.request().postDataJSON(); await route.fulfill({ json: { text: 'Cinematic tracking shot through an ancient temple at sunrise.' } }); });
  await page.route('**/api/video', async route => { renders++; videoPayload = route.request().postDataJSON(); await route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByTestId('scene-4').getByRole('button', { name: 'AI Enhance' }).click();
  await expect(page.getByLabel('Kịch bản cảnh 4', { exact: true })).toHaveValue('Cinematic tracking shot through an ancient temple at sunrise.');
  expect(textPayload.accountId).toBe(1);
  expect(textPayload.prompt).toContain('Rewrite this scene');
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Kiểm tra render thực tế' })).toBeDisabled();
  expect(renders).toBe(0);
  await page.getByRole('checkbox', { name: 'Tôi đồng ý gửi một yêu cầu render thử', exact: false }).check();
  await page.getByRole('button', { name: 'Kiểm tra render thực tế' }).click();
  await expect(page.locator('.diagnostic-result')).toContainText('hoàn tất');
  expect(renders).toBe(1);
  expect(videoPayload.duration).toBe(4); expect(videoPayload.resolution).toBe('360p');
  await expect(page.locator('.diagnostic-result')).toContainText('GPU: chưa có thông tin');
});

test('refreshing a newly configured adapter enables rendering without losing the script', async ({ page }) => {
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('Keep this script while connecting.');
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'adapter', accounts: [], busy: false, credit: null, gpu: null } }));
  await page.getByRole('button', { name: 'Đọc cấu hình', exact: true }).click();
  await expect(page.locator('.setup-help')).toHaveCount(0);
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeEnabled();
  await expect(page.getByLabel('Kịch bản cảnh 1', { exact: true })).toHaveValue('Keep this script while connecting.');
});

test('one login and one button create all ten videos using the same Muse account', async ({ page }) => {
  const account = { id: 1, state: 'disconnected', authenticated: false, active: false, checkedAt: null as string | null };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', accounts: [account], busy: false } }));
  await page.route('**/api/account/connect', route => { account.state = 'login_open'; account.active = true; return route.fulfill({ json: { accounts: [account] } }); });
  await page.route('**/api/account/check', route => { Object.assign(account, { state: 'ready', authenticated: true, checkedAt: new Date().toISOString() }); return route.fulfill({ json: { accounts: [account] } }); });
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4', metadata: { duration: 4, width: 640, height: 360 } } }); });
  await page.reload();
  await page.getByRole('button', { name: 'Kết nối Muse', exact: true }).click();
  await expect(page.locator('.single-account-controls')).toContainText('Chờ đăng nhập');
  await page.getByRole('button', { name: 'Kiểm tra phiên', exact: true }).click();
  await expect(page.locator('.single-account-controls')).toContainText('Đã xác minh');
  await expect(page.locator('.scene-account-picker, .account-inline, .account-list')).toHaveCount(0);
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 20000 });
  expect(calls).toEqual(Array(10).fill(1));
  await expect(page.getByTestId('scene-1').locator('.video-metadata')).toHaveText('Muse trả về: 640×360 · 4.0 giây');
  account.authenticated = false; account.state = 'login_open';
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.getByRole('button', { name: 'Đọc cấu hình', exact: true }).click();
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'Tạo lại cảnh' })).toBeDisabled();
  await expect(page.locator('.scene-card video')).toHaveCount(10);
});

test('a fixture advertising independent conversations can start ten image requests', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true, checkedAt: null };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', executionConcurrency: 10, accounts: [account], busy: false } }));
  const calls: number[] = [];
  const pending: (() => Promise<void>)[] = [];
  await page.route('**/api/image', async route => { calls.push(route.request().postDataJSON().accountId); await new Promise<void>(resolve => pending.push(async () => { await route.fulfill({ json: { base64: image, mimeType: 'image/png' } }); resolve(); })); });
  await page.reload();
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
  await expect.poll(() => calls.length).toBe(10);
  await expect(page.locator('.status-badge.running')).toHaveCount(10);
  await expect(page.locator('.generated-image')).toHaveCount(0);
  await Promise.all(pending.map(release => release()));
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 20000 });
  await expect(page.locator('.generated-image')).toHaveCount(10);
  expect(calls).toEqual(Array(10).fill(1));
  await expect(page.locator('.scene-account-picker, #shared-account, #email-bulk')).toHaveCount(0);
});

test('legacy account choices cannot route any of the ten scenes to another account', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('muse-workstation-v1', JSON.stringify({ version: 1, settings: { shareUnassigned: false, sharedAccountId: 8 }, scenes: Array.from({ length: 10 }, (_, i) => ({ prompt: `Legacy scene ${i + 1}`, accountId: i + 1, email: `old${i}@example.com`, enabled: true })) })));
  await configureAdapter(page);
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await expect(page.getByLabel('Kịch bản cảnh 10', { exact: true })).toHaveValue('Legacy scene 10');
  await expect(page.locator('.scene-account-picker, #shared-account, #email-bulk')).toHaveCount(0);
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 20000 });
  expect(calls).toEqual(Array(10).fill(1));
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('muse-workstation-v1')!));
  expect(saved.settings.sharedAccountId).toBeUndefined();
  expect(saved.scenes.every((scene: any) => scene.accountId === undefined && scene.email === undefined)).toBe(true);
});

test('imports a 4K image batch from SRT, follows independent prompts, and converts the images to 1080p video requests', async ({ page }) => {
  await configureAdapter(page);
  const imageCalls: any[] = []; const videoCalls: any[] = [];
  await page.route('**/api/image', route => { imageCalls.push(route.request().postDataJSON()); return route.fulfill({ json: { base64: image, mimeType: 'image/png', metadata: { width: 3840, height: 2160 } } }); });
  await page.route('**/api/video', route => { videoCalls.push(route.request().postDataJSON()); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4', metadata: { width: 640, height: 360, duration: 4 } } }); });
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByLabel('Độ nét ảnh', { exact: true }).selectOption('4k');
  await page.getByRole('checkbox', { name: 'Đồng nhất nhân vật', exact: true }).uncheck();
  await page.getByRole('button', { name: 'Nhập TXT / SRT', exact: true }).click();
  await page.getByLabel('Nội dung TXT / SRT').fill('1\n00:00:00,000 --> 00:00:04,000\nA person in a forest\n\n2\n00:00:04,000 --> 00:00:08,000\nA different person at sea');
  await page.getByRole('button', { name: 'Nạp & Chạy các cảnh', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');
  expect(imageCalls.map(c => c.prompt)).toEqual(['A person in a forest', 'A different person at sea']);
  expect(imageCalls.every(c => c.resolution === '4k' && c.characterLock === false && c.image === undefined)).toBe(true);
  await expect(page.getByTestId('scene-1').locator('.video-metadata')).toHaveText('Muse trả về: 640×360');
  await expect(page.getByTestId('scene-1').locator('.quality-result')).toHaveText('Chưa đạt yêu cầu 4K');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải cảnh 1', exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^image-000001-scene-01-[a-f0-9]{32}\.png$/);
  await page.getByRole('button', { name: 'Chuyển bộ ảnh đã tạo sang video' }).click();
  await expect(page.getByRole('button', { name: 'Từ ảnh', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByLabel('Chất lượng', { exact: true }).selectOption('1080p');
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');
  expect(videoCalls).toHaveLength(2);
  expect(videoCalls.every(c => c.sourceMode === 'image' && c.image.imageBytes === image && c.characterLock === false && c.resolution === '1080p')).toBe(true);
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await expect(page.locator('.generated-image')).toHaveCount(2);
});

test('character lock attaches the portrait; disabling it and editing the prompt regenerates independently', async ({ page }) => {
  await configureAdapter(page);
  const calls: any[] = [];
  await page.route('**/api/image', route => { calls.push(route.request().postDataJSON()); return route.fulfill({ json: { base64: image, mimeType: 'image/png' } }); });
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Tải ảnh nhân vật chung' }).click();
  await (await chooser).setFiles({ name: 'portrait.png', mimeType: 'image/png', buffer: png });
  await expect(page.locator('.scene-image')).toHaveCount(10);
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  expect(calls[0].image.imageBytes).toBe(png.toString('base64'));
  expect(calls[0].characterLock).toBe(true);
  await page.getByRole('checkbox', { name: 'Đồng nhất nhân vật', exact: true }).uncheck();
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('A new independent character');
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toHaveCount(0);
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  expect(calls[1].image).toBeUndefined(); expect(calls[1].characterLock).toBe(false);
  expect(calls[1].prompt).toBe('A new independent character');
});

test('balance panel shows an observed zero and distinguishes an unreadable balance', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true, checkedAt: null, balance: { valueText: '0', unit: 'token', label: 'Tokens remaining: 0', observedAt: new Date().toISOString(), source: 'muse-ui' } as any };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', accounts: [account], busy: false } }));
  await page.route('**/api/account/check', route => { account.balance = null; return route.fulfill({ json: { accounts: [account] } }); });
  await page.reload();
  await expect(page.getByTestId('account-balance')).toContainText('0 token');
  await page.getByRole('button', { name: 'Cập nhật số dư', exact: true }).click();
  await expect(page.getByTestId('account-balance')).toContainText('Chưa đọc được');
  await expect(page.getByTestId('account-balance')).not.toContainText('0 token');
});

test('large generated image is compressed only for video input while the original image is retained', async ({ page }) => {
  await configureAdapter(page);
  const largeImage = Buffer.concat([png, Buffer.alloc(9 * 1024 * 1024)]).toString('base64');
  await page.route('**/api/image', route => route.fulfill({ json: { base64: largeImage, mimeType: 'image/png' } }));
  let input: any;
  await page.route('**/api/video', route => { input = route.request().postDataJSON(); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Dùng ảnh này tạo video', exact: true }).click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('video')).toBeVisible();
  expect(input.image.mimeType).toBe('image/webp');
  expect(input.image.imageBytes.length).toBeLessThan(8 * 1024 * 1024 * 4 / 3);
  await expect(page.getByTestId('scene-1')).toContainText('Ảnh đầu vào đã nén dưới 8 MB; ảnh gốc được giữ.');
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
});

test('image-to-video batch only sends scenes that have a source frame', async ({ page }) => {
  await configureAdapter(page);
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByRole('button', { name: 'Từ ảnh', exact: true }).click();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeDisabled();
  const chooser = page.waitForEvent('filechooser');
  await page.getByTestId('scene-1').getByRole('button', { name: '+ Chọn ảnh nhân vật', exact: true }).click();
  await (await chooser).setFiles({ name: 'frame.png', mimeType: 'image/png', buffer: png });
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1');
  expect(calls).toEqual([1]);
  await expect(page.locator('.scene-error')).toHaveCount(0);
});

test('a verified Muse session enables generation even without a login-page composer', async ({ page }) => {
  const account = { id: 1, state: 'composer_loading', authenticated: false, sessionAuthenticated: true, composerReady: false, active: true,
    connectionMessage: 'Phiên Muse đã được xác minh. Tool mở ô soạn riêng khi bạn bấm tạo.', checkedAt: null };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', embeddedLogin: true, accounts: [account], busy: false } }));
  await page.route('**/api/account/check', route => route.fulfill({ json: { accounts: [account] } }));
  await page.reload();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeEnabled();
  await expect(page.locator('.connection-pill')).toContainText('Đã xác minh');
  await expect(page.locator('.connection-warning')).toHaveCount(0);
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(page.getByTestId('scene-1').locator('video')).toHaveCount(1);
  expect(calls).toEqual([1]);
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeVisible();
  account.state = 'check_failed'; account.sessionAuthenticated = false;
  account.connectionMessage = 'Không xác minh được phiên Muse (HTTP 503). Kiểm tra tab Muse rồi thử Kiểm tra phiên lại.';
  await page.getByRole('button', { name: 'Kiểm tra phiên', exact: true }).click();
  await expect(page.locator('.connection-feedback')).toContainText('HTTP 503');
  await page.getByLabel('Đóng thông báo', { exact: true }).click();
  await expect(page.locator('.connection-feedback')).toBeVisible();
  await expect(page.locator('.connection-feedback')).toContainText('HTTP 503');
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeDisabled();
});

test('Message diagnostics show a persistent failure without sending a render', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, sessionAuthenticated: true, composerReady: false, active: true };
  const renderCalls: string[] = [];
  page.on('request', request => { if (/\/api\/(image|video|text)$/.test(request.url())) renderCalls.push(request.url()); });
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', embeddedLogin: true, accounts: [account], busy: false } }));
  await page.route('**/api/account/composer', route => route.fulfill({ status: 504, json: { error: 'MUSE_COMPOSER_NOT_READY: Chưa gửi prompt. Chẩn đoán trang luồng: {"origin":"https://muse.ai","route":"/chat","visibleEditors":0}' } }));
  await page.reload();
  await page.getByRole('button', { name: 'Kiểm tra ô Message', exact: true }).click();
  await expect(page.locator('.composer-feedback')).toContainText('Chưa tìm được ô nhập Message');
  await page.locator('.composer-feedback').getByText('Chi tiết trang luồng', { exact: true }).click();
  await expect(page.locator('.composer-feedback pre')).toContainText('visibleEditors');
  await page.getByRole('button', { name: 'Tài khoản Muse', exact: true }).click();
  await expect(page.getByRole('dialog').locator('.composer-feedback')).toContainText('Chưa tìm được ô nhập Message');
  await page.getByRole('dialog').getByLabel('Đóng', { exact: true }).click();
  await expect(page.locator('.composer-feedback pre')).toBeVisible();
  expect(renderCalls).toEqual([]);
  await expect(page.locator('.status-badge.running')).toHaveCount(0);
});

test('Muse defaults to a queue: one scene runs, nine wait, and all ten use one batch', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', accounts: [account], busy: false } }));
  const calls: { accountId: number; batchId: string; sceneId: number }[] = [];
  const releases: (() => Promise<void>)[] = [];
  await page.route('**/api/image', async route => {
    calls.push(route.request().postDataJSON());
    await new Promise<void>(resolve => releases.push(async () => { await route.fulfill({ json: { base64: image, mimeType: 'image/png' } }); resolve(); }));
  });
  await page.reload();
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
  await expect.poll(() => calls.length).toBe(1);
  await expect(page.locator('.status-badge.running')).toHaveCount(1);
  await expect(page.locator('.status-badge.queued')).toHaveCount(9);
  for (let index = 0; index < 10; index++) {
    await expect.poll(() => releases.length).toBe(index + 1);
    await releases[index]();
    await expect(page.locator('.generated-image')).toHaveCount(index + 1);
  }
  expect(calls.map(call => call.accountId)).toEqual(Array(10).fill(1));
  expect(calls.map(call => call.sceneId)).toEqual([1,2,3,4,5,6,7,8,9,10]);
  expect(new Set(calls.map(call => call.batchId)).size).toBe(1);
});

test('downloading a WebP preview exports a decodable PNG file with the same pixels', async ({ page }) => {
  await configureAdapter(page);
  const webp = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 2; canvas.height = 2;
    const context = canvas.getContext('2d')!; context.fillStyle = '#123456'; context.fillRect(0,0,2,2);
    return canvas.toDataURL('image/webp', 1).split(',')[1];
  });
  await page.route('**/api/image', route => route.fulfill({ json: { base64: webp, mimeType: 'image/webp' } }));
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toHaveCount(1);
  const pixels = await page.getByTestId('scene-1').locator('.generated-image').evaluate(element => {
    const canvas = document.createElement('canvas'); canvas.width = 2; canvas.height = 2;
    const context = canvas.getContext('2d')!; context.drawImage(element as HTMLImageElement, 0, 0);
    return [...context.getImageData(0,0,2,2).data];
  });
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải cảnh 1', exact: true }).click();
  const result = await download;
  expect(result.suggestedFilename()).toMatch(/^image-000001-scene-01-[a-f0-9]{32}\.png$/);
  const bytes = await readFile((await result.path())!);
  expect([...bytes.subarray(0,8)]).toEqual([137,80,78,71,13,10,26,10]);
  const decoded = await page.evaluate(base64 => new Promise(resolve => {
    const img = new Image(); img.onload = () => {
      const canvas = document.createElement('canvas'); canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      const context = canvas.getContext('2d')!; context.drawImage(img,0,0);
      resolve({ dimensions: [img.naturalWidth, img.naturalHeight], pixels: [...context.getImageData(0,0,2,2).data] });
    }; img.onerror = () => resolve(null); img.src = 'data:image/png;base64,' + base64;
  }), bytes.toString('base64'));
  expect(decoded).toEqual({ dimensions: [2,2], pixels });
});

test('ten-account mode routes only verified slots, imports ten labels and preserves the shared-account option',async({page})=>{
  const accounts=Array.from({length:10},(_,i)=>({id:i+1,label:`Muse ${i+1}`,authenticated:i<9,sessionAuthenticated:i<9,active:i<9,state:i<9?'ready':'disconnected',checkedAt:null}));
  await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,embeddedLogin:true,executionConcurrency:1,maxConcurrency:10,accounts}}));
  await page.route('**/api/account/select',route=>route.fulfill({json:{accounts}}));
  let imported:string[]=[];
  await page.route('**/api/account/import',route=>{imported=route.request().postDataJSON().labels;return route.fulfill({json:{accounts:accounts.map((account,i)=>({...account,label:imported[i]}))}})});
  await page.reload();
  await page.getByRole('button',{name:'Quản lý 10 tài khoản',exact:true}).click();
  const manager=page.getByRole('dialog',{name:'Quản lý tài khoản Muse',exact:true});
  const labels=Array.from({length:10},(_,i)=>`owner${i+1}@example.invalid`);
  await manager.locator('input[type=file][accept=".txt"]').setInputFiles({name:'accounts.txt',mimeType:'text/plain',buffer:Buffer.from(labels.join('\r\n'))});
  await expect(manager.getByLabel('Danh sách 10 tài khoản',{exact:true})).toHaveValue(labels.join('\n'));
  await manager.getByRole('button',{name:'Lưu danh sách',exact:true}).click();await expect.poll(()=>imported.length).toBe(10);expect(imported).toEqual(labels);
  await manager.getByRole('button',{name:'Hoàn tất',exact:true}).click();
  await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
  const requests:any[]=[];const release:(()=>Promise<void>)[]=[];
  await page.route('**/api/image',async route=>{requests.push(route.request().postDataJSON());await new Promise<void>(resolve=>release.push(async()=>{await route.fulfill({json:{base64:image,mimeType:'image/png'}});resolve()}))});
  await page.getByRole('button',{name:'TẠO 10 ẢNH',exact:true}).click();await expect.poll(()=>requests.length).toBe(9);
  expect(requests.map(data=>data.accountId).sort((a,b)=>a-b)).toEqual([1,2,3,4,5,6,7,8,9]);expect(requests.every(data=>data.accountMode==='multiple'&&data.sceneId===data.accountId)).toBe(true);
  await expect(page.getByTestId('scene-10').getByText('Chưa xác minh Muse 10.',{exact:false})).toBeVisible();
  await expect(page.getByLabel('Chế độ tài khoản',{exact:true})).toBeDisabled();await expect(page.getByLabel('Kịch bản cảnh 10',{exact:true})).toBeEditable();
  for(const done of release)await done();await expect(page.locator('.generated-image')).toHaveCount(9);
  await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('single');await expect(page.getByLabel('Số luồng:',{exact:true})).toHaveValue('1');
  await page.reload();await expect(page.getByLabel('Chế độ tài khoản',{exact:true})).toHaveValue('single');
});

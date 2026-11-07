import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {mockFolderPicker,exportedFolders} from '../fixtures/folders.ts';
const image=(await readFile(new URL('../../public/demo-image.png',import.meta.url))).toString('base64');
const video=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');

test.beforeEach(async({page})=>{await mockFolderPicker(page.context());await page.goto('/')});

test('selecting 20, 30 and 40 streams renders exactly that many ordered slots, preserves hidden prompts and exposes matching accounts',async({page})=>{
  for(const count of [20,30,40]){
    await page.getByLabel('Số luồng:',{exact:true}).selectOption(String(count));
    await expect(page.locator('.scene-card')).toHaveCount(count);await expect(page.getByLabel('Số ô',{exact:true})).toHaveValue(String(count));
    await expect(page.locator('.scene-number').last()).toHaveText('#'+count);await expect(page.getByLabel(`Kịch bản cảnh ${count}`,{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:`TẠO ${count} VIDEO`,exact:true})).toBeVisible();
  }
  await page.getByLabel('Kịch bản cảnh 30',{exact:true}).fill('Retain this scene while hidden');
  await page.getByLabel('Số luồng:',{exact:true}).selectOption('20');await expect(page.getByLabel('Kịch bản cảnh 30',{exact:true})).toHaveCount(0);
  await page.getByLabel('Số luồng:',{exact:true}).selectOption('40');await expect(page.getByLabel('Kịch bản cảnh 30',{exact:true})).toHaveValue('Retain this scene while hidden');
  await page.reload();await expect(page.locator('.scene-card')).toHaveCount(40);await expect(page.getByLabel('Số luồng:',{exact:true})).toHaveValue('40');await expect(page.getByLabel('Kịch bản cảnh 30',{exact:true})).toHaveValue('Retain this scene while hidden');
  await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');await page.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();await expect(page.locator('.account-item')).toHaveCount(40);await expect(page.getByRole('button',{name:'Đăng nhập Muse 40',exact:true})).toBeVisible();
});

test('forty imported prompts generate all forty image and video slots and export forty ordinary files with continuous numbering',async({page})=>{
  test.setTimeout(90000);
  await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:40}}));await page.reload();
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();await page.getByLabel('Nội dung TXT / SRT',{exact:true}).fill(Array.from({length:40},(_,i)=>`Forty scene ${i+1}`).join('\n'));await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();await expect(page.locator('.scene-card')).toHaveCount(40);
  const calls:number[]=[];await page.route('**/api/image',route=>{calls.push(route.request().postDataJSON().sceneId);return route.fulfill({json:{base64:image,mimeType:'image/png'}})});await page.route('**/api/video',route=>route.fulfill({json:{base64:video,mimeType:'video/mp4'}}));
  await page.getByRole('button',{name:'TẠO 40 ẢNH',exact:true}).click();await expect(page.locator('.generated-image')).toHaveCount(40);expect(calls.slice().sort((a,b)=>a-b)).toEqual(Array.from({length:40},(_,i)=>i+1));
  await page.getByRole('button',{name:'Tải tất cả (40/40)',exact:true}).click();await expect.poll(async()=>(await exportedFolders(page))[0]?.files.length).toBe(40);const images=(await exportedFolders(page))[0];expect(images.files[39].name).toMatch(/^image-000040-scene-40-/);
  await page.reload();await expect(page.locator('.generated-image')).toHaveCount(40);await page.getByRole('button',{name:'Tạo video',exact:true}).click();await page.getByRole('button',{name:'TẠO 40 VIDEO',exact:true}).click();await expect(page.locator('.scene-card video')).toHaveCount(40);
  await page.getByRole('button',{name:'Tải tất cả (40/40)',exact:true}).click();await expect.poll(async()=>(await exportedFolders(page))[0]?.files.length).toBe(40);const videos=(await exportedFolders(page))[0];expect(videos.files[0].name).toMatch(/^video-000041-scene-01-/);expect(videos.files[39].name).toMatch(/^video-000080-scene-40-/);expect(videos.files.every(file=>file.bytes.toString('base64')===video)).toBe(true);
});

test('a shared-chat-only Muse keeps all thirty selected slots and runs one verified worker instead of blocking the batch',async({page})=>{
  const account={id:1,authenticated:true,sessionAuthenticated:true,active:true,state:'ready'};let warning='';
  await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',executionConcurrency:1,preferredConcurrency:30,concurrencyWarning:warning,accounts:[account]}}));
  await page.route('**/api/account/concurrency',route=>{warning='MUSE_PARALLEL_UNVERIFIED: Shared chat';return route.fulfill({status:409,json:{error:warning}})});
  await page.route('**/api/account/prepare',route=>route.fulfill({json:{executionConcurrency:1,preferredConcurrency:30,concurrencyWarning:warning}}));
  await page.reload();await page.getByLabel('Số luồng:',{exact:true}).selectOption('30');await expect(page.locator('.scene-card')).toHaveCount(30);await expect(page.getByLabel('Số luồng:',{exact:true})).toHaveValue('30');
  await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();await page.getByLabel('Nội dung TXT / SRT',{exact:true}).fill(Array.from({length:30},(_,i)=>`Queued scene ${i+1}`).join('\n'));await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
  let calls=0;await page.route('**/api/image',route=>{calls++;return new Promise(()=>{})});
  await page.getByRole('button',{name:'TẠO 30 ẢNH',exact:true}).click();await expect.poll(()=>calls).toBe(1);await expect(page.locator('.status-badge.running')).toHaveCount(1);await expect(page.locator('.status-badge.queued')).toHaveCount(29);await expect(page.getByText('Yêu cầu 30 luồng · đang dùng 1 luồng đã xác minh.',{exact:false})).toBeVisible();await page.getByRole('button',{name:'Dừng tất cả luồng',exact:true}).click();await expect(page.locator('.status-badge.cancelled')).toHaveCount(30);
});

test('Codex MCP configuration points at the chosen local port and never copies the secret key',async({page})=>{
  await page.context().grantPermissions(['clipboard-read','clipboard-write']);
  await page.addInitScript(()=>{(window as any).museTransport={automationControl:async()=>({enabled:true,listening:true,port:9876,address:'http://127.0.0.1:9876',key:'c'.repeat(64),error:''})}});
  await page.reload();await page.getByRole('button',{name:'Cổng API',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Cổng API cho công cụ bên ngoài',exact:true});await dialog.getByRole('button',{name:'Sao chép cấu hình Codex MCP',exact:true}).click();
  const config=await page.evaluate(()=>navigator.clipboard.readText());expect(config).toContain('[mcp_servers.muse_studio]\n');expect(config).toContain('url = "http://127.0.0.1:9876/mcp"');expect(config).toContain('bearer_token_env_var = "MUSE_STUDIO_KEY"');expect(config).not.toContain('c'.repeat(64));
});

import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const image=await readFile(new URL('../../public/demo-image.png',import.meta.url));
const clip=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');

test('restoring accounts keeps polling after the first verified session and unlocks without opening the account dialog',async({page})=>{
 let restoring=true;let checks=0;
 await page.route('**/api/status',route=>{checks++;return route.fulfill({json:{museConfigured:true,transport:'browser',embeddedLogin:true,restoringSessions:restoring,accounts:[{id:1,state:'ready',authenticated:true,sessionAuthenticated:true,active:true}]}})});
 await page.goto('/');await expect(page.getByText('Đang khôi phục các phiên Muse đã lưu trên máy…',{exact:false})).toBeVisible();await expect(page.getByRole('button',{name:'TẠO 10 VIDEO',exact:true})).toBeDisabled();
 restoring=false;await expect(page.getByRole('button',{name:'TẠO 10 VIDEO',exact:true})).toBeEnabled({timeout:10000});expect(checks).toBeGreaterThan(1);await expect(page.getByText('Đang khôi phục các phiên Muse đã lưu trên máy…',{exact:false})).toHaveCount(0);
});

test('sync toggles, selected settings and reference images affect exactly their targets and survive reload',async({page})=>{
  await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:40}}));await page.goto('/');
  await page.getByRole('button',{name:'Bỏ chọn',exact:true}).click();
  for(const id of [2,4])await page.getByLabel(`Chọn đồng bộ cảnh ${id}`,{exact:true}).check();
  await page.getByLabel('Ô đang chỉnh',{exact:true}).selectOption('2');
  await page.getByLabel('Chất lượng',{exact:true}).selectOption('4k');
  await expect(page.getByTestId('scene-2').locator('.scene-config')).toContainText('4K');await expect(page.getByTestId('scene-4').locator('.scene-config')).toContainText('4K');await expect(page.getByTestId('scene-1').locator('.scene-config')).toContainText('720P');
  const chooser=page.waitForEvent('filechooser');await page.getByRole('button',{name:'Tải ảnh nhân vật chung',exact:true}).click();await(await chooser).setFiles({name:'sync.png',mimeType:'image/png',buffer:image});
  await expect(page.locator('.scene-image')).toHaveCount(2);for(const id of [2,4])await expect(page.getByTestId(`scene-${id}`).locator('.scene-image')).toHaveCount(1);
  await page.getByRole('button',{name:'Đồng bộ thao tác: BẬT',exact:true}).click();await page.getByLabel('Ô đang chỉnh',{exact:true}).selectOption('3');await page.getByLabel('Chất lượng',{exact:true}).selectOption('1080p');
  await page.getByRole('button',{name:'Áp dụng cho 1 cảnh',exact:true}).click();await expect(page.locator('.scene-image')).toHaveCount(3);await expect(page.getByTestId('scene-3').locator('.scene-config')).toContainText('1080P');
  await page.reload();await expect(page.getByRole('button',{name:'Đồng bộ thao tác: TẮT',exact:true})).toHaveAttribute('aria-pressed','false');await expect(page.getByLabel('Chọn đồng bộ cảnh 2',{exact:true})).toBeChecked();await expect(page.getByLabel('Chọn đồng bộ cảnh 1',{exact:true})).not.toBeChecked();await expect(page.getByTestId('scene-3').locator('.scene-config')).toContainText('1080P');
  const payloads:any[]=[];await page.route('**/api/video',route=>{payloads.push(route.request().postDataJSON());return route.fulfill({json:{base64:clip,mimeType:'video/mp4'}})});
  await page.getByRole('button',{name:'Đồng bộ thao tác: TẮT',exact:true}).click();await page.getByRole('button',{name:'Tạo ô đã chọn',exact:true}).click();await expect(page.locator('.scene-card video')).toHaveCount(2);expect(payloads.map(value=>value.sceneId).sort()).toEqual([2,4]);expect(payloads.every(value=>value.resolution==='4k')).toBe(true);
});

test('stopping the synchronized selection leaves an unselected worker running',async({page})=>{
  await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:40}}));await page.goto('/');await page.getByLabel('Số ô',{exact:true}).selectOption('3');
  await page.getByLabel('Chọn đồng bộ cảnh 3',{exact:true}).uncheck();const calls:number[]=[];await page.route('**/api/video',route=>{calls.push(route.request().postDataJSON().sceneId);return new Promise(()=>{})});
  await page.getByRole('button',{name:'TẠO 3 VIDEO',exact:true}).click();await expect.poll(()=>calls.length).toBe(3);await page.getByRole('button',{name:'Dừng ô đã chọn',exact:true}).click();await expect(page.locator('.status-badge.cancelled')).toHaveCount(2);await expect(page.getByTestId('scene-3').locator('.status-badge')).toHaveClass(/running/);await page.getByRole('button',{name:'Dừng tất cả luồng',exact:true}).click();
});

test('optional proxy form is scoped to one account and does not echo saved credentials',async({page})=>{
 const accounts=Array.from({length:40},(_,i)=>({id:i+1,state:'ready',authenticated:true,sessionAuthenticated:true,active:true,proxy:{supported:true,enabled:i===1,server:i===1?'http://127.0.0.1:8123':'',hasUsername:i===1,hasPassword:i===1}}));
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',embeddedLogin:true,multiAccount:true,accounts}}));
 const calls:any[]=[];await page.route('**/api/account/proxy',route=>{calls.push(route.request().postDataJSON());return route.fulfill({json:{accounts}})});
 await page.goto('/');await page.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();await page.getByRole('button',{name:'Proxy Muse 2',exact:true}).click();
 await expect(page.getByLabel('Địa chỉ proxy',{exact:true})).toHaveValue('http://127.0.0.1:8123');await expect(page.getByLabel('Tên đăng nhập proxy',{exact:true})).toHaveCount(0);await page.getByRole('button',{name:'Lưu proxy',exact:true}).click();await expect.poll(()=>calls.length).toBe(1);expect(calls[0]).toEqual({accountId:2,proxy:{enabled:true,server:'http://127.0.0.1:8123'}});
 await page.getByRole('button',{name:'Proxy Muse 3',exact:true}).click();await page.getByLabel('Bật proxy',{exact:true}).check();await page.getByLabel('Địa chỉ proxy',{exact:true}).fill('http://proxy.example.invalid:9000');await page.getByLabel('Thay tài khoản proxy',{exact:true}).check();await page.getByLabel('Tên đăng nhập proxy',{exact:true}).fill('proxy-user');await page.getByLabel('Mật khẩu proxy',{exact:true}).fill('fixture-password');await page.getByRole('button',{name:'Lưu proxy',exact:true}).click();await expect.poll(()=>calls.length).toBe(2);expect(calls[1].accountId).toBe(3);expect(calls[1].proxy.password).toBe('fixture-password');expect(await page.evaluate(()=>localStorage.getItem('muse-workstation-v1'))).not.toContain('fixture-password');
});

import{test,expect}from'@playwright/test';
test('a never-ending request stops at the 200-second limit, keeps the prompt, and is not retried',async({page})=>{
 let calls=0;let release!:()=>void;const held=new Promise<void>(resolve=>release=resolve);
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:400}}));
 await page.route('**/api/video',async route=>{calls++;await held;await route.fulfill({status:504,json:{error:'late fixture timeout'}}).catch(()=>{})});
 await page.goto('/');await page.clock.install();await page.getByLabel('Số ô',{exact:true}).selectOption('1');await page.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Keep this full prompt after the deadline.');await page.getByRole('button',{name:'TẠO 1 VIDEO',exact:true}).click();await expect.poll(()=>calls).toBe(1);await expect(page.locator('.status-badge.running')).toHaveCount(1);
 await page.clock.fastForward(200001);await expect(page.locator('.status-badge.error')).toHaveCount(1);await expect(page.locator('.scene-error pre')).toContainText('MUSE_WAIT_LIMIT');await expect(page.locator('.status-badge.running')).toHaveCount(0);await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toHaveValue('Keep this full prompt after the deadline.');expect(calls).toBe(1);release();
});

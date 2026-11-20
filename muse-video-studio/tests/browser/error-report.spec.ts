import{test,expect}from'@playwright/test';import{readFile}from'node:fs/promises';
test('each failed slot can copy an error report or download TXT, with a download fallback when clipboard is blocked',async({page})=>{
 await page.context().grantPermissions(['clipboard-read','clipboard-write']);
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:400}}));
 await page.route('**/api/image',route=>route.fulfill({status:504,json:{error:'MUSE_TIMEOUT: Fixture error detail'}}));
 await page.goto('/');await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();await page.getByLabel('Số ô',{exact:true}).selectOption('1');await page.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Private prompt omitted from report');await page.getByRole('button',{name:'TẠO 1 ẢNH',exact:true}).click();
 await page.getByRole('button',{name:'Sao chép lỗi cảnh 1',exact:true}).click();const copied=await page.evaluate(()=>navigator.clipboard.readText());expect(JSON.parse(copied).error).toContain('MUSE_TIMEOUT');expect(copied).not.toContain('Private prompt');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Tải lỗi TXT cảnh 1',exact:true}).click();const file=await download;expect(file.suggestedFilename()).toBe('Muse-error-scene-1.txt');expect(JSON.parse(await readFile((await file.path())!,'utf8')).error).toContain('Fixture error detail');
 await page.evaluate(()=>{navigator.clipboard.writeText=async()=>{throw new Error('Blocked clipboard')}});const fallback=page.waitForEvent('download');await page.getByRole('button',{name:'Sao chép lỗi cảnh 1',exact:true}).click();expect((await fallback).suggestedFilename()).toBe('Muse-error-scene-1.txt');
});

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

test('a waiting slot shows the actual Muse reply and downloads a status report before the generation request ends',async({page})=>{
 let batchId='';let release!:()=>void;const held=new Promise<void>(resolve=>release=resolve);
 const observation={checkedAt:new Date().toISOString(),messageAcknowledged:true,assistantReplies:1,visibleVideos:0,visibleImages:0,matchedMedia:false,streaming:false,replyScope:'conversation',reply:'Would you like me to create a video using the available model?'};
 await page.route('**/api/status',route=>route.fulfill({json:{version:'1.13.4',museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:400,workerProgress:batchId?[{batchId,sceneId:1,accountId:1,output:'image',phase:'reply-received',active:true,submitted:true,observation}]:[]}}));
 await page.route('**/api/image',async route=>{batchId=route.request().postDataJSON().batchId;await held;await route.fulfill({status:422,json:{error:'MUSE_ACTION_REQUIRED: Muse requests confirmation'}})});
 await page.goto('/');await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();await page.getByLabel('Số ô',{exact:true}).selectOption('1');await page.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Private scene prompt');await page.getByRole('button',{name:'TẠO 1 ẢNH',exact:true}).click();
 await expect(page.getByText('Muse đã trả lời · đang kiểm tra kết quả',{exact:true})).toBeVisible();await page.getByText('Phản hồi gần nhất của Muse',{exact:true}).click();await expect(page.locator('.scene-observation pre')).toHaveText(observation.reply);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Tải trạng thái TXT cảnh 1',exact:true}).click();const report=JSON.parse(await readFile((await(await download).path())!,'utf8'));expect(report.observation.reply).toBe(observation.reply);expect(report.phase).toBe('reply-received');expect(JSON.stringify(report)).not.toContain('Private scene prompt');release();await expect(page.locator('.scene-error')).toBeVisible();
});

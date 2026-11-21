import{test,expect}from'@playwright/test';import{readFile}from'node:fs/promises';
const video=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');
test('recover five existing files without generating or preparing chats; retain TXT names and show 720p honestly',async({page})=>{
 let generated=0,prepared=0;const recovered:{sceneId:number;prompt:string}[]=[];
 const accounts=Array.from({length:40},(_,i)=>({id:i+1,label:`Muse ${i+1}`,authenticated:true,sessionAuthenticated:true,state:'ready',executionConcurrency:5}));
 await page.route('**/api/status',route=>route.fulfill({json:{version:'1.13.7',canRecoverMedia:true,museConfigured:true,transport:'browser',multiAccount:true,accounts,maxConcurrency:400,executionConcurrency:5}}));
 await page.route('**/api/account/prepare',route=>{prepared++;return route.fulfill({status:500,json:{error:'Recovery must not prepare or open new chats'}})});
 await page.route('**/api/video',route=>{generated++;return route.fulfill({status:500,json:{error:'Recovery must not submit generation'}})});
 await page.route('**/api/media/recover',route=>{recovered.push(route.request().postDataJSON());return route.fulfill({json:{base64:video,mimeType:'video/mp4',metadata:{width:1280,height:720,duration:10}}})});
 await page.goto('/');await page.getByLabel('Số ô',{exact:true}).selectOption('5');
 for(let i=1;i<=5;i++){await page.getByLabel(`Kịch bản cảnh ${i}`,{exact:true}).fill('Saved landscape '+i);await page.getByLabel(`Tên tệp cảnh ${i}`,{exact:true}).fill(i===1?'nam':'cảnh '+i)}
 await page.getByLabel('Chất lượng',{exact:true}).selectOption('1080p');await page.getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();
 await expect(page.locator('.status-badge.done')).toHaveCount(5);expect(recovered.map(x=>x.sceneId).sort((a,b)=>a-b)).toEqual([1,2,3,4,5]);expect(generated).toBe(0);expect(prepared).toBe(0);
 for(const request of recovered)expect(request.prompt).toBe('Saved landscape '+request.sceneId);
 await expect(page.locator('.quality-result.red')).toHaveCount(5);await expect(page.locator('.video-metadata').first()).toContainText('1280×720');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Tải cảnh 1',exact:true}).click();expect((await download).suggestedFilename()).toBe('nam.mp4');
});
test('a mapping error offers recovery as the main scene action instead of silently generating the scene again',async({page})=>{
 let generated=0,prepared=0,recovered=0;
 const accounts=[{id:1,label:'Muse 01',authenticated:true,sessionAuthenticated:true,state:'ready',executionConcurrency:1}];
 await page.route('**/api/status',route=>route.fulfill({json:{canRecoverMedia:true,museConfigured:true,transport:'browser',multiAccount:true,accounts,maxConcurrency:400,executionConcurrency:1}}));
 await page.route('**/api/account/prepare',route=>{prepared++;return route.fulfill({json:{executionConcurrency:1,accounts}})});
 await page.route('**/api/video',route=>{generated++;return route.fulfill({status:409,json:{error:'MUSE_BATCH_UNMATCHED: Files exist but local mapping needs recovery'}})});
 await page.route('**/api/media/recover',route=>{recovered++;return route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 await page.goto('/');await page.getByLabel('Số ô',{exact:true}).selectOption('1');await page.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Saved landscape 1');await page.getByRole('button',{name:'TẠO 1 VIDEO',exact:true}).click();
 const card=page.getByTestId('scene-1');await expect(card.locator('.scene-error')).toContainText('chưa ghép được');await card.locator('.card-footer').getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();
 await expect(card.locator('.status-badge.done')).toHaveCount(1);expect(generated).toBe(1);expect(prepared).toBe(1);expect(recovered).toBe(1);
});

test('three saved videos survive a reload; receive only missing scenes two and three without regenerating any scene',async({page})=>{
 let generated=0;const recovered:number[]=[];const accounts=[{id:1,label:'Muse 01',authenticated:true,sessionAuthenticated:true,state:'ready',executionConcurrency:5}];
 await page.route('**/api/status',route=>route.fulfill({json:{canRecoverMedia:true,museConfigured:true,transport:'browser',multiAccount:true,accounts,maxConcurrency:400,executionConcurrency:5}}));
 await page.route('**/api/account/prepare',route=>route.fulfill({json:{executionConcurrency:5,accounts}}));
 await page.route('**/api/video',route=>{generated++;const id=route.request().postDataJSON().sceneId;return route.fulfill([2,3].includes(id)?{status:409,json:{error:'MUSE_BATCH_UNMATCHED: Two native captions need recovery'}}:{json:{base64:video,mimeType:'video/mp4'}})});
 await page.route('**/api/media/recover',route=>{recovered.push(route.request().postDataJSON().sceneId);return route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 await page.goto('/');await page.getByLabel('Số ô',{exact:true}).selectOption('5');for(let i=1;i<=5;i++)await page.getByLabel(`Kịch bản cảnh ${i}`,{exact:true}).fill('Original landscape '+i);await page.getByRole('button',{name:'TẠO 5 VIDEO',exact:true}).click();
 await expect(page.locator('.status-badge.done')).toHaveCount(3);await expect(page.locator('.status-badge.error')).toHaveCount(2);expect(generated).toBe(5);
 await page.reload();await expect(page.locator('.scene-card video')).toHaveCount(3);await page.getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();await expect(page.locator('.status-badge.done')).toHaveCount(5);expect(recovered.sort()).toEqual([2,3]);expect(generated).toBe(5);await expect(page.locator('.scene-card video')).toHaveCount(5);
});

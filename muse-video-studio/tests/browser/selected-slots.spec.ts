import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const image=(await readFile(new URL('../../public/demo-image.png',import.meta.url))).toString('base64');
const accounts=Array.from({length:40},(_,i)=>({id:i+1,label:`Owner ${i+1}`,authenticated:true,sessionAuthenticated:true,state:'ready'}));

test('only selected nonconsecutive slots receive TXT/SRT, run and persist; hidden data survives',async({page})=>{
 await page.addInitScript(()=>{if(!localStorage.getItem('muse-workstation-v1'))localStorage.setItem('muse-workstation-v1',JSON.stringify({version:1,settings:{slotCount:10,accountMode:'multiple',output:'image'},scenes:Array.from({length:40},(_,i)=>({prompt:`Keep ${i+1}`,enabled:true,accountId:i+1}))}));});
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,accounts,executionConcurrency:1}}));
 await page.route('**/api/image',route=>route.fulfill({json:{base64:image,mimeType:'image/png'}}));
 await page.goto('/');await page.getByTestId('scene-2').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await expect(page.getByTestId('scene-2').locator('.generated-image')).toBeVisible();
 await page.getByRole('button',{name:'Ẩn tất cả ô',exact:true}).click();await expect(page.locator('.scene-card')).toHaveCount(0);
 for(const id of [1,3,4,7])await page.getByLabel(`Hiện ô ${id}`,{exact:true}).check();
 await expect(page.locator('.scene-number')).toHaveText(['#01','#03','#04','#07']);await expect(page.getByLabel('Số ô',{exact:true})).toHaveValue('4');await expect(page.getByLabel('Số luồng:',{exact:true})).toHaveValue('4');
 await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
 await page.getByRole('button',{name:'Chọn TXT / SRT',exact:true}).click({trial:true});
 await page.locator('input[type=file][accept=".txt,.srt"]').setInputFiles({name:'script.txt',mimeType:'text/plain',buffer:Buffer.from('First\nThird\nFourth\nSeventh')});
 await expect(page.locator('.script-preview>div>span')).toHaveText(['#01','#03','#04','#07']);
 await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
 for(const [i,id] of [1,3,4,7].entries())await expect(page.getByLabel(`Kịch bản cảnh ${id}`,{exact:true})).toHaveValue(['First','Third','Fourth','Seventh'][i]);
 await page.reload();await expect(page.locator('.scene-card')).toHaveCount(4);
 await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
 const srt=[1,2,3,4].map(i=>`${i}\n00:00:00,000 --> 00:00:01,000\nSubtitle ${i}`).join('\n\n');
 await page.locator('input[type=file][accept=".txt,.srt"]').setInputFiles({name:'script.srt',mimeType:'text/plain',buffer:Buffer.from(srt)});
 await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
 const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('muse-workstation-v1')!));expect(saved.scenes[1].prompt).toBe('Keep 2');expect(saved.scenes[26].prompt).toBe('Keep 27');expect(saved.settings.multipleSlotIds).toEqual([1,3,4,7]);
 const calls:number[]=[];await page.route('**/api/image',route=>{calls.push(route.request().postDataJSON().accountId);return route.fulfill({json:{base64:image,mimeType:'image/png'}})});
 await page.getByRole('button',{name:'TẠO 4 ẢNH',exact:true}).click();await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow','4');expect(calls.sort((a,b)=>a-b)).toEqual([1,3,4,7]);
 await page.getByLabel('Hiện ô 2',{exact:true}).check();await expect(page.getByLabel('Kịch bản cảnh 2',{exact:true})).toHaveValue('Keep 2');await expect(page.getByTestId('scene-2').locator('.generated-image')).toBeVisible();
});

test('overflow never silently imports outside the selected slots; empty selection survives reload',async({page})=>{
 await page.goto('/');await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');
 await page.getByRole('button',{name:'Ẩn tất cả ô',exact:true}).click();await page.reload();await expect(page.locator('.scene-card')).toHaveCount(0);
 await page.getByLabel('Hiện ô 27',{exact:true}).check();await expect(page.locator('.scene-number')).toHaveText(['#27']);
 await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();await page.getByLabel('Nội dung TXT / SRT',{exact:true}).fill('One\nTwo');await expect(page.getByRole('button',{name:'Nạp vào Studio',exact:true})).toBeDisabled();await expect(page.getByText('Kịch bản vượt số ô đã chọn.',{exact:false})).toBeVisible();
});

test('one click runs ten simultaneous slots and queues the other thirty without shrinking forty-slot layout',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('muse-workstation-v1',JSON.stringify({version:1,settings:{slotCount:40,accountMode:'single',singleAccountId:27,output:'image'},scenes:Array.from({length:40},(_,i)=>({prompt:`Parallel ${i+1}`,enabled:true}))})));
 let executionConcurrency=1;
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,accounts,executionAccountId:27,executionConcurrency,preferredConcurrency:2}}));
 const prepares:any[]=[];await page.route('**/api/account/prepare',route=>{prepares.push(route.request().postDataJSON());executionConcurrency=10;return route.fulfill({json:{executionConcurrency:10,preferredConcurrency:10}})});
 const calls:any[]=[];const release:Array<()=>Promise<void>>=[];let holding=true;
 await page.route('**/api/image',route=>{calls.push(route.request().postDataJSON());const respond=()=>route.fulfill({json:{base64:image,mimeType:'image/png'}});if(holding)return new Promise<void>(resolve=>release.push(async()=>{await respond();resolve()}));return respond()});
 await page.goto('/');await page.getByRole('button',{name:'TẠO SONG SONG 10 Ô',exact:true}).click();await expect.poll(()=>calls.length).toBe(10);await expect(page.locator('.status-badge.running')).toHaveCount(10);await expect(page.locator('.status-badge.queued')).toHaveCount(30);await expect(page.locator('.scene-card')).toHaveCount(40);expect(prepares).toEqual([{accountId:27,concurrency:10}]);
 await release.shift()!();await expect.poll(()=>calls.length).toBe(11);holding=false;await Promise.all(release.map(fn=>fn()));await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow','40');expect(calls).toHaveLength(40);expect(calls.every(call=>call.accountId===27)).toBe(true);await expect(page.locator('.scene-card')).toHaveCount(40);
});

test('parallel-ten action sends no prompt if ten independent conversations cannot be verified',async({page})=>{
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,accounts,executionConcurrency:1}}));
 await page.route('**/api/account/prepare',route=>route.fulfill({json:{executionConcurrency:1,preferredConcurrency:10,concurrencyWarning:'Shared conversation only'}}));
 let calls=0;await page.route('**/api/video',route=>{calls++;return route.fulfill({status:500,json:{error:'Unexpected submission'}})});
 await page.goto('/');await page.getByRole('button',{name:'TẠO SONG SONG 10 Ô',exact:true}).click();await expect(page.getByText('Chưa thể chạy song song 10 ô:',{exact:false})).toBeVisible();expect(calls).toBe(0);await expect(page.locator('.status-badge.running')).toHaveCount(0);
});

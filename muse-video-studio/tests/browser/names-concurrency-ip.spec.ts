import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {mockFolderPicker,exportedFolders} from '../fixtures/folders.ts';
const image=(await readFile(new URL('../../public/demo-image.png',import.meta.url))).toString('base64');
const video=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');
const accounts=Array.from({length:40},(_,i)=>({id:i+1,label:`Muse ${i+1}`,authenticated:true,sessionAuthenticated:true,active:true,state:'ready',executionConcurrency:6}));
test('large TXT headings and SRT names reach individual and batch files; unnamed numbering continues after reload',async({page})=>{
 await mockFolderPicker(page.context());
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:400}}));
 await page.route('**/api/image',route=>route.fulfill({json:{base64:image,mimeType:'image/png'}}));
 await page.route('**/api/video',route=>route.fulfill({json:{base64:video,mimeType:'video/mp4'}}));
 await page.goto('/');await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
 await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
 const script='[1] AIKO TANAKA — JDR001\nNotes: retained identity.\n1. PROMPT CHAN DUNG — AIKO:\nA portrait, no text.\n2. PROMPT TOAN THAN — AIKO:\nA full-body image, no text.\n3. MO TA GIONG NOI:\nVoice metadata, not a render prompt.';
 await page.getByLabel('Nội dung TXT / SRT',{exact:true}).fill(script);await expect(page.locator('.script-preview>div')).toHaveCount(2);await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
 await expect(page.getByLabel('Tên tệp cảnh 1',{exact:true})).toHaveValue('AIKO TANAKA — JDR001 — CHAN DUNG');await expect(page.getByLabel('Tên tệp cảnh 2',{exact:true})).toHaveValue('AIKO TANAKA — JDR001 — TOAN THAN');
 await page.getByLabel('Số ô',{exact:true}).selectOption('2');await page.getByRole('button',{name:'TẠO 2 ẢNH',exact:true}).click();await expect(page.locator('.generated-image')).toHaveCount(2);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Tải cảnh 1',exact:true}).click();expect((await download).suggestedFilename()).toBe('AIKO TANAKA — JDR001 — CHAN DUNG.png');
 await page.getByRole('button',{name:'Tải tất cả (2/2)',exact:true}).click();await expect.poll(async()=>(await exportedFolders(page))[0]?.files.length).toBe(2);expect((await exportedFolders(page))[0].files.map(f=>f.name)).toEqual(['AIKO TANAKA — JDR001 — CHAN DUNG.png','AIKO TANAKA — JDR001 — TOAN THAN.png']);
 await page.reload();await expect(page.getByLabel('Tên tệp cảnh 2',{exact:true})).toHaveValue('AIKO TANAKA — JDR001 — TOAN THAN');
 await page.getByRole('button',{name:'Tạo video',exact:true}).click();await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
 await page.getByLabel('Nội dung TXT / SRT',{exact:true}).fill('1\n00:00:00,000 --> 00:00:10,000\nTên video: Cảnh mở đầu.mp4\nA named video.\n\n2\n00:00:10,000 --> 00:00:20,000\nA video without a title.');await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();await page.getByRole('button',{name:'TẠO 2 VIDEO',exact:true}).click();await expect(page.locator('.scene-card video')).toHaveCount(2);
 await page.getByRole('button',{name:'Tải tất cả (2/2)',exact:true}).click();await expect.poll(async()=>(await exportedFolders(page))[0]?.files.length).toBe(2);expect((await exportedFolders(page))[0].files.map(f=>f.name)).toEqual(['Cảnh mở đầu.mp4','1.mp4']);
 await page.reload();const second=page.waitForEvent('download');await page.getByRole('button',{name:'Tải cảnh 2',exact:true}).click();expect((await second).suggestedFilename()).toBe('2.mp4');
});
test('10 accounts × 6 submits sixty concurrent videos, caps each account at six and preserves names/layout across reload',async({page})=>{
 test.setTimeout(90000);
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,executionConcurrency:6,accounts}}));
 const prepares:any[]=[];await page.route('**/api/account/prepare',route=>{prepares.push(route.request().postDataJSON());return route.fulfill({json:{executionConcurrency:6,accounts}})});
 const calls:any[]=[];const release:Array<()=>Promise<void>>=[];
 await page.route('**/api/video',route=>{calls.push(route.request().postDataJSON());return new Promise<void>(resolve=>release.push(async()=>{await route.fulfill({json:{base64:video,mimeType:'video/mp4'}});resolve()}))});
 await page.goto('/');await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');
 await expect(page.getByLabel('Số tài khoản chạy',{exact:true})).toHaveValue('10');await expect(page.getByLabel('Ô chạy mỗi tài khoản',{exact:true})).toHaveValue('6');await expect(page.locator('.scene-card')).toHaveCount(60);await page.screenshot({path:'test-results/muse-113-60-slots.png'});
 await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();await page.getByLabel('Nội dung TXT / SRT',{exact:true}).fill(Array.from({length:60},(_,i)=>`Scene ${i+1} plain prompt`).join('\n'));await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
 await page.getByRole('button',{name:'TẠO 60 VIDEO',exact:true}).click();await expect.poll(()=>calls.length).toBe(60);await expect(page.locator('.status-badge.running')).toHaveCount(60);
 for(let id=1;id<=10;id++){const wave=calls.filter(call=>call.accountId===id);expect(wave).toHaveLength(6);expect(wave.every(call=>call.submissionGroup?.size===6)).toBe(true);expect(new Set(wave.map(call=>call.submissionGroup.id)).size).toBe(1);}
 expect(new Set(calls.map(call=>call.submissionGroup.id)).size).toBe(10);
 expect(prepares).toHaveLength(10);expect(prepares.every(value=>value.concurrency===6)).toBe(true);
 await Promise.all(release.map(fn=>fn()));await expect(page.locator('.scene-card video')).toHaveCount(60,{timeout:30000});await expect(page.getByLabel('Chế độ tài khoản',{exact:true})).toBeEnabled();
 await page.reload();await expect(page.locator('.scene-card')).toHaveCount(60);await expect(page.getByLabel('Kịch bản cảnh 60',{exact:true})).toHaveValue('Scene 60 plain prompt');await expect(page.getByLabel('Tài khoản cảnh 60',{exact:true})).toHaveValue('10');
 await page.getByLabel('Ô chạy tài khoản 1',{exact:true}).selectOption('2');await expect(page.locator('.scene-card')).toHaveCount(56);await page.reload();await expect(page.getByLabel('Ô chạy tài khoản 1',{exact:true})).toHaveValue('2');await expect(page.getByLabel('Ô chạy tài khoản 2',{exact:true})).toHaveValue('6');
 await page.getByLabel('Ô chạy mỗi tài khoản',{exact:true}).selectOption('10');await expect(page.locator('.scene-card')).toHaveCount(100);await page.getByLabel('Ô chạy mỗi tài khoản',{exact:true}).selectOption('1');await expect(page.locator('.scene-card')).toHaveCount(10);await page.getByLabel('Ô chạy mỗi tài khoản',{exact:true}).selectOption('6');await expect(page.getByLabel('Kịch bản cảnh 60',{exact:true})).toHaveValue('Scene 60 plain prompt');
});
test('each proxy has an independent read-only IP, check action and error state',async({page})=>{
 const rows=accounts.map(account=>({...account,proxy:{supported:true,enabled:true,server:`http://proxy${account.id}.invalid:8000`,exitIP:'',ipState:'unchecked'}}));
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',embeddedLogin:true,multiAccount:true,accounts:rows}}));
 const calls:number[]=[];await page.route('**/api/account/proxy-ip',route=>{const id=route.request().postDataJSON().accountId;calls.push(id);rows[id-1].proxy={...rows[id-1].proxy,exitIP:id===2?'203.0.113.2':'',ipState:id===2?'ready':'error'};return route.fulfill({json:{accounts:rows,proxy:{...rows[id-1].proxy,ipError:id===2?'':'Proxy connection failed'}}})});
 await page.goto('/');await page.getByRole('button',{name:'Quản lý tài khoản',exact:true}).click();await expect(page.getByLabel('IP proxy 2',{exact:true})).toHaveValue('Chưa kiểm tra');
 await page.getByRole('button',{name:'Kiểm tra IP proxy 2',exact:true}).click();await expect(page.getByLabel('IP proxy 2',{exact:true})).toHaveValue('203.0.113.2');await expect(page.getByLabel('IP proxy 1',{exact:true})).toHaveValue('Chưa kiểm tra');expect(calls).toEqual([2]);
});
test('different account limits submit exactly two and four simultaneous videos on their assigned accounts',async({page})=>{
 const rows=accounts.map(account=>({...account}));const prepares:any[]=[];const calls:any[]=[];const release:Array<()=>Promise<void>>=[];
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,accounts:rows}}));
 await page.route('**/api/account/prepare',route=>{const data=route.request().postDataJSON();prepares.push(data);rows[data.accountId-1].executionConcurrency=data.concurrency;return route.fulfill({json:{executionConcurrency:data.concurrency,accounts:rows}})});
 await page.route('**/api/video',route=>{calls.push(route.request().postDataJSON());return new Promise<void>(resolve=>release.push(async()=>{await route.fulfill({json:{base64:video,mimeType:'video/mp4'}});resolve()}))});
 await page.goto('/');await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');await page.getByLabel('Số tài khoản chạy',{exact:true}).fill('2');
 await page.getByLabel('Ô chạy tài khoản 1',{exact:true}).selectOption('2');await page.getByLabel('Ô chạy tài khoản 2',{exact:true}).selectOption('4');await expect(page.locator('.scene-card')).toHaveCount(6);
 await page.getByRole('button',{name:'TẠO 6 VIDEO',exact:true}).click();await expect.poll(()=>calls.length).toBe(6);expect(calls.filter(x=>x.accountId===1)).toHaveLength(2);expect(calls.filter(x=>x.accountId===2)).toHaveLength(4);expect(prepares).toEqual([{accountId:1,concurrency:2},{accountId:2,concurrency:4}]);
 await Promise.all(release.map(fn=>fn()));await expect(page.locator('.scene-card video')).toHaveCount(6);
});

test('ten mixed bracket headings import in order, display names on every card and retain exact names in image/video downloads',async({page})=>{
 await mockFolderPicker(page.context());
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'adapter',accounts:[],maxConcurrency:400}}));
 await page.route('**/api/image',route=>route.fulfill({json:{base64:image,mimeType:'image/png'}}));
 await page.route('**/api/video',route=>route.fulfill({json:{base64:video,mimeType:'video/mp4'}}));
 const names=['nam','thái','nga','thang','hoang','thu','thao','tuan','phang','phu'];
 const headings=[' [1] nam ',' [2] thái',' [3] nga',' [4]thang',' [5] hoang',' [6] thu',' [7]  thao',' [8]tuan',' [ 9 ] phang','[10]phu '];
 const sections=headings.map((heading,i)=>`${heading}\nFull prompt ${i+1}.\nSecond line ${i+1}.`);
 await page.goto('/');await page.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
 await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
 await page.locator('input[type=file][accept=".txt,.srt"]').setInputFiles({name:'Troaimusic.txt',mimeType:'text/plain',buffer:Buffer.from(sections.join('\r\n'))});
 await expect(page.locator('.script-preview>div')).toHaveCount(10);await expect(page.locator('.script-entry-name')).toHaveText(names);
 await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
 for(const [i,name]of names.entries()){
  await expect(page.getByLabel(`Tên tệp cảnh ${i+1}`,{exact:true})).toHaveValue(name);
  await expect(page.getByLabel(`Kịch bản cảnh ${i+1}`,{exact:true})).toHaveValue(`Full prompt ${i+1}.\nSecond line ${i+1}.`);
 }
 await expect(page.locator('.scene-title')).toHaveText(names.map((name,i)=>`[${i+1}] ${name}`));
 await page.getByRole('button',{name:'TẠO 10 ẢNH',exact:true}).click();await expect(page.locator('.generated-image')).toHaveCount(10);
 await page.getByRole('button',{name:'Tải tất cả (10/10)',exact:true}).click();await expect.poll(async()=>(await exportedFolders(page))[0]?.files.map(f=>f.name)).toEqual(names.map(name=>name+'.png'));
 await page.reload();await expect(page.locator('.scene-title')).toHaveText(names.map((name,i)=>`[${i+1}] ${name}`));
 await page.getByRole('button',{name:'Tạo video',exact:true}).click();await page.getByRole('button',{name:'Nhập TXT / SRT',exact:true}).click();
 const srt=sections.map((section,i)=>`${i+1}\n00:00:${String(i).padStart(2,'0')},000 --> 00:00:${String(i+1).padStart(2,'0')},000\n${section}`).join('\n\n');
 await page.locator('input[type=file][accept=".txt,.srt"]').setInputFiles({name:'titles.srt',mimeType:'application/x-subrip',buffer:Buffer.from(srt)});await expect(page.locator('.script-entry-name')).toHaveText(names);await page.getByRole('button',{name:'Nạp vào Studio',exact:true}).click();
 await page.getByRole('button',{name:'TẠO 10 VIDEO',exact:true}).click();await expect(page.locator('.scene-card video')).toHaveCount(10);
 await page.getByRole('button',{name:'Tải tất cả (10/10)',exact:true}).click();await expect.poll(async()=>(await exportedFolders(page))[0]?.files.map(f=>f.name)).toEqual(names.map(name=>name+'.mp4'));
 const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Tải cảnh 8',exact:true}).click();expect((await downloaded).suggestedFilename()).toBe('tuan.mp4');
});

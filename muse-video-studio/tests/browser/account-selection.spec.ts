import {test,expect} from '@playwright/test';

test('per-slot accounts and corresponding proxies persist without replacing workspace data',async({page})=>{
 const accounts=Array.from({length:40},(_,i)=>({id:i+1,label:`owner${i+1}`,authenticated:true,sessionAuthenticated:true,state:'ready',proxy:{supported:true,enabled:false,server:''}}));
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',embeddedLogin:true,multiAccount:true,executionConcurrency:10,preferredConcurrency:10,accounts}}));
 await page.route('**/api/account/select',route=>route.fulfill({json:{accounts}}));
 const proxies:any[]=[];await page.route('**/api/account/proxy',route=>{proxies.push(route.request().postDataJSON());return route.fulfill({json:{accounts}})});
 await page.goto('/');await page.getByLabel('Chế độ tài khoản',{exact:true}).selectOption('multiple');
 await page.getByLabel('Tài khoản cảnh 1',{exact:true}).selectOption('27');
 await page.getByLabel('Tài khoản cảnh 2',{exact:true}).selectOption('27');
 await page.getByLabel('Proxy cảnh 1',{exact:true}).click();
 await expect(page.getByRole('region',{name:'Proxy tài khoản 27'})).toBeVisible();
 await page.getByLabel('Bật proxy',{exact:true}).check();
 await page.getByLabel('Địa chỉ proxy',{exact:true}).fill('http://127.0.0.1:8080');
 await page.getByRole('button',{name:'Lưu proxy',exact:true}).click();
 await expect.poll(()=>proxies.length).toBe(1);expect(proxies[0].accountId).toBe(27);
 await page.getByRole('button',{name:'Đóng',exact:true}).click();
 await page.reload();await expect(page.getByLabel('Tài khoản cảnh 1',{exact:true})).toHaveValue('27');await expect(page.getByLabel('Tài khoản cảnh 2',{exact:true})).toHaveValue('27');
 // Sharing an account queues the second slot instead of submitting two conflicting requests.
 let calls:any[]=[];await page.route('**/api/video',route=>{calls.push(route.request().postDataJSON());return new Promise(()=>{})});
 await page.getByTestId('scene-1').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
 await page.getByTestId('scene-2').getByRole('button',{name:'Tạo cảnh này',exact:true}).click();
 await expect.poll(()=>calls.length).toBe(1);expect(calls[0].accountId).toBe(27);
});

test('any signed-in account can run ten shared lanes and survives reload',async({page})=>{
 const accounts=[1,27].map(id=>({id,label:`owner${id}`,authenticated:true,sessionAuthenticated:true,state:'ready'}));
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,executionConcurrency:10,preferredConcurrency:10,accounts}}));
 await page.route('**/api/account/select',route=>route.fulfill({json:{accounts}}));
 const preparation:any[]=[];await page.route('**/api/account/prepare',route=>{preparation.push(route.request().postDataJSON());return route.fulfill({json:{executionConcurrency:10,preferredConcurrency:10}})});
 await page.goto('/');await page.getByLabel('Tài khoản chạy mọi ô',{exact:true}).selectOption('27');await page.reload();await expect(page.getByLabel('Tài khoản chạy mọi ô',{exact:true})).toHaveValue('27');
 const calls:any[]=[];await page.route('**/api/video',route=>{calls.push(route.request().postDataJSON());return new Promise(()=>{})});
 await page.getByRole('button',{name:'TẠO 10 VIDEO',exact:true}).click();await expect.poll(()=>calls.length).toBe(10);expect(calls.every(call=>call.accountId===27&&call.accountMode==='single')).toBe(true);expect(preparation[0].accountId).toBe(27);
});

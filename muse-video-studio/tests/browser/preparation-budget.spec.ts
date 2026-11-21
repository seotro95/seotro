import{test,expect}from'@playwright/test';
test('sixty seconds of preparation leave only 140 seconds for first-wave generation; total loading ends at 200 seconds',async({page})=>{
 let prepareRelease!:()=>void,renderRelease!:()=>void;let preparing=false;const prepared=new Promise<void>(r=>prepareRelease=r),held=new Promise<void>(r=>renderRelease=r);const requests:{waitBudgetMs:number}[]=[];
 const accounts=[{id:1,label:'Muse 01',authenticated:true,sessionAuthenticated:true,state:'ready',executionConcurrency:1}];
 await page.route('**/api/status',route=>route.fulfill({json:{museConfigured:true,transport:'browser',multiAccount:true,accounts,maxConcurrency:400,executionConcurrency:1}}));
 await page.route('**/api/account/prepare',async route=>{preparing=true;await prepared;await route.fulfill({json:{executionConcurrency:1,accounts}}).catch(()=>{})});
 await page.route('**/api/video',async route=>{requests.push(route.request().postDataJSON());await held;await route.fulfill({status:504,json:{error:'late fixture response'}}).catch(()=>{})});
 try{await page.goto('/');await page.clock.install();await page.getByLabel('Số ô',{exact:true}).selectOption('1');await page.getByLabel('Kịch bản cảnh 1',{exact:true}).fill('Keep this full prompt after preparation and timeout.');await page.getByRole('button',{name:'TẠO 1 VIDEO',exact:true}).click();await expect.poll(()=>preparing).toBe(true);await page.clock.fastForward(60000);prepareRelease();await expect.poll(()=>requests.length).toBe(1);expect(requests[0].waitBudgetMs).toBeGreaterThan(138000);expect(requests[0].waitBudgetMs).toBeLessThanOrEqual(140000);await expect(page.locator('.status-badge.running')).toHaveCount(1);
  await page.clock.fastForward(140001);await expect(page.locator('.status-badge.error')).toHaveCount(1);await expect(page.locator('.status-badge.running')).toHaveCount(0);await expect(page.locator('.scene-error pre')).toContainText('MUSE_WAIT_LIMIT');expect(requests.length).toBe(1);await expect(page.getByLabel('Kịch bản cảnh 1',{exact:true})).toHaveValue('Keep this full prompt after preparation and timeout.');
 }finally{prepareRelease?.();renderRelease?.();}
});

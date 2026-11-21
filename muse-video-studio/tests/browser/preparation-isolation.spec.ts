import{test,expect}from'@playwright/test';import{readFile}from'node:fs/promises';
const video=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');
test('a missing composer on account three preserves its prompts and does not block four scenes on two healthy accounts',async({page})=>{
 const accounts=Array.from({length:40},(_,i)=>({id:i+1,label:`Muse ${i+1}`,authenticated:true,sessionAuthenticated:true,state:'ready',executionConcurrency:2}));
 await page.addInitScript(()=>localStorage.setItem('muse-workstation-v1',JSON.stringify({version:1,settings:{accountMode:'multiple',selectedAccountIds:[1,2,3],requestedConcurrency:2,slotCount:6,output:'video'},scenes:Array.from({length:6},(_,i)=>({prompt:'Preserve prompt '+(i+1),enabled:true,accountId:Math.floor(i/2)+1}))})));
 await page.route('**/api/status',route=>route.fulfill({json:{canRecoverMedia:true,museConfigured:true,transport:'browser',multiAccount:true,accounts,executionConcurrency:2}}));
 const prepared:number[]=[],generated:{accountId:number;sceneId:number}[]=[];
 await page.route('**/api/account/prepare',route=>{const id=route.request().postDataJSON().accountId;prepared.push(id);return route.fulfill(id===3?{status:409,json:{error:'MUSE_COMPOSER_NOT_READY: Authenticated page has zero Message editors; no prompt sent'}}:{json:{executionConcurrency:2,accounts}})});
 await page.route('**/api/video',route=>{generated.push(route.request().postDataJSON());return route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 await page.goto('/');await expect(page.locator('.scene-card')).toHaveCount(6);await page.getByRole('button',{name:'TẠO 6 VIDEO',exact:true}).click();
 await expect(page.locator('.status-badge.done')).toHaveCount(4);await expect(page.locator('.status-badge.error')).toHaveCount(2);expect(prepared.sort()).toEqual([1,2,3]);expect(generated.map(x=>x.sceneId).sort()).toEqual([1,2,3,4]);expect(generated.some(x=>x.accountId===3)).toBe(false);
 for(const id of [5,6]){await expect(page.getByLabel(`Kịch bản cảnh ${id}`,{exact:true})).toHaveValue('Preserve prompt '+id);await expect(page.getByTestId(`scene-${id}`).locator('.scene-error pre')).toContainText('MUSE_COMPOSER_NOT_READY')}
});

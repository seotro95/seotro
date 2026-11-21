import{test,expect}from'@playwright/test';
import type{Page}from'@playwright/test';
import{readFile}from'node:fs/promises';
const video=(await readFile(new URL('../../public/demo.mp4',import.meta.url))).toString('base64');
const prompt='CLIP 058 — An original landscape with mature adult researchers. Silent video.';
const accounts=[1,2].map(id=>({id,label:`Muse ${id}`,state:'ready',authenticated:true,sessionAuthenticated:true,executionConcurrency:6}));
async function setup(page:Page,options:{modifier?:string;sceneModifier?:string}={}){
 await page.addInitScript(({prompt,modifier,sceneModifier})=>localStorage.setItem('muse-workstation-v1',JSON.stringify({version:1,settings:{accountMode:'multiple',accountPlanMode:'expanded',selectedAccountIds:[1,2],requestedConcurrency:6,slotCount:58,multipleSlotIds:[1,58],output:'video',syncOperations:false,modifier:modifier||''},scenes:Array.from({length:58},(_,i)=>({prompt:i===57?prompt:'Keep other account prompt '+(i+1),outputName:i===57?'Tên Nam 058':'other '+(i+1),enabled:true,accountId:i===57?2:1,...(i===57&&sceneModifier!==undefined?{renderSettings:{modifier:sceneModifier}}:{})}))})),{prompt,...options});
 await page.route('**/api/status',route=>route.fulfill({json:{version:'1.13.14',museConfigured:true,transport:'browser',multiAccount:true,canRecoverMedia:true,canClearToolDraft:true,accounts,executionConcurrency:6}}));
 await page.route('**/api/account/prepare',route=>route.fulfill({json:{executionConcurrency:6,accounts}}));
 await page.goto('/');await expect(page.getByTestId('scene-58').getByRole('button',{name:'Tạo cảnh này',exact:true})).toBeEnabled();
}

test('Explicit cleanup targets scene58 account2, preserves names/prompts and never auto-retries; another account can still generate',async({page})=>{
 const generated:any[]=[],cleaned:any[]=[];let release!:()=>void,releaseOther!:()=>void;const held=new Promise<void>(resolve=>release=resolve),otherHeld=new Promise<void>(resolve=>releaseOther=resolve);
 const modifier='   Keep the camera steady.\nAll visible people are mature adults.   ',fullPrompt=[prompt,modifier.trim()].join('\n\n');
 await page.route('**/api/video',async route=>{const data=route.request().postDataJSON();generated.push(data);if(data.accountId===1)await otherHeld;return route.fulfill(data.accountId===2&&generated.filter(row=>row.accountId===2).length===1?{status:409,json:{error:'MUSE_DRAFT_EXISTS: Ô Message ban đầu đang có bản nháp. Tool giữ nguyên nội dung và chưa gửi prompt.'}}:{json:{base64:video,mimeType:'video/mp4'}})});
 await page.route('**/api/account/clear-tool-draft',async route=>{cleaned.push(route.request().postDataJSON());await held;await route.fulfill({json:{cleared:true,acknowledged:false,message:'Đã dọn đúng bản nháp tool. Chưa nhấn Enter.',accounts}})});
 await setup(page,{modifier:'An unrelated default for other scenes.',sceneModifier:modifier});const card=page.getByTestId('scene-58');await card.getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await expect(card.locator('.scene-error')).toContainText('Dọn bản nháp tool');expect(generated[0].prompt).toBe(fullPrompt);
 try{
  const other=page.getByTestId('scene-1');await other.getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await expect(other.locator('.status-badge.running')).toHaveCount(1);await expect.poll(()=>generated.length).toBe(2);await expect(page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true}).click();await expect.poll(()=>cleaned.length).toBe(1);expect(cleaned[0]).toEqual({accountId:2,prompt:fullPrompt,output:'video'});expect(cleaned[0].prompt).toBe(generated[0].prompt);expect(generated).toHaveLength(2);await expect(card.locator('.card-footer button').first()).toBeDisabled();await expect(other.locator('.status-badge.running')).toHaveCount(1);
  release();await expect(page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true})).toHaveCount(0);await expect(card.getByRole('button',{name:'Tạo cảnh này',exact:true})).toBeEnabled();expect(generated).toHaveLength(2);
  await expect(page.getByLabel('Kịch bản cảnh 58',{exact:true})).toHaveValue(prompt);await expect(page.getByLabel('Tên tệp cảnh 58',{exact:true})).toHaveValue('Tên Nam 058');await expect(page.locator('.toast')).toContainText('Chưa tự gửi prompt hoặc tạo tệp');
  await expect(other.locator('.status-badge.running')).toHaveCount(1);releaseOther();await expect(other.locator('.status-badge.done')).toHaveCount(1);
  await card.getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await expect(card.locator('.status-badge.done')).toHaveCount(1);expect(generated.map(row=>row.accountId)).toEqual([2,1,2]);expect(generated[2].prompt).toBe(fullPrompt);expect(generated[2].outputName).toBe('Tên Nam 058');
 }finally{release();releaseOther()}
});

test('Acknowledged cleanup offers receive-existing as the main action and does not regenerate a previously received request',async({page})=>{
 const generated:any[]=[],received:any[]=[];let cleaned=0;
 await page.route('**/api/video',route=>{generated.push(route.request().postDataJSON());return route.fulfill({status:409,json:{error:'MUSE_DRAFT_EXISTS: Ô Message ban đầu đang có bản nháp.'}})});
 await page.route('**/api/account/clear-tool-draft',route=>{cleaned++;return route.fulfill({json:{cleared:true,acknowledged:true,message:'Muse đã nhận lượt này. Bản nháp dư đã dọn.',accounts}})});
 await page.route('**/api/media/recover',route=>{received.push(route.request().postDataJSON());return route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 await setup(page);const card=page.getByTestId('scene-58');await card.getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true}).click();await expect(card.locator('.scene-error')).toContainText('Muse đã nhận lượt có prompt này');await expect(card.locator('.card-footer').getByRole('button',{name:'Nhận lại từ Muse',exact:true})).toBeEnabled();expect(generated).toHaveLength(1);expect(received).toHaveLength(0);expect(cleaned).toBe(1);
 await card.locator('.card-footer').getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();await expect(card.locator('.status-badge.done')).toHaveCount(1);expect(generated).toHaveLength(1);expect(received).toHaveLength(1);expect(received[0]).toMatchObject({accountId:2,sceneId:58,prompt,output:'video'});await expect(page.getByLabel('Tên tệp cảnh 58',{exact:true})).toHaveValue('Tên Nam 058');
});

test('Rejected cleanup leaves the original error, prompt and output name intact without a generation retry',async({page})=>{
 let generated=0,cleaned=0;
 await page.route('**/api/video',route=>{generated++;return route.fulfill({status:409,json:{error:'MUSE_DRAFT_EXISTS: Ô Message ban đầu đang có bản nháp.'}})});
 await page.route('**/api/account/clear-tool-draft',route=>{cleaned++;return route.fulfill({status:409,json:{error:'MUSE_DRAFT_UNVERIFIED: Nội dung không khớp nguyên bản prompt tool. Bản nháp được giữ.'}})});
 await setup(page);const card=page.getByTestId('scene-58');await card.getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true}).click();await expect(page.locator('.toast')).toContainText('MUSE_DRAFT_UNVERIFIED');await expect(page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true})).toBeEnabled();await expect(card.locator('.scene-error pre')).toContainText('MUSE_DRAFT_EXISTS');await expect(page.getByLabel('Kịch bản cảnh 58',{exact:true})).toHaveValue(prompt);await expect(page.getByLabel('Tên tệp cảnh 58',{exact:true})).toHaveValue('Tên Nam 058');expect(generated).toBe(1);expect(cleaned).toBe(1);
});

test('An uncertain Enter attempt offers read-only recovery without exposing a cleanup or automatic retry',async({page})=>{
 let generated=0,cleaned=0,received=0;
 await page.route('**/api/video',route=>{generated++;return route.fulfill({status:409,json:{error:'MUSE_DRAFT_UNCERTAIN: Enter was attempted; receipt is unknown.'}})});
 await page.route('**/api/account/clear-tool-draft',route=>{cleaned++;return route.fulfill({json:{cleared:false,acknowledged:false}})});
 await page.route('**/api/media/recover',route=>{received++;return route.fulfill({json:{base64:video,mimeType:'video/mp4'}})});
 await setup(page);const card=page.getByTestId('scene-58');await card.getByRole('button',{name:'Tạo cảnh này',exact:true}).click();await expect(card.locator('.scene-error')).toContainText('chưa xác nhận được Muse đã nhận');await expect(page.getByRole('button',{name:'Dọn bản nháp tool cảnh 58',exact:true})).toHaveCount(0);await expect(card.locator('.card-footer').getByRole('button',{name:'Nhận lại từ Muse',exact:true})).toBeEnabled();expect(generated).toBe(1);expect(received).toBe(0);expect(cleaned).toBe(0);
 await card.locator('.card-footer').getByRole('button',{name:'Nhận lại từ Muse',exact:true}).click();await expect(card.locator('.status-badge.done')).toHaveCount(1);expect(received).toBe(1);expect(generated).toBe(1);expect(cleaned).toBe(0);
});

import {MAX_SLOTS,isSlotCount} from '../limits.mjs';
import { normalizeSettings, parseScript } from './core.ts';
import type { Settings } from './core.ts';

export const apiError=(status: number,message: string)=>Object.assign(new Error(message),{status});
export function parseAutomationBatch(data: any,current: Settings) {
  if(!data||typeof data!=='object'||Array.isArray(data))throw apiError(400,'Cần một đối tượng JSON.');
  const fields=['prompts','script','sceneIds','output','settings','referenceImage','sourceMediaId'];
  if(Object.keys(data).some(key=>!fields.includes(key)))throw apiError(400,'Tham số không hỗ trợ. Xem API-AUTOMATION.md.');
  if(data.prompts!==undefined&&data.script!==undefined)throw apiError(400,'Chỉ gửi prompts hoặc script.');
  const prompts=data.script!==undefined?typeof data.script==='string'?parseScript(data.script):null:data.prompts;
  if(!Array.isArray(prompts)||prompts.length<1||prompts.length>MAX_SLOTS||prompts.some(prompt=>typeof prompt!=='string'||!prompt.trim()||prompt.length>8000))throw apiError(400,'Gửi 1–40 prompt không rỗng, tối đa 8.000 ký tự mỗi cảnh.');
  const ids=data.sceneIds??prompts.map((_,index)=>index+1);
  if(!Array.isArray(ids)||ids.length!==prompts.length||new Set(ids).size!==ids.length||ids.some(id=>!Number.isInteger(id)||id<1||id>MAX_SLOTS))throw apiError(400,'sceneIds cần khớp prompts, không trùng, từ 1 đến 40.');
  const patch=data.settings??{};
  if(!patch||typeof patch!=='object'||Array.isArray(patch))throw apiError(400,'settings không hợp lệ.');
  const choices: Record<string,readonly unknown[]>={accountMode:['single','multiple'],mode:['muse','demo'],model:['Omni 1.1 Flash','Veo 3.1 - Lite','Veo 3.1 - Fast'],aspectRatio:['16:9','9:16'],duration:[4,6,8,10],resolution:['360p','720p','1080p','2k','4k'],imageResolution:['2k','4k'],videoInput:['text','image'],r2v:[true,false],autoSync:[true,false]};
  for(const [key,value] of Object.entries(patch))if(['slotCount','requestedConcurrency'].includes(key)?!isSlotCount(value):key==='modifier'?typeof value!=='string'||value.length>2000:!choices[key]?.includes(value))throw apiError(400,`Thiết lập ${key} không hợp lệ.`);
  if(data.output!==undefined&&!['image','video'].includes(data.output))throw apiError(400,'output cần là image hoặc video.');
  const settings=normalizeSettings({...current,...patch,slotCount:Math.max(patch.slotCount??current.slotCount,...ids),output:data.output??current.output});
  if(patch.duration!==undefined&&settings.duration!==patch.duration)throw apiError(400,'Mô hình Veo yêu cầu thời lượng 8 giây.');
  if(data.referenceImage&&data.sourceMediaId)throw apiError(400,'Chỉ chọn referenceImage hoặc sourceMediaId.');
  if(data.referenceImage&&(!['image/png','image/jpeg','image/webp'].includes(data.referenceImage.mimeType)||typeof data.referenceImage.base64!=='string'||data.referenceImage.base64.length>11200000||! /^[A-Za-z0-9+/]+={0,2}$/.test(data.referenceImage.base64)))throw apiError(400,'referenceImage cần ảnh PNG/JPEG/WebP base64 tối đa 8 MB.');
  if(data.sourceMediaId!==undefined&&(typeof data.sourceMediaId!=='string'||! /^[a-f0-9-]{36}$/i.test(data.sourceMediaId)))throw apiError(400,'sourceMediaId không hợp lệ.');
  if(settings.output==='video'&&settings.videoInput==='image'&&!data.referenceImage&&!data.sourceMediaId)throw apiError(400,'Video từ ảnh cần referenceImage hoặc sourceMediaId.');
  return {prompts:prompts.map(prompt=>prompt.trim()) as string[],ids:ids as number[],settings};
}

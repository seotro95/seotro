import{parseScriptEntries}from'./script-import.ts';
export type ScriptFile={name:string;text:string};
type ReadableScript={name:string;size:number;text:()=>Promise<string>};
export async function readScriptFiles(files:readonly ReadableScript[]):Promise<ScriptFile[]>{
  if(!files.length)return[];
  if(files.length>400)throw new Error('Chọn tối đa 400 tệp TXT/SRT trong một lần.');
  if(files.some(file=>! /\.(txt|srt)$/i.test(file.name)))throw new Error('Chỉ nhận tệp TXT hoặc SRT UTF-8. Các tệp cũ trong bảng nhập vẫn được giữ.');
  if(files.some(file=>file.size>16*1024*1024))throw new Error('Mỗi tệp kịch bản tối đa 16 MB.');
  if(files.reduce((sum,file)=>sum+file.size,0)>32*1024*1024)throw new Error('Tổng các tệp kịch bản tối đa 32 MB mỗi lần nhập.');
  const collator=new Intl.Collator('vi',{numeric:true,sensitivity:'base'});
  const ordered=[...files].sort((a,b)=>collator.compare(a.name,b.name));
  const results=await Promise.allSettled(ordered.map(async file=>({name:file.name,text:await file.text()})));
  const failed=results.findIndex(result=>result.status==='rejected');
  if(failed>=0)throw new Error(`Không đọc được ${ordered[failed].name}. Chưa nạp thiếu một phần của nhóm tệp.`);
  return results.map(result=>(result as PromiseFulfilledResult<ScriptFile>).value);
}
export function parseScriptFiles(files:readonly ScriptFile[]){
  return files.map(file=>({...file,entries:parseScriptEntries(file.text)}));
}

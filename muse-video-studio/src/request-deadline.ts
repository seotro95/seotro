import{UI_WAIT_LIMIT_MS}from'../limits.mjs';
export async function withinDeadline<T>(work:(signal:AbortSignal)=>Promise<T>,signal:AbortSignal|undefined,timeoutMs:number=UI_WAIT_LIMIT_MS):Promise<T>{
  const control=new AbortController();const combined=signal?AbortSignal.any([signal,control.signal]):control.signal;
  const timer=setTimeout(()=>control.abort(new Error('MUSE_WAIT_LIMIT: Đã hết giới hạn 250 giây chờ. Tool đã dừng chờ; kiểm tra kết quả trong Muse trước khi tạo lại.')),timeoutMs);
  let abort:()=>void=()=>{};
  try{combined.throwIfAborted();const cancelled=new Promise<never>((_,reject)=>{abort=()=>reject(combined.reason);combined.addEventListener('abort',abort,{once:true})});return await Promise.race([work(combined),cancelled]);}
  finally{clearTimeout(timer);combined.removeEventListener('abort',abort)}
}

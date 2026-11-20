import{randomUUID,createHash}from'node:crypto';

// Collect the scene calls already admitted by the per-account scheduler. One
// composer submission carries the whole cohort, instead of interrupting the
// agent with a burst of separate user messages.
export class ChatBatches{
  constructor(run,{limit=()=>6,collectMs=500}={}){this.run=run;this.limit=limit;this.collectMs=collectMs;this.collecting=new Map();this.groups=new Set()}
  add(options){
    options.signal.throwIfAborted();
    const reference=options.image?createHash('sha256').update(options.image.base64).digest('hex'):'';
    const key=`${options.output}:${options.submissionGroup?.id||'automatic'}:${reference}`;
    let group=this.collecting.get(key);
    if(group&&group.control.signal.aborted&&!group.started){clearTimeout(group.timer);this.collecting.delete(key);this.groups.delete(group);group=null;}
    if(!group){group={key,rows:[],started:false,cancelled:false,control:new AbortController()};this.collecting.set(key,group);this.groups.add(group);group.timer=setTimeout(()=>this.flush(group),options.submissionGroup?Math.max(5000,this.collectMs):this.collectMs)}
    return new Promise((resolve,reject)=>{
      const row={...options,fileToken:'MUSE_'+randomUUID().replaceAll('-',''),createdAt:Date.now(),done:false};
      const finish=(error,value)=>{if(row.done)return;row.done=true;row.signal.removeEventListener('abort',abort);error?reject(error):resolve(value)};
      const abort=()=>{row.onStage?.('cancelled-provider');if(!group.started)finish(row.signal.reason);if(group.rows.every(item=>item.done||item.signal.aborted))group.control.abort(row.signal.reason)};
      row.resolve=value=>finish(null,value);row.reject=error=>finish(error);group.rows.push(row);row.signal.addEventListener('abort',abort,{once:true});row.onStage?.('waiting-cohort');
      const expected=Math.min(this.limit(),options.submissionGroup?.size||this.limit());
      if(group.rows.length>=expected)queueMicrotask(()=>this.flush(group));
    });
  }
  flush(group){
    if(group.started)return;group.started=true;clearTimeout(group.timer);if(this.collecting.get(group.key)===group)this.collecting.delete(group.key);
    const rows=group.rows.filter(row=>!row.done);
    if(!rows.length){this.groups.delete(group);return;}
    Promise.resolve().then(()=>this.run(rows,group)).catch(error=>rows.forEach(row=>row.reject(error))).finally(()=>{this.groups.delete(group);rows.forEach(row=>{if(!row.done)row.reject(new Error('MUSE_BATCH_INCOMPLETE: Lượt tạo kết thúc mà chưa có kết quả của ô.'))})});
  }
  cancelAll(reason=new Error('ABORTED: Đã đóng phiên Muse.')){for(const group of this.groups){group.cancelled=true;clearTimeout(group.timer);group.control.abort(reason);for(const row of group.rows)row.reject(reason)}this.collecting.clear();this.groups.clear()}
}

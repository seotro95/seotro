const error=text=>Object.assign(new Error('MUSE_PARALLEL_PREPARE_FAILED: '+text),{status:409});
// Rendezvous before Enter, never after generation. A cancelled member is removed
// from the wave; any preparation failure prevents the other unsent requests.
export class SubmitGroups {
 constructor({timeoutMs=90000}={}){this.groups=new Map();this.timeoutMs=timeoutMs}
 register(spec,batchId,sceneId,signal){
  if(!spec||spec.size===1)return null;
  const key=batchId+':'+spec.id;let group=this.groups.get(key);
  if(!group){group={size:spec.size,needed:spec.size,members:new Map(),closed:false};this.groups.set(key,group);group.timer=setTimeout(()=>this.fail(group,error('Các ô chưa chuẩn bị đủ để gửi cùng lượt. Chưa gửi prompt; không tự chuyển sang từng ô.')),this.timeoutMs);group.timer.unref?.()}
  if(group.closed||group.size!==spec.size||group.members.has(sceneId))throw error('Nhóm gửi hoặc số cảnh bị trùng/không khớp.');
  let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});promise.catch(()=>{});
  const member={ready:false,resolve,reject,signal,abort:null};group.members.set(sceneId,member);
  member.abort=()=>{if(group.closed)return;member.cancelled=true;group.needed--;signal.removeEventListener('abort',member.abort);reject(signal.reason||error('Đã hủy ô.'));this.release(group)};
  signal.addEventListener('abort',member.abort,{once:true});if(signal.aborted)member.abort();
  return {ready:()=>{if(!member.cancelled)member.ready=true;this.release(group);return promise},fail:reason=>this.fail(group,reason)};
 }
 release(group){if(!group.closed&&[...group.members.values()].filter(m=>m.ready&&!m.cancelled).length>=group.needed){group.closed=true;clearTimeout(group.timer);for(const m of group.members.values()){m.signal.removeEventListener('abort',m.abort);if(!m.cancelled)m.resolve()}this.prune()}}
 fail(group,reason){if(group.closed)return;group.closed=true;clearTimeout(group.timer);for(const m of group.members.values()){m.signal.removeEventListener('abort',m.abort);m.reject(reason)}this.prune()}
 prune(){if(this.groups.size<=128)return;for(const [key,g]of this.groups)if(g.closed){this.groups.delete(key);if(this.groups.size<=128)break}}
 clear(){for(const g of this.groups.values())this.fail(g,error('Phiên Muse đã đóng trước khi gửi.'));this.groups.clear()}
}

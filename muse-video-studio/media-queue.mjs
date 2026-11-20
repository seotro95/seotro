// Share the download/decode budget across all accounts. Render submission does
// not acquire this pool; sixty or more remote jobs can still overlap.
export class MediaQueue{
  constructor(limit=6){this.limit=limit;this.active=0;this.pending=[]}
  async run(work,signal){
    signal?.throwIfAborted();
    const release=await new Promise((resolve,reject)=>{
      const row={start:()=>{signal?.removeEventListener('abort',row.abort);this.active++;let done=false;resolve(()=>{if(done)return;done=true;this.active--;this.pump()})},abort:()=>{const index=this.pending.indexOf(row);if(index>=0)this.pending.splice(index,1);signal?.removeEventListener('abort',row.abort);reject(signal.reason)}};
      signal?.addEventListener('abort',row.abort,{once:true});this.pending.push(row);this.pump();
    });
    try{signal?.throwIfAborted();return await work()}finally{release()}
  }
  pump(){while(this.active<this.limit&&this.pending.length)this.pending.shift().start()}
  snapshot(){return {active:this.active,queued:this.pending.length,limit:this.limit}}
}
export const mediaQueue=new MediaQueue(6);

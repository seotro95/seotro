export async function prepareAccounts<T,R>(plans:readonly T[],prepare:(plan:T,index:number)=>Promise<R>,limit=3):Promise<R[]>{
  const results=new Array<R>(plans.length);let next=0;let failed=false;let failure:unknown;
  await Promise.all(Array.from({length:Math.min(Math.max(1,limit),plans.length)},async()=>{
    while(!failed&&next<plans.length){const index=next++;try{results[index]=await prepare(plans[index],index)}catch(error){failed=true;failure=error}}
  }));
  if(failed)throw failure;return results;
}

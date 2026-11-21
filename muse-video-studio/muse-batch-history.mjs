// Runs in the existing, authenticated Muse frame. Read only: never opens a
// conversation, edits a draft, presses Enter or asks Muse to generate again.
export function findSavedBatch({sceneId,prompt,output}){
  const normalize=value=>String(value||'').normalize('NFKC').replace(/\r\n/g,'\n').trim();
  const users=[...document.querySelectorAll('[data-message-item][data-message-role="user"]')];
  for(const user of users.reverse()){
    const text=user.textContent||'';
    const marker=text.match(/\[(studio-batch-[a-f0-9-]{36})\]/i)?.[1];
    if(!marker||!new RegExp('Create \\d+ independent '+output+' files?','i').test(text))continue;
    const rows=[...text.matchAll(/\[BEGIN_CLIP (CLIP_(\d{3})_[a-f0-9]{8}) (MUSE_[a-f0-9]{32})\]\n([\s\S]*?)\n\[END_CLIP \3\]/gi)].map(match=>{
      const body=match[4],split=body.startsWith('Use your ')?body.indexOf('\nScene:\n'):-1;
      return {label:match[1],sceneId:Number(match[2]),fileToken:match[3],prompt:normalize(split<0?body:body.slice(split+8))};
    });
    const target=rows.find(row=>row.sceneId===sceneId&&row.prompt===normalize(prompt));
    if(target)return {marker,rows:rows.map(({prompt,...row})=>row),fileToken:target.fileToken};
  }
  return null;
}

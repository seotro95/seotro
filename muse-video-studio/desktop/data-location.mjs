import {existsSync,mkdirSync,readFileSync,cpSync,renameSync,writeFileSync,rmSync} from 'node:fs';
import {mkdir,cp,rename,writeFile,stat,rm} from 'node:fs/promises';
import path from 'node:path';import {randomUUID} from 'node:crypto';
const recognized=directory=>['Partitions','Local State','account-vault','account-labels.json'].some(name=>existsSync(path.join(directory,name)));
const copyFilter=source=>!['SingletonLock','SingletonCookie','SingletonSocket','DevToolsActivePort','Cache','Code Cache','GPUCache','DawnCache','Crashpad'].includes(path.basename(source));
export function dataLocation({root,platform,isPackaged,localData,override}){
  if(override||platform!=='win32'||!isPackaged)return {directory:path.resolve(override||path.join(root,'.data','muse-desktop')),home:null};
  const home=path.join(localData,'Muse AI Studio');mkdirSync(path.join(home,'profiles'),{recursive:true});
  let relative='profiles/default';try{const saved=JSON.parse(readFileSync(path.join(home,'profile-location.json'),'utf8'));if(/^profiles\/[a-zA-Z0-9-]+$/.test(saved.profile)&&recognized(path.join(home,saved.profile)))relative=saved.profile}catch{}
  let directory=path.join(home,relative);const legacy=path.join(root,'.data','muse-desktop');
  if(!recognized(directory)&&recognized(legacy)){
    relative=`profiles/legacy-${randomUUID()}`;directory=path.join(home,relative);const staging=directory+'.importing';
    try{cpSync(legacy,staging,{recursive:true,filter:copyFilter});renameSync(staging,directory);const marker=path.join(home,'profile-location.json');writeFileSync(marker+'.tmp',JSON.stringify({profile:relative}),{mode:0o600});renameSync(marker+'.tmp',marker)}catch(error){rmSync(staging,{recursive:true,force:true});throw error}
  }
  return {directory,home};
}
export async function importData(location,selected,current){
  if(!location.home)throw new Error('MUSE_DATA_IMPORT_UNAVAILABLE: Chuyển dữ liệu tự động có trong bản Windows đầy đủ.');
  const choices=[path.join(selected,'resources/app/.data/muse-desktop'),path.join(selected,'.data/muse-desktop'),selected];
  const source=choices.find(directory=>recognized(directory));
  if(!source||path.resolve(source)===path.resolve(current))throw new Error('MUSE_DATA_IMPORT_INVALID: Chọn thư mục bản cũ chứa hồ sơ Muse khác với hồ sơ đang mở.');
  const profile=`profiles/import-${randomUUID()}`;const destination=path.join(location.home,profile);const staging=destination+'.importing';
  await mkdir(path.dirname(destination),{recursive:true});
  try{await cp(source,staging,{recursive:true,filter:copyFilter});if(!(await stat(staging)).isDirectory())throw new Error('MUSE_DATA_IMPORT_FAILED');await rename(staging,destination)}catch(error){await rm(staging,{recursive:true,force:true});throw error}
  const marker=path.join(location.home,'profile-location.json');
  await writeFile(marker+'.tmp',JSON.stringify({profile}),{mode:0o600});await rename(marker+'.tmp',marker);
  return destination;
}

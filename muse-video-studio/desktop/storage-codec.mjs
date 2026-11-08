// Backend selection is a Linux-only Electron API. Windows must use its OS
// encryptor without querying a desktop keyring backend.
export async function storageCodec(safeStorage,platform=process.platform){
  const asynchronous=await safeStorage.isAsyncEncryptionAvailable().catch(()=>false);
  const synchronous=!asynchronous&&platform==='win32'&&safeStorage.isEncryptionAvailable();
  let backend;
  if(platform==='linux'){try{backend=safeStorage.getSelectedStorageBackend?.()}catch{backend='unknown'}}
  return {isEncryptionAvailable:()=>asynchronous||synchronous,getSelectedStorageBackend:()=>backend,
    encryptString:value=>asynchronous?safeStorage.encryptStringAsync(value):safeStorage.encryptString(value),
    decryptString:async bytes=>asynchronous?(await safeStorage.decryptStringAsync(bytes)).result:safeStorage.decryptString(bytes)};
}

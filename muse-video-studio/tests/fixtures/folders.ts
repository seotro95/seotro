import type { BrowserContext, Page } from '@playwright/test';

export async function mockFolderPicker(context: BrowserContext) {
  await context.addInitScript(() => {
    const folders = new Map<string, any>();
    function directory(name: string): any {
      const children = new Map<string, any>(); const files = new Map<string, Blob>();
      return { name, files, children,
        async getDirectoryHandle(child: string, options?: { create?: boolean }) {
          if (!children.has(child)) {
            if (!options?.create) throw new DOMException('Not found','NotFoundError');
            children.set(child,directory(child)); if (name==='fixture-root') folders.set(child,children.get(child));
          }
          return children.get(child);
        },
        async getFileHandle(file: string, options?: { create?: boolean }) {
          if (!files.has(file) && !options?.create) throw new DOMException('Not found','NotFoundError');
          return {async createWritable(){let pending: Blob;return {async write(blob: Blob){pending=blob},async close(){files.set(file,pending)}}}};
        },
      };
    }
    const root=directory('fixture-root');
    (window as any).showDirectoryPicker=async()=>root;
    (window as any).fixtureFolderSnapshot=async()=>{
      const result=[];
      for(const [name,folder] of folders){
        const values=[];
        for(const [filename,blob] of folder.files){
          const bytes=new Uint8Array(await (blob as Blob).arrayBuffer());let binary='';
          for(let index=0;index<bytes.length;index+=8192)binary+=String.fromCharCode(...bytes.subarray(index,index+8192));
          values.push({name:filename,base64:btoa(binary)});
        }
        result.push({name,files:values});
      }
      return result;
    };
  });
}
export async function exportedFolders(page: Page): Promise<{ name: string; files: { name: string; bytes: Buffer }[] }[]> {
  const folders=await page.evaluate(()=>(window as any).fixtureFolderSnapshot());
  return folders.map((folder: any)=>({name:folder.name,files:folder.files.map((file: any)=>({name:file.name,bytes:Buffer.from(file.base64,'base64')}))}));
}

"""Split the existing numbered prompt TXT into ordered groups of ten."""
from pathlib import Path
import argparse,hashlib,re,zipfile

def split(source,out):
 blocks=re.split(r'\n\s*\n',source.read_text(encoding='utf-8-sig').strip())
 assert len(blocks)==184
 assert [b.split('\n',1)[0] for b in blocks]==[f'{i}.' for i in range(1,185)]
 out.mkdir(parents=True,exist_ok=True);folder=out/'batches';folder.mkdir(exist_ok=True)
 files=[];recombined=[]
 for offset in range(0,184,10):
  group=blocks[offset:offset+10];batch=offset//10+1
  path=folder/f'{batch:02}_PROMPT_{offset+1:03}-{offset+len(group):03}.txt'
  path.write_text('\n\n'.join(group)+'\n',encoding='utf-8-sig',newline='\r\n')
  back=re.split(r'\n\s*\n',path.read_text(encoding='utf-8-sig').strip())
  assert back==group and len(back)==(4 if batch==19 else 10)
  files.append(path);recombined.extend(back)
 assert len(files)==19 and recombined==blocks
 archive=out/'MUSE_19_TXT_MOI_TEP_10_PROMPT.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,Path('MUSE_19_TXT_MOI_TEP_10_PROMPT')/p.name)
 (out/'MUSE_19_TXT_SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in [*files,archive]),encoding='utf-8')
 print('Verified 19 TXT files: batches 01–18 contain 10 prompts each; batch 19 contains 181–184. All prompt text and numbering preserved.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path)
 a=p.parse_args();split(a.source,a.out)

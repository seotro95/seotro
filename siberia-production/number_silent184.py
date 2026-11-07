"""Number the owner's existing 184 published prompts without changing their text."""
from pathlib import Path
import argparse,hashlib,re

def number(source,destination):
 prompts=re.split(r'\n\s*\n',source.read_text(encoding='utf-8-sig').strip())
 assert len(prompts)==184
 assert all(p.startswith('Create one continuous 10-second,') and 'ABSOLUTELY SILENT' in p for p in prompts)
 result='\n\n'.join(f'{i}.\n{prompt}' for i,prompt in enumerate(prompts,1))+'\n'
 blocks=re.split(r'\n\s*\n',result.strip())
 assert [block.split('\n',1)[0] for block in blocks]==[f'{i}.' for i in range(1,185)]
 assert [block.split('\n',1)[1] for block in blocks]==prompts
 destination.parent.mkdir(parents=True,exist_ok=True)
 destination.write_text(result,encoding='utf-8-sig',newline='\r\n')
 digest=hashlib.sha256(destination.read_bytes()).hexdigest()
 destination.with_suffix('.SHA256.txt').write_text(digest+'  '+destination.name+'\n',encoding='utf-8')
 print(f'184 prompts numbered 1–184; original prompt text preserved. SHA-256: {digest}')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
 a=p.parse_args();number(a.source,a.destination)

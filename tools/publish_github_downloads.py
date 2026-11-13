"""Publish verified requested delivery files using Git's authenticated transport.

Uses an isolated bare repository and a new branch. Uploads at most two 16 MB
MP3 files per push to stay under ordinary request and GitHub file-size limits.
No GitHub API workaround, actions workflow, or change to the app checkout.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'github-delivery'
BARE = ROOT / 'github-publisher.git'
BRANCH = 'angkor-085-21m32s'
REMOTE = 'https://github.com/seotro95/seotro.git'
STATE = ROOT / 'validation/github-upload-state.json'
INDEX = ROOT / 'validation/github-publisher.index'
env = os.environ.copy()
env['GIT_INDEX_FILE'] = str(INDEX)

def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, env=env, **kwargs)

def git(*args, **kwargs):
    return run(['git', '--git-dir='+str(BARE), *args], **kwargs).stdout.strip()

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()

def save(state):
    temporary=STATE.with_suffix('.partial')
    temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(STATE)

def add(path):
    blob=git('hash-object','-w','--',str(path),text=True)
    git('update-index','--add','--cacheinfo','100644',blob,path.relative_to(STAGE).as_posix(),text=True)

def checksums():
    lines=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file() and path.name not in ['SHA256SUMS.txt','README-final.md']:
            lines.append(f'{sha(path)}  {path.relative_to(STAGE).as_posix()}')
    (STAGE/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
    add(STAGE/'SHA256SUMS.txt')

def push_commit(parent, message):
    tree=git('write-tree',text=True)
    args=['commit-tree',tree]
    if parent:args+=['-p',parent]
    commit=git(*args,input=message+'\n',text=True)
    git('update-ref','refs/heads/'+BRANCH,commit,text=True)
    result=run(['git','--git-dir='+str(BARE),'push','origin',commit+':refs/heads/'+BRANCH],text=True)
    print('Uploaded commit '+commit[:12]+': '+message,flush=True)
    return commit

def main():
    manifest=json.loads((ROOT/'DELIVERY_MANIFEST.json').read_text())
    assert len(manifest['files'])==17
    audio=[STAGE/row['file'] for row in manifest['files']]
    for row,path in zip(manifest['files'],audio):
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
        assert path.stat().st_size<100*1024*1024
    if not BARE.exists():
        run(['git','init','--bare',str(BARE)],text=True)
        git('remote','add','origin',REMOTE,text=True)
        for setting in ['user.name','user.email']:
            value=run(['git','-C','/workspace/seotro','config','--get',setting],text=True).stdout.strip()
            assert value
            git('config',setting,value,text=True)
    remote=git('ls-remote','--heads','origin','refs/heads/'+BRANCH,text=True)
    if STATE.exists():
        state=json.loads(STATE.read_text())
        assert state['branch']==BRANCH
        parent=state.get('last_pushed_commit')
        if remote:assert remote.split()[0]==parent,'Remote changed; inspect before continuing.'
        if state.get('status')=='uploaded' and all(state.get('uploaded_hashes',{}).get(row['language'])==row['sha256'] for row in manifest['files']):
            print('Delivery already uploaded; verify download URLs.',flush=True)
            return
    else:
        assert not remote,'Branch already exists; inspect rather than replace it.'
        state={'branch':BRANCH,'remote':REMOTE,'status':'uploading','uploaded_languages':[],
               'last_pushed_commit':None,'pushes':[]}
        parent=None
        git('read-tree','--empty',text=True)
        for path in sorted(STAGE.rglob('*')):
            if path.is_file() and path.name!='README-final.md' and path.suffix!='.mp3':add(path)
        parent=push_commit(None,'Add Angkor episode 85 delivery documents')
        state.update(last_pushed_commit=parent)
        state['pushes'].append({'commit':parent,'mp3s':0})
        save(state)
    for path in sorted(STAGE.rglob('*')):
        if path.is_file() and path.name!='README-final.md' and path.suffix!='.mp3':add(path)
    completed=set(state['uploaded_languages'])
    pending=[(row,path) for row,path in zip(manifest['files'],audio) if row['language'] not in completed or state.get('uploaded_hashes',{}).get(row['language'])!=row['sha256']]
    for offset in range(0,len(pending),2):
        batch=pending[offset:offset+2]
        for row,path in batch:add(path)
        count=len(completed)+len(batch)
        (STAGE/'README.md').write_text(f'# Angkor — tập 85 — 21:32\n\nĐang tải lên: **{count}/17 MP3**. Trang tải đầy đủ sẽ xuất hiện khi hoàn tất.\n')
        add(STAGE/'README.md')
        parent=push_commit(parent,f'Upload Angkor narration {count} of 17')
        completed.update(row['language'] for row,path in batch)
        state.setdefault('uploaded_hashes',{}).update({row['language']:row['sha256'] for row,path in batch})
        state.update(last_pushed_commit=parent,uploaded_languages=sorted(completed))
        state['pushes'].append({'commit':parent,'mp3s':count})
        save(state)
    # All MP3 blobs have reached GitHub before announcing the completed download page.
    final=json.loads((STAGE/'DELIVERY_MANIFEST.json').read_text())
    final.update(published=True,delivery_channel='GitHub',repository='seotro95/seotro',branch=BRANCH)
    for item in final['files']:
        item['download_url']=f'https://github.com/seotro95/seotro/raw/refs/heads/{BRANCH}/'+item['file']
    (STAGE/'DELIVERY_MANIFEST.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n')
    (STAGE/'README.md').write_text((STAGE/'README-final.md').read_text())
    add(STAGE/'README.md');add(STAGE/'DELIVERY_MANIFEST.json');checksums()
    parent=push_commit(parent,'Complete Angkor download page with 17 verified MP3s')
    state.update(status='uploaded',last_pushed_commit=parent,
                 page_url=f'https://github.com/seotro95/seotro/tree/{BRANCH}',
                 archive_url=f'https://github.com/seotro95/seotro/archive/refs/heads/{BRANCH}.zip')
    save(state)
    print(json.dumps({'status':'uploaded','mp3s':17,'page_url':state['page_url'],'archive_url':state['archive_url']}),flush=True)

if __name__=='__main__':main()

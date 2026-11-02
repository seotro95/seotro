"""Copy only declared, pinned model files from a local update pack."""
import json,shutil,sys
from pathlib import Path
from local_models import catalog as multi_catalog,digest
from fast_backend import catalog as piper_catalog

def install(source,root):
    source=Path(source);root=Path(root);pack=source/'voice-pack';file=pack/'PACK.json'
    piper={m['id']:m for m in piper_catalog()};multi=multi_catalog()
    declared=json.loads(file.read_text()) if file.is_file() else {'piper':[k for k,m in piper.items() if m.get('bundled',True)],'multi':[]}
    if set(declared)!={'piper','multi'} or any(not isinstance(declared[k],list) or not all(isinstance(v,str) for v in declared[k]) or len(declared[k])!=len(set(declared[k])) for k in declared):raise ValueError('Danh sách mô hình trong gói không hợp lệ.')
    records=[]
    for kind,catalog in [('piper',piper),('multi',multi)]:
        for key in declared[kind]:
            if key not in catalog:raise ValueError('Mô hình không thuộc danh mục đã xác minh: '+key)
            relative=Path('models/piper')/key if kind=='piper' else Path('models')/key
            records.append((relative,catalog[key]))
    # Validate every source file before changing any installed model.
    for relative,record in records:
        for name,sha in record['files'].items():
            src=pack/relative/name
            if not src.is_file() or digest(src)!=sha:raise ValueError('Sai/thiếu mô hình trong gói: '+str(relative/name))
    for relative,record in records:
        dst=root/relative;dst.mkdir(parents=True,exist_ok=True)
        for name,sha in record['files'].items():
            target=dst/name
            if target.is_file() and digest(target)==sha:continue
            tmp=target.with_name(target.name+'.install.partial');shutil.copyfile(pack/relative/name,tmp);tmp.replace(target)
        print('Đã sẵn sàng mô hình CPU:',relative.name,flush=True)
    model_license=pack/'models/supertonic3/LICENSE-MODEL'
    if 'supertonic3' in declared['multi'] and model_license.is_file():
        shutil.copyfile(model_license,root/'models/supertonic3/LICENSE-MODEL')
if __name__=='__main__':install(*sys.argv[1:])

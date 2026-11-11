from __future__ import annotations
import hashlib,json,os,re,shutil,urllib.request,zipfile
from pathlib import Path
from .common import Context,binary,data_dir,save_json

def ensure_ffmpeg(ctx: Context):
    try:
        binary('ffmpeg');binary('ffprobe');return
    except RuntimeError:
        if os.name!='nt':raise
    ctx.emit(0,'Lần đầu: tải FFmpeg chính thức từ bản phát hành;không cần cài thủ công.')
    api='https://api.github.com/repos/FFmpeg-Builds/FFmpeg-Builds/releases/latest'
    request=urllib.request.Request(api,headers={'User-Agent':'AutoDocStudio/1.0','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=60) as response:release=json.load(response)
    options=[]
    for a in release.get('assets',[]):
        m=re.fullmatch(r'ffmpeg-n(\d+)\.(\d+)-latest-win64-gpl-shared-[\d.]+\.zip',a['name'])
        if m:options.append(((int(m[1]),int(m[2])),a))
    if not options:raise RuntimeError('Chưa tìm được FFmpeg Windows phù hợp. Đặt ffmpeg.exe/ffprobe.exe và DLL đi kèm vào thư mục bin.')
    asset=max(options,key=lambda x:x[0])[1];expected=asset.get('digest','')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',expected):raise RuntimeError('Bản FFmpeg không có SHA256;không tải bản chưa xác minh.')
    cache=data_dir();archive=cache/'ffmpeg-download.zip.part';h=hashlib.sha256();size=0
    with urllib.request.urlopen(asset['browser_download_url'],timeout=90) as response,archive.open('wb') as out:
        while True:
            ctx.check();b=response.read(1024*1024)
            if not b:break
            out.write(b);h.update(b);size+=len(b)
            ctx.emit(min(1.5,size/max(1,asset['size'])*1.5),f'Tải FFmpeg: {size//1048576}/{asset["size"]//1048576}MB')
    if size!=asset['size'] or 'sha256:'+h.hexdigest()!=expected:
        archive.unlink(missing_ok=True);raise RuntimeError('Tải FFmpeg chưa đủ hoặc hash không khớp. Kiểm mạng rồi chạy lại.')
    stage=cache/'ffmpeg-stage';stage.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP FFmpeg bị hỏng.')
        for info in z.infolist():
            p=Path(info.filename)
            if '..' in p.parts or p.is_absolute():raise RuntimeError('Đường dẫn ZIP không hợp lệ.')
            if info.is_dir():continue
            keep=(p.parent.name=='bin' and (p.suffix.lower()=='.dll' or p.name in ['ffmpeg.exe','ffprobe.exe'])) or p.name.lower().startswith(('license','copying','readme'))
            if keep:
                with z.open(info) as src,(stage/p.name).open('wb') as out:shutil.copyfileobj(src,out)
    if not all((stage/n).is_file() for n in ['ffmpeg.exe','ffprobe.exe']):raise RuntimeError('ZIP thiếu FFmpeg/ffprobe.')
    target=cache/'bin';target.mkdir(exist_ok=True)
    for p in stage.iterdir():p.replace(target/p.name)
    stage.rmdir();archive.unlink(missing_ok=True)
    save_json(cache/'FFMPEG_PROVENANCE.json',{'release':release['html_url'],'asset':asset['name'],'sha256':h.hexdigest(),'downloaded_directly_from_upstream':True})
    ctx.run([binary('ffmpeg'),'-version'],log=cache/'ffmpeg_version.log');ctx.run([binary('ffprobe'),'-version'],log=cache/'ffprobe_version.log')

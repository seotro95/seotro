import hashlib,json,os,shutil,subprocess,zipfile
from pathlib import Path
P=Path('productions/video-08-baishiya');O=Path('document-delivery');O.mkdir(exist_ok=True);TAG='baishiya-video-08-22m20s';REPO=os.environ['GITHUB_REPOSITORY']
archive=P/'BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='1d49eade5314221f470a1c0a0e84e5d22c0df181f9d670eea9920481f4811254'
shutil.copy(archive,O/archive.name)
for p in [P/'KICH_BAN_EN_22m20s.txt',P/'KICH_BAN_EN_CO_MOC.txt',P/'PHAN_TICH_NGUON_VA_QUY_TRINH.txt']+sorted((P/'PROMPTS').glob('*.txt')):
 shutil.copy(p,O/('BAISHIYA_08_'+p.name))
notes='''# Baishiya — chủ đề8,22:20

Bàn giao tài liệu trước voice: kịch bản tiếng Anh3162từ/134mốc10s;120prompt mới/12TXT,đúng10prompt mỗiTXT;14mốcREUSEcóCSVđánh dấu;hook12shottrong30svoiceđầu. Tất cảclipimlặng,khônghìnhtrẻem,chỉngườitrưởngthànhrõ25–60tuổi.

Tải ZIP để có kịch bản sạch,có mốc,SRT,timeline,12TXTprompt,nguồn kiểm chứng và quy trình. CácTXT cũng cótảiriêng ởAssets.

17voiceđangchuẩnbị:16nam,H’MôngTrắngnữ3,cùngID/styleđãlưu. Chưa cóclip8,chưa dựngvideo8. NghiêncứuchínhXiaetal.2024,Nature,DOI10.1038/s41586-024-07612-9,CCBY4.0;diễngiảimới,khôngsaochéphình. Kếtquảtập1–4,6giữnguyên;tập5,7vẫnqueued.
'''
(O/'NOTES.md').write_text(notes)
if subprocess.run(['gh','release','view',TAG,'--repo',REPO],capture_output=True).returncode:subprocess.run(['gh','release','create',TAG,'--repo',REPO,'--target','705eb9241c9ba969c7a9b6726bdfe5eb07dc8e34','--title','Baishiya Topic08 —22m20s original script and120 silent video prompts','--draft','--notes-file',str(O/'NOTES.md')],check=True)
for p in O.iterdir():
 if p.suffix in ['.txt','.zip']:subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--draft=false','--latest=false'],check=True)
print('Document release published;17voices not yet claimed',flush=True)

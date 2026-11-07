"""Export the existing 227 scene prompts as TXT and 23 small Muse projects."""
from pathlib import Path
import hashlib,json,shutil,zipfile

base=Path(__file__).resolve().parent
kit=base/'kit'
plan=json.loads((kit/'shot_plan.json').read_text(encoding='utf-8'))
out=Path('muse-prompt-delivery');out.mkdir(exist_ok=True)
folder=out/'MUSE_23_BATCHES';(folder/'batches').mkdir(parents=True,exist_ok=True)
shots=plan['shots'];assert len(shots)==227 and sum(s['frames'] for s in shots)==46080
all_text='\n\n'.join(s['prompt'] for s in shots)+'\n'
(out/'MUSE_227_PROMPTS.txt').write_text(all_text,encoding='utf-8')
shutil.copyfile(out/'MUSE_227_PROMPTS.txt',folder/'MUSE_227_PROMPTS.txt')
shutil.copyfile(kit/'SHOT_LIST.csv',folder/'SHOT_LIST.csv')
shutil.copyfile(kit/'shot_plan.json',folder/'shot_plan.json')
batch_rows=[]
for offset in range(0,len(shots),10):
 number=offset//10+1;group=shots[offset:offset+10]
 project=kit/'muse-projects'/f'video-{number:02}.json'
 data=json.loads(project.read_text(encoding='utf-8'))
 assert data['version']==1 and len(data['scenes'])==10
 assert [s['prompt'] for s in data['scenes'] if s['enabled']]==[s['prompt'] for s in group]
 shutil.copyfile(project,folder/'batches'/project.name)
 (folder/'batches'/f'video-{number:02}.txt').write_text('\n\n'.join(s['prompt'] for s in group)+'\n',encoding='utf-8')
 batch_rows.append(f'| {number:02} | {offset+1}–{offset+len(group)} | {len(group)} |')
readme='''# Prompt tạo video Siberia bằng Muse 1.6.0

Đây là toàn bộ 227 prompt cảnh cho kịch bản mới dài 25:36. Các tệp là hướng dẫn tạo cảnh, chưa phải video đã tạo.

## Cài đặt

- Chế độ Muse thật; đầu ra Video; đầu vào văn bản.
- Model yêu cầu: Omni 1.1 Flash.
- Tỉ lệ 16:9; độ phân giải yêu cầu 1080p; thời lượng yêu cầu 10 giây mỗi clip.
- Dùng giọng Anh đã xuất riêng khi dựng; bỏ âm thanh gốc của các clip tạo sinh.

## Dùng từng bộ

Mở `batches/video-01.json` bằng chức năng nhập dự án của Muse, nếu phiên bản của bạn có chức năng này. Hoặc mở `batches/video-01.txt`, dán lần lượt 10 đoạn vào 10 ô cảnh. Một đoạn là một prompt. Mỗi lượt dùng một bộ; tiếp tục video-02 đến video-23.

Tệp `MUSE_227_PROMPTS.txt` chứa tất cả prompt để đọc và sao chép. Hãy dùng các tệp theo bộ khi làm việc với giao diện chỉ có 10 ô cảnh. Bộ 23 có 7 cảnh; 3 ô cuối trong dự án JSON được tắt.

## Ghép đúng thời lượng

227 clip yêu cầu 10 giây cung cấp phần media dư để cắt và làm chuyển cảnh. Không ghép nguyên tất cả clip 10 giây thành bản cuối. `SHOT_LIST.csv` và `shot_plan.json` ghi thời điểm và số frame cần dùng; bản dựng chuẩn là 46.080 frame ở 30 fps, đúng 25:36.

Các hình tạo sinh là minh họa. So hình địa danh với nguồn tham khảo; các sơ đồ và cảnh tái dựng phải được ghi nhãn phù hợp khi dựng. Clip do Muse trả về cần được kiểm tra thời lượng và độ nét thực tế.

| Bộ | Số cảnh | Số ô dùng |
|---|---|---|
'''+ '\n'.join(batch_rows)+'\n'
(folder/'README_VI.md').write_text(readme,encoding='utf-8')
(out/'MUSE_PROMPTS_README_VI.md').write_text(readme,encoding='utf-8')
archive=out/'MUSE_23_BATCHES.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(folder.rglob('*')):
  if p.is_file():z.write(p,Path(folder.name)/p.relative_to(folder))
checks=''.join(hashlib.sha256((out/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in ['MUSE_227_PROMPTS.txt','MUSE_23_BATCHES.zip','MUSE_PROMPTS_README_VI.md'])
(out/'MUSE_PROMPTS_SHA256SUMS.txt').write_text(checks,encoding='utf-8')
print(json.dumps({'prompt_count':len(shots),'batches':23,'zip_bytes':archive.stat().st_size,'target_seconds':1536}))

import json,subprocess
from pathlib import Path
R=Path(__file__).parent;D=R/'verified-release/details';manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());assert manifest['voice_count']==17
base='https://github.com/seotro95/seotro/releases/download/baishiya-video-08-22m20s/'
notes='''# Baishiya: The Survival Story Hidden in Broken Bones

Chủ đề8 đã có kịch bản và17voice riêng, mỗi bản22:20 sau giải mã. Giữ16giọngnam vàH’MôngTrắngnữ3, đúngID và mẫu giọng đã lưu. Video chính dùng tiếngAnh.

'''
notes+=f'[Tải ZIP đủ17voice]({base}BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip) · [Tải kịch bản và12TXTprompt]({base}BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip) · [Hồ sơ giọng]({base}BAISHIYA_08_HO_SO_GIONG_TEN_QUOC_GIA.zip)\n\n'
notes+='Kịch bản Anh3.162từ,134mốc10giây;120prompt mới trong12TXT,đúng10prompt mỗi tệp;14mốcREUSE có đánh dấu. Mọi clip im lặng,không có hình trẻ em ở bất kỳ đâu. Hook12shot nằm trong30giây voice đầu,không cộng intro.\n\n| Quốc gia / ngôn ngữ | Giọng | Tải riêng |\n|---|---|---|\n'
for m in manifest['voices']:notes+=f'| {m["name"]} | {m["voice_id"]} | [MP3]({base}{m["filename"]}) |\n'
notes+='\nMỗi MP3 đã được kiểm tra đúng64.320.000mẫu khi giải mã ở48kHz=1.340giây. BảnAnh căn134ô10giây;bản dịch căn12chương:hai chương120giây,mười chương110giây. Đồng bộ chương và tổng,không đồng bộ từng từ giữa các ngôn ngữ.\n\n'
notes+='Đã sửa thuật ngữ khoa học và rà câu chưa dịch;giữ mã giọng,nhấn nhá,cao độ và mẫu tham chiếu. Bản dịch,nghe và phương ngữH’MôngTrắng vẫn cần người bản ngữ rà soát độc lập. Chưa dựngvideo8 vì chưa nhậnclip của tập này.\n\n'
notes+='Nguồn khoa học chính:Xia và cộng sự(2024),Nature632,108–113,DOI[10.1038/s41586-024-07612-9](https://doi.org/10.1038/s41586-024-07612-9),CCBY4.0. Kịch bản diễn giải mới,không sao chép hình hoặc lời của video tham khảo. Danh sách nguồn và giới hạn bằng chứng có trongZIP tài liệu.\n'
# Keep prose readable in both browser and downloaded Markdown.
for a,b in [('17voice','17 voice'),('16giọngnam','16 giọng nam'),('H’MôngTrắng','H’Mông Trắng'),('nữ3','nữ 3'),('tiếngAnh','tiếng Anh'),('3.162từ','3.162 từ'),('134mốc10giây','134 mốc 10 giây'),('120prompt','120 prompt'),('12TXT','12 TXT'),('10prompt','10 prompt'),('14mốcREUSE','14 mốc REUSE'),('12shot','12 shot'),('30giây','30 giây'),('64.320.000mẫu','64.320.000 mẫu'),('1.340giây','1.340 giây'),('48kHz','48 kHz'),('134ô10giây','134 ô 10 giây'),('12chương','12 chương'),('120giây','120 giây'),('110giây','110 giây'),('video8','video 8'),('Chủ đề8','Chủ đề 8'),('mỗi bản22:20','mỗi bản 22:20')]:notes=notes.replace(a,b)
p=R/'RELEASE_NOTES_FINAL.md';p.write_text(notes)
subprocess.run(['gh','release','edit','baishiya-video-08-22m20s','--repo','seotro95/seotro','--title','Baishiya Topic08 —17 expressive voices,22m20s','--notes-file',str(p),'--latest=false'],check=True)
print('Release title and notes now reflect completed17voice delivery')

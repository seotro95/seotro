import json
from pathlib import Path
R=Path(__file__).parent
qa=json.loads((R/'PUBLIC_DOWNLOAD_QA.json').read_text());assert qa['status']=='passed' and qa['voice_count']==17
base='https://github.com/seotro95/seotro/releases/download/saqqaq-hair-video-91-22m12s/'
body=f'''# Chủ đề 91 — Tóc Saqqaq và ADN Bắc Cực — 22:12

**The Hair That Changed Arctic History**

[Tải đủ 17 giọng ZIP]({base}SAQQAQ_HAIR_91_17_VOICES_22m12s.zip) · [Kịch bản và 12 TXT prompt]({base}SAQQAQ_HAIR_91_TAI_LIEU_22m12s.zip) · [5 tiêu đề và 5 prompt thumbnail]({base}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản nguyên bản có 3.703 từ Anh, 134 mốc: 133 mốc dài 10 giây và 2 giây cuối. Có 120 prompt tạo clip mới trong 12 TXT, đúng 10 prompt/TXT. Đã đánh dấu 14 mốc dùng lại. Mỗi prompt cấm trẻ em, thiếu niên, lời nói và âm thanh. Nhân vật đều là người hiện đại trưởng thành. Tóc, mô hình phân tử và địa hình là minh họa, không phải mẫu thật, dữ liệu đo, chân dung hoặc tuyến di cư đã xác nhận.

Đã có **17 MP3 riêng: 16 nam và nữ H’mông female-3**. Mỗi bản được tải lại public, kiểm SHA và giải mã đúng **1.332 giây = 63.936.000 mẫu ở 48 kHz**. Việt dùng đúng **Nam Minh — vi-VN-NamMinhNeural** qua backend online Melo + Việt Studio 1.3.1. H’mông dùng công cụ riêng Voice-Studio-Hmong 1.6.6, mẫu nữ female-3 cố định. Giữ đủ 17 ID từ tập 71; không sửa audio của các tập trước.

Anh căn 134 mốc. Các bản dịch căn 14 chương chung: 13 × 100 giây + 32 giây cuối. Cùng thời lượng không có nghĩa từng từ đồng thời. SRT bản dịch theo chương cần chia nhỏ trước khi hiển thị. Việt và H’mông được viết lại đủ 14 chương. Các bản khác được địa phương hóa từ phần nội dung chính của mỗi chương, lược chuyển ý lặp để giữ nhịp đọc tự nhiên; đã rà ngày tháng, đơn vị, thuật ngữ và các ý khoa học chính. Chưa có kiểm nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.

Câu chuyện theo tóc Saqqaq từ Qeqertasussuk qua bảo tồn, định tuổi, xác thực ADN và lịch sử cư dân. Phân biệt công bố ty thể năm 2008, genome nhân năm 2010, khung nghiên cứu năm 2014/2019 và hướng epigenome năm 2014. Tuổi mẫu không phải tuổi di cư; văn hóa không phải nhãn gen; dự đoán tính trạng không phải ảnh thật. Không khẳng định mọi dòng tổ tiên liên quan đều biến mất.

Chưa có footage hoặc MP4 tập 91. Khi có clip, 10 cảnh mạnh trong 30 giây đầu nằm trong tổng 22:12. Phim chính chỉ voice Anh, xóa âm clip, không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh/thẻ chữ.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
manifest=json.loads((R/'AUDIO_MANIFEST.json').read_text())
for v in manifest['voices']:body+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 22:12 |\n"
(R/'README.md').write_text(body)
guide='''CHỦ ĐỀ 91 — TÓC SAQQAQ VÀ ADN BẮC CỰC — 22:12

1. Tạo 120 clip dài 10 giây từ 12 TXT trong PROMPTS. Đặt tên 001.mp4 đến 120.mp4 theo ID prompt, không theo ID mốc lời.
2. TIMELINE_134_CANH.csv nối 134 mốc lời với clip. Có 14 mốc REUSE trong CAC_CANH_DUNG_LAI.txt. Mốc cuối lấy 2 giây từ clip 001.
3. Mỗi prompt cấm lời nói, âm thanh, trẻ em và thiếu niên. Mọi nhân vật/bàn tay phải rõ 35–65 tuổi. Không hình trẻ em trong nền, bóng, ảnh, màn hình, phản chiếu hoặc mô hình. Không dựng người sở hữu tóc hoặc chân dung cổ xác thực. Tóc/mô hình là vật liệu minh họa hiện đại, không mẫu thật hoặc dữ liệu đo.
4. Đã có 17 MP3 tên quốc gia/ngôn ngữ, giữ 17 ID từ tập 71. Việt dùng NamMinhNeural nam; H’mông female-3 nữ qua công cụ riêng 1.6.6; 15 giọng khác nam. Backend Melo 1.3.1 dùng cho 16 giọng online.
5. Mỗi voice được tải lại, kiểm SHA và giải mã đúng 63.936.000 mẫu ở 48 kHz, tương đương 1.332 giây. Anh căn 134 mốc; bản dịch căn 14 chương: 13×100 giây+32 giây. Không khẳng định từng từ đồng thời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.
6. Voice giữ ID và cao độ, có ngắt nghỉ/nhấn nhá vừa phải. Việt/H’mông viết lại 14 chương; các bản khác địa phương hóa nội dung chính theo chương và rà thuật ngữ, ngày tháng. Chưa có kiểm nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.
7. Chưa có footage hoặc MP4 tập 91. Khi có clip, chọn 10 cảnh mạnh trong 30 giây đầu khớp voice Anh; intro nằm trong tổng 22:12. Xóa âm clip, không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh đứng/thẻ chữ.
8. Nội dung phân biệt ty thể 2008, genome nhân 2010, nghiên cứu lịch sử 2014/2019 và epigenome 2014. Tuổi tóc không phải tuổi di cư; mô hình không phải GPS; dự đoán tính trạng không phải ảnh; một người không đại diện toàn bộ Bắc Cực.
9. Giữ hồ sơ giọng v3 từ tập 71 và quy trình đã lưu. Không tự đổi giọng hoặc tạo lại audio đã xong. Link riêng từng giọng nằm trong README.md và AUDIO_MANIFEST.json.
'''
(R/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
print('Final91download text prepared from public verification')

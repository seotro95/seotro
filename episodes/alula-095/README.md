# Chủ đề 95 — AlUla: Rock, Water, and Ancient Routes

Đã tạo 17 bản voice riêng, mỗi bản giải mã đúng **20:42 (1.242 giây)**.
Tiếng Anh Andrew là bản chính; tiếng Việt dùng Nam Minh. Tất cả các giọng là
nam, ngoại trừ Hmong Trắng nữ 3 theo yêu cầu. Xem VOICE_PROFILES_LOCKED.json
để dùng lại cùng mã giọng và mẫu tham chiếu trong các tập sau.

## Dùng prompt và dựng phim

- Thư mục prompts có 13 TXT đánh số liên tục 1–125: 12 tệp đầu mỗi tệp 10
  prompt, tệp cuối 5 prompt. Mỗi prompt đều yêu cầu im lặng và không trẻ em.
- Tạo cả 125 clip dài 10 giây. Dùng đủ cảnh 1–124; cảnh 125 chỉ lấy 2 giây
  đầu. Tổng 20:42. Ưu tiên cắt thẳng trên lưới; fade kết nằm trong 2 giây cuối.
- Góc quay, cỡ cảnh và chuyển động đã viết riêng theo nội dung từng cảnh.
  Không bật âm thanh do mô hình video tạo; loại track đó trước khi ghép voice.
- Cảnh lịch sử và sơ đồ là tái dựng/minh họa. Khi xuất phim nên gắn nhãn thích
  hợp trong phần dựng; không giới thiệu chúng là footage cổ hoặc bằng chứng mới.
- Kịch bản Anh–Việt có mốc giờ; scripts chứa lời TXT sạch, SRT và JSON cho 17
  ngôn ngữ. Không đưa phần tiêu đề và chỉ dẫn sân khấu vào công cụ đọc.
- 5_TIEU_DE_VA_5_THUMBNAIL.txt chứa 5 cặp tiêu đề và prompt thumbnail; đây là
  prompt ảnh, chưa phải ảnh hoặc phim đã được tạo.

## Voice và kiểm tra

Backend của Melo-Viet Studio 1.3.1 và Voice Studio Hmong 1.6.6 được chạy trên
Linux Cloud. Không tuyên bố đã vận hành giao diện/BAT Windows trong phiên này.
Anh/Việt dùng nhánh Edge của Melo; các bản khác dùng Piper hoặc Supertonic như
hồ sơ đã lưu; Hmong dùng Native VITS + OpenVoice V2, female-3, clear-v1.
Anh được bổ sung adapter chia lô nhỏ theo mốc từ của cùng thư viện Edge để
giảm lỗi kết nối; mã giọng, tốc độ và cao độ gốc được giữ. Chỉ những lô có
metadata khớp toàn bộ lời mới được tách. Không dùng âm thanh tập cũ thay thế.

17 bản đều khớp 124 ô lời và thêm 2 giây cuối không lời. Đã đối chiếu script,
mã giọng, SHA-256, số mẫu giải mã MP3 và master FLAC. Mỗi bản có 29.808.000
mẫu mono ở 24 kHz. Một số trình phát có thể hiển thị thêm phần đệm MP3; độ
dài giải mã có xử lý gapless vẫn là 1.242 giây. Master FLAC được giữ tại workspace.

Bản dịch đã rà nội dung và thuật ngữ trọng điểm; chưa có lượt nghe duyệt toàn
bộ bởi người bản ngữ. Riêng phát âm Hmong Trắng cần người bản ngữ nghe kiểm
tra trước khi đăng. Không xem kiểm tra kỹ thuật là chứng nhận phát âm.

Nguồn công cụ:
- https://github.com/seotro95/seotro/releases/tag/melo-viet-studio-1.3.1-txt-srt-41595029816
- https://github.com/seotro95/seotro/releases/tag/voice-studio-hmong-1.6.6

Nguồn video, phương pháp quan sát và tài liệu kiểm chứng nằm trong các tệp
PHAN_TICH_VIDEO_NGUON.md và NGUON_KIEM_CHUNG.md.

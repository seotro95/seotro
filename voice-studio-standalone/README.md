# Voice Studio Riêng 1.2 · Đa quốc gia, ưu tiên tốc độ trên CPU

Bản Portable Windows 10/11 x64 đóng gói sẵn Python, FFmpeg và các mô hình. Giải nén toàn bộ ZIP rồi mở `MO_TOOL.bat`. Liên kết bản đã kiểm tra nằm trong [trang tải](../downloads/voice-studio/README.md).

- Nhân bản tiếng Việt mặc định Nano 4 bước, tự chọn số đoạn xử lý song song theo CPU/RAM, giữ mẫu giọng đã chọn. Có thể đổi sang 8/16 bước hoặc Tiêu chuẩn để nghe và so sánh chất lượng.
- Thêm 16 giọng Piper theo quốc gia: Mỹ, Anh, Pháp, Đức, Tây Ban Nha, Ý, Brazil, Nga, Hà Lan, Bỉ, Ba Lan, Thụy Điển, Ukraine, Séc, Đan Mạch và Romania. Các giọng này chạy offline trên CPU và có sẵn trong Portable.
- Tìm ngôn ngữ/quốc gia, lọc giọng; tạo lời đọc, kể chuyện, bản tin, review từ kịch bản của bạn. Piper là giọng có sẵn; nhân bản trong Portable hỗ trợ tiếng Việt.
- Nhập tối đa **200.000 ký tự**, TXT/SRT; xuất WAV/MP3/TXT/SRT; dừng/tiếp tục, lưu lịch sử và ghép các đoạn thành bản thu hoàn chỉnh.
- **Ưu tiên tốc độ** giữ giọng và ngôn ngữ quốc tế đã chọn. **Đo tốc độ thực** dùng đoạn mẫu đúng ngôn ngữ, không thay nội dung đang soạn.

Nano 4 bước có thể giảm độ tự nhiên hoặc độ giống mẫu; hãy nghe thử. Tốc độ phụ thuộc máy và mô hình. Kết quả đo bản 1.2 trên Linux 4 lõi: 64 phút 55,5 giây WAV nhân bản trong 82,9 giây; chưa phải kết quả trên máy Windows của bạn. Xem [HIEU_NANG.md](HIEU_NANG.md).

Khi cập nhật: tắt tool, sao lưu `app/.data`, giải nén bản mới sang thư mục mới. Chuyển các thư mục con `voices`, `jobs`, `audio`, `parts` từ bản cũ vào `app/.data` mới nếu cần giữ mẫu/lịch sử; giữ các mô hình đi kèm bản mới.

Nếu chạy **mã nguồn** thay vì Portable: cài Python 3.12 x64, chạy `CAI_DAT.bat`, `TAI_GIONG_NHAN_BAN_NHANH.bat` và `TAI_GIONG_QUOC_TE_NHANH.bat` trước khi mở tool. Qwen quốc tế/nhân bản quốc tế là thành phần tùy chọn riêng, không kèm trong Portable CPU.

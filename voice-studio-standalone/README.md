# Voice Studio Riêng 1.1 · Nhân bản tiếng Việt trên CPU

Windows 10/11 x64, Python 3.12. Gói mã nguồn kèm bộ cài, tải mô hình ở lần đầu.

Nếu mới dùng: giải nén toàn bộ ZIP rồi chạy `CAI_DAT.bat`.

**Giọng nhân bản nhanh:**

1. Chạy `TAI_GIONG_NHAN_BAN_NHANH.bat` một lần.
2. Chạy `MO_TOOL.bat`, chọn mẫu giọng cá nhân tiếng Việt.
3. Bấm **Ưu tiên tốc độ**, rồi **Tạo giọng nói**. Mẫu giọng đang chọn được giữ nguyên.
4. Dùng **Đo tốc độ thực** để đo trên máy của bạn; chọn 8/16 bước hoặc nhân bản tiêu chuẩn nếu cần chất lượng cao hơn.

Máy thử 4 lõi CPU / 32 GiB RAM tạo **64 phút 56,6 giây WAV trong 80,5 giây**, tổng tạo WAV + xuất MP3 **92,1 giây**. Đây là kết quả với Nano 4 bước trên máy thử Linux, không phải cam kết trên mọi máy Windows. Chưa đánh giá độ giống người nói thật hoặc phát âm từng từ.

Cập nhật từ bản cũ: tắt tool và sao lưu `app/.data`; chép tệp mới vào thư mục tool, giữ `.venv` và `app/.data`, rồi chạy bộ tải nhân bản nhanh. Xem [DOC_TRUOC.md](DOC_TRUOC.md) để biết hướng dẫn đầy đủ và [HIEU_NANG.md](HIEU_NANG.md) để biết cách đo.

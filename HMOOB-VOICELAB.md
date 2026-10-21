# Hmoob VoiceLab — tool mới cho văn bản dài

**Tạm ngừng phát hành ZIP 1.0:** Windows Defender trên máy người dùng đã chặn gói `Hmoob-VoiceLab-1.0-source.zip` với tên `Trojan:Script/Ulthar.A!ml`. Chưa xác minh được nguyên nhân hoặc kết luận cảnh báo nhầm. Không khôi phục/cho phép tệp bị chặn hoặc tắt bảo vệ để chạy. Xem [kết quả điều tra](hmoob-voicelab/SECURITY-REVIEW.md).

Mã nguồn độc lập tại [hmoob-voicelab](hmoob-voicelab/README.md). Nhập tối đa **1.000.000 ký tự**, hàng đợi có thể dừng/tiếp tục, đầu ra thành nhiều chương WAV và ZIP. Windows dùng Python 3.12 64-bit, chạy `start.bat`; cài bộ tạo giọng bằng `install_voice.bat`.

Ngày 21/10/2026: **59 kiểm thử đạt**, mô hình đã tải và xác minh checksum trên cloud; tác vụ F5-Hmong thật chạy ngoại tuyến đã tạo WAV từ mẫu công khai và cả hai giọng mặc định. Đã sửa tiếp tục khi checkpoint hỏng và tốc độ câu ngắn. Hai giọng mặc định đã có lời và mốc được người dùng nghe xác nhận: **Nữ 0–5,30 giây; Nam 0–4,50 giây**. Bản đọc AI thử mới dài **4,128 giây (nữ)** và **3,819 giây (nam)**, lưu trong Lịch sử của tool. Chưa đánh giá phát âm, độ giống giọng hoặc đọc dài bằng mô hình thật. Xem hướng dẫn và kết quả kiểm thử trong `VALIDATION.md` của tool. Trạng thái tạm ngừng phát hành ZIP vẫn giữ nguyên.

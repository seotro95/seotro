# Hmoob VoiceLab — tool mới cho văn bản dài

**Tạm ngừng phát hành ZIP 1.0:** Windows Defender trên máy người dùng đã chặn gói `Hmoob-VoiceLab-1.0-source.zip` với tên `Trojan:Script/Ulthar.A!ml`. Chưa xác minh được nguyên nhân hoặc kết luận cảnh báo nhầm. Không khôi phục/cho phép tệp bị chặn hoặc tắt bảo vệ để chạy. Xem [kết quả điều tra](hmoob-voicelab/SECURITY-REVIEW.md).

Mã nguồn độc lập tại [hmoob-voicelab](hmoob-voicelab/README.md). Nhập tối đa **1.000.000 ký tự**, hàng đợi có thể dừng/tiếp tục, đầu ra thành nhiều chương WAV và ZIP. Windows dùng Python 3.12 64-bit, chạy `start.bat`; cài bộ tạo giọng bằng `install_voice.bat`.

Phần ứng dụng đã kiểm thử. **Chưa xác minh tạo voice Hmong thật hoặc tốc độ**: máy cloud hiện bị proxy chặn tải mô hình Hugging Face (CONNECT 403); cần tải đủ trọng số và nhập lời khớp đoạn giọng mẫu. Xem hướng dẫn và `VALIDATION.md` trong thư mục tool.

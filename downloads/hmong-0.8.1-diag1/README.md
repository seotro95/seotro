# Hmong Voice Studio 0.8.1 DIAG-1 — bản đầy đủ

[Tải ZIP đầy đủ](./HMONG_VOICE_STUDIO_0.8.1_DIAG_1_DAY_DU.zip?raw=true).

1. Giải nén vào **thư mục mới có quyền ghi**; không chèn hoặc ghi đè bản cũ.
2. Đóng Studio cũ, mở thư mục `Hmong-Voice-Studio-0.8.1-DIAG-1`.
3. Bấm **CHAY-STUDIO.bat** và chờ bộ cài hoàn tất, trình duyệt tự mở.

Máy cần Python 3.10–3.12 64-bit (khuyên dùng 3.12). Lần đầu cần Internet
để tự cài thư viện và tải/xác minh khoảng **5,4 GB mô hình**. Gói có đầy đủ
ứng dụng, giao diện, hai mẫu giọng và bản vá chẩn đoán; không đóng sẵn Python
hoặc trọng số AI để chạy offline ngay. Dữ liệu bản cũ không cần chuyển sang.

Bản vá giữ nhật ký khi tiến trình tạo voice dừng, hiển thị mã thoát, ghi traceback
và thử lại khi Windows tạm khóa tệp kết quả. Nếu vẫn lỗi, gửi ảnh thông báo
và file `voice-*.log` mới nhất trong `.data/logs` của bản mới. Kiểm tra log
trước khi chia sẻ; không gửi API key.

Đã đạt 26 kiểm thử tác vụ/chẩn đoán và 47 kiểm thử bộ cài/khởi động trên Linux;
kiểm tra ZIP sau giải nén đạt cho giao diện, tài nguyên và API trạng thái.
Kiểm thử bộ cài dùng mô phỏng tải/cài; chưa thử Windows hoặc inference CosyVoice
thật. Chưa xác định nguyên nhân gốc khiến CosyVoice dừng trên máy người dùng.

`SHA256SUMS.txt` chứa mã kiểm tra gói ZIP.

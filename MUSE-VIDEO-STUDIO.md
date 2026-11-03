# Muse Video Workstation — bản web độc lập

[Tải gói ZIP cho Windows/Linux/macOS](https://github.com/seotro95/seotro/raw/refs/heads/main/Muse-Video-Workstation.zip) · [Mã nguồn và hướng dẫn](muse-video-studio/README.md)

Giao diện 10 slot dựng theo ảnh và mô tả Flow: nhập TXT/SRT, đồng bộ ảnh nhân vật, quản lý nhãn 10 tài khoản, điều phối hàng đợi tuần tự, dừng/tiếp tục, xem trước và tải video.

**Phần tạo video AI thật chưa được kết nối.** Người dùng xác nhận bản gốc tạo qua Flow; chưa có API Muse.ai tương ứng hoặc adapter thực tế để thay thế runtime Flow. Nhập email không đăng nhập tài khoản. Không có tích hợp Gemini. Chế độ kiểm thử dùng clip có nhãn, không tạo video từ prompt.

## Chạy trên máy tính

1. Cài Node.js 24 trở lên từ https://nodejs.org/.
2. Tải và giải nén ZIP, mở thư mục `Muse-Video-Workstation`.
3. Windows: chạy `start.bat`. Linux/macOS: chạy `bash start.sh`.
4. Mở địa chỉ cục bộ máy chủ in ra. Giữ cửa sổ chạy; Ctrl+C để dừng.

Lần đầu cần Internet để cài thư viện. Gói có sẵn bản build. Launcher Windows chưa được chạy trên Windows thật.

Build, 8 kiểm thử trình duyệt và các kiểm thử logic/máy chủ đã qua trên Linux. Kiểm thử API dùng adapter giả cục bộ, không chứng minh tạo video thật qua Muse.ai. Xem [kết quả xác minh](muse-video-studio/VALIDATION.md) và [hợp đồng adapter](muse-video-studio/README.md#kết-nối-adapter-muse-phía-máy-chủ).

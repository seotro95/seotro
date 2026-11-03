# Muse Video Workstation — bản web độc lập 1.0.1

[Tải gói ZIP cho Windows/Linux/macOS](https://github.com/seotro95/seotro/raw/refs/heads/main/Muse-Video-Workstation.zip) · [Mã nguồn và hướng dẫn](muse-video-studio/README.md)

Giao diện 10 slot dựng theo ảnh và mô tả người dùng: nhập TXT/SRT, đồng bộ ảnh nhân vật, quản lý nhãn 10 tài khoản, điều phối hàng đợi tuần tự, dừng/tiếp tục, xem trước và tải video.

**Phần tạo video AI thật chưa được kết nối.** Bản này chỉ dành cho Muse AI và chế độ kiểm thử có nhãn. Chưa có API/adapter Muse.ai thực tế hoặc cơ chế xác thực tài khoản được kiểm chứng. Nhập email không đăng nhập tài khoản. Tính năng tạo video chỉ bật khi có khai báo adapter, và vẫn cần kiểm tra quyền truy cập thật.

## Chạy trên máy tính

1. Cài Node.js 24 trở lên từ https://nodejs.org/.
2. Tải và giải nén ZIP, mở thư mục `Muse-Video-Workstation`.
3. Windows: chạy `start.bat`. Linux/macOS: chạy `bash start.sh`.
4. Trình duyệt tự mở sau khi máy chủ sẵn sàng. Giữ cửa sổ chạy; Ctrl+C chỉ dùng khi muốn tắt tool. Nếu cần, mở thủ công địa chỉ máy chủ in ra.

Lần đầu cần Internet để cài thư viện. Gói có sẵn bản build. Launcher Windows chưa được chạy trên Windows thật.

Xem kết quả build, kiểm thử trình duyệt và logic/máy chủ trên Linux trong báo cáo xác minh. Kiểm thử API dùng adapter giả cục bộ, không chứng minh tạo video thật qua Muse.ai. Xem [kết quả xác minh](muse-video-studio/VALIDATION.md) và [hợp đồng adapter](muse-video-studio/README.md#kết-nối-adapter-muse-phía-máy-chủ).

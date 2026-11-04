# Muse AI Video Workstation 1.1.0

[Tải ZIP Windows/Linux/macOS](https://github.com/seotro95/seotro/raw/refs/heads/main/Muse-Video-Workstation.zip) · [Mã nguồn và hướng dẫn](muse-video-studio/README.md)

Bản 1.1.0 có cầu nối đăng nhập tài khoản Muse bằng Chrome/Edge riêng cho từng slot. Bạn tự đăng nhập trong cửa sổ do tool mở; tool dùng phiên đó để gửi prompt/ảnh và nhận video mới. Không cần tự dựng adapter cho phương án này.

**Đây là kết nối trình duyệt không chính thức, đã kiểm thử với trang giả lập, chưa xác minh đăng nhập và render thật trên Muse.ai.** Mô hình/thời lượng/khung hình được gửi dưới dạng yêu cầu trong prompt; cần xem video trả về để kiểm tra khả năng thực tế của tài khoản.

1. Cài Node.js 24+ và Google Chrome hoặc Microsoft Edge.
2. Giải nén ZIP vào thư mục mới, chạy `start.bat` trên Windows hoặc `bash start.sh` trên Linux/macOS có giao diện đồ họa.
3. Trong tool chọn **10 Tài khoản Muse → Kết nối #1**.
4. Đăng nhập Muse trong cửa sổ được mở → quay lại tool bấm **Kiểm tra phiên #1**.
5. Khi có **Đã xác minh**, tạo thử một cảnh. Kết nối thêm các slot để chạy hàng loạt.

Phiên lưu cục bộ trong `.data/muse-accounts`, không nằm trong ZIP hoặc dự án JSON. Không chia sẻ thư mục này. Email trong bảng chỉ là nhãn, không thay thế đăng nhập. Giữ cửa sổ máy chủ chạy khi dùng tool.

Nếu Muse đổi giao diện hoặc tài khoản không có khả năng tạo video, tool sẽ báo lỗi; không dùng clip mẫu để giả lập thành công. Chế độ kiểm thử riêng luôn có nhãn. Có thể dùng adapter API riêng ở cấu hình nâng cao.

Xem [kết quả xác minh](muse-video-studio/VALIDATION.md). Launcher Windows chưa được chạy trên Windows thật.

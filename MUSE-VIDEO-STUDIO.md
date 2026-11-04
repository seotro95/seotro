# Muse AI Video Workstation 1.2.0

[Tải ZIP Windows/Linux/macOS](https://github.com/seotro95/seotro/raw/refs/heads/main/Muse-Video-Workstation.zip) · [Mã nguồn và hướng dẫn](muse-video-studio/README.md)

Bản 1.2.0 có cầu nối đăng nhập tài khoản Muse bằng Chrome/Edge riêng cho từng slot. Bạn tự đăng nhập trong cửa sổ do tool mở; tool dùng phiên đó để gửi prompt/ảnh và nhận video mới. Không cần tự dựng adapter cho phương án này.

**Đây là kết nối trình duyệt không chính thức, đã kiểm thử với trang giả lập, chưa xác minh đăng nhập và render thật trên Muse.ai.** Mô hình/thời lượng/khung hình được gửi dưới dạng yêu cầu trong prompt; cần xem video trả về để kiểm tra khả năng thực tế của tài khoản.

1. Cài Node.js 24+ và Google Chrome hoặc Microsoft Edge.
2. Giải nén ZIP vào thư mục mới, chạy `start.bat` trên Windows hoặc `bash start.sh` trên Linux/macOS có giao diện đồ họa.
3. Trong tool chọn **10 Tài khoản Muse → Kết nối #1**.
4. Đăng nhập Muse trong cửa sổ được mở → quay lại tool bấm **Kiểm tra phiên #1**.
5. Khi có **Đã xác minh**, bật **Tự dùng chung cho ô chưa gán tài khoản**. Các cảnh có thể tạo bằng một phiên này; không cần đăng nhập 10 lần. Có thể gán riêng từng cảnh nếu muốn.

Phiên lưu cục bộ trong `.data/muse-accounts`, không nằm trong ZIP hoặc dự án JSON. Không chia sẻ thư mục này. Email trong bảng chỉ là nhãn, không thay thế đăng nhập. Giữ cửa sổ máy chủ chạy khi dùng tool.

Bản này có tab **Tạo ảnh hàng loạt** từ prompt/TXT/SRT, mức yêu cầu 2K/4K và tùy chọn giữ nhân vật. Video có chế độ **Từ prompt / Từ ảnh**, mức 720p/1080p/2K/4K. Bộ ảnh đã tạo có thể chuyển sang ảnh đầu vào video mà không mất kết quả ảnh.

Bảng token/credit chỉ hiển thị số đọc được từ vùng số dư Muse có nhãn và thời điểm đọc. Nếu không có số tin cậy sẽ ghi **Chưa đọc được**. Tệp trả thấp hơn độ phân giải yêu cầu được đánh dấu rõ; không tự gắn nhãn 4K khi chưa đạt kích thước.

Nếu Muse đổi giao diện hoặc tài khoản không có khả năng tạo video, tool sẽ báo lỗi; không dùng clip mẫu để giả lập thành công. Chế độ kiểm thử riêng luôn có nhãn. Có thể dùng adapter API riêng ở cấu hình nâng cao.

Xem [kết quả xác minh](muse-video-studio/VALIDATION.md). Launcher Windows chưa được chạy trên Windows thật.

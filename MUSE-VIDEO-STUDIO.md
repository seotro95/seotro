# Muse AI Studio 1.4.3 · 10 luồng đồng thời

[Tải ZIP mới](https://github.com/seotro95/seotro/raw/refs/heads/main/Muse-Video-Workstation.zip) · [Hướng dẫn đầy đủ](muse-video-studio/README.md)

**Bản 1.4.3 sửa nút tạo bị khóa dù đã đăng nhập.** Phiên Muse được API xác minh sẽ mở nút tạo; mỗi cảnh tự mở cuộc trò chuyện và tìm ô Message riêng. Hỗ trợ ô Message ngoài khung giao diện cũ. Đóng hẳn tool cũ trước khi giải nén bản mới đè các tệp chương trình; giữ nguyên `.data` và `.env`.

**Một tài khoản Muse, tối đa 10 luồng ảnh/video chạy đồng thời trong các cuộc trò chuyện riêng. Đăng nhập ngay trong cửa sổ tool bằng tab Muse tích hợp; không cần cài hoặc mở Chrome riêng.**

1. Đóng tool cũ, giải nén ZIP mới, chạy `start.bat` (cần Node.js 24+; lần đầu cần Internet để tải runtime Electron chính thức).
2. Bấm **Đăng nhập Muse trong tool**, hoàn tất đăng nhập trực tiếp trên trang Muse.
3. Bấm **← Về Studio**, đợi **Đã xác minh**; có thể bấm Kiểm tra phiên để cập nhật thủ công.
4. Nhập 10 prompt hoặc TXT/SRT, chọn ảnh/video, bấm **TẠO 10 ẢNH / TẠO 10 VIDEO**.

Số luồng hiện tại được hiển thị. Có thể dừng toàn bộ, chạy lại phần chưa xong, tải từng kết quả hoặc cả bộ. Giữ các chức năng ảnh 2K/4K, đồng nhất nhân vật, video từ prompt/ảnh, yêu cầu độ nét 720p/1080p/2K/4K và bảng số dư đọc được từ Muse.

Bản 1.3 chạy tuần tự; bản 1.4 thay cả giao diện, máy chủ và các cuộc trò chuyện xử lý song song. Kênh gửi desktop tránh giới hạn 6 kết nối HTTP/1 của trình duyệt tới localhost. Mọi luồng dùng cùng một phiên, không cần các tài khoản khác.

**Kết nối không chính thức; đã xác minh trên Electron thật với dịch vụ giả lập, chưa xác minh đăng nhập hoặc tạo media trên Muse.ai thật.** Muse có thể giới hạn render đồng thời hoặc không chấp nhận đăng nhập nhúng. Độ nét/model là yêu cầu qua prompt, không phải cam kết khả năng của dịch vụ. Xem [kết quả kiểm thử](muse-video-studio/VALIDATION.md).

Không có phiên người dùng trong ZIP/Git. Phiên desktop lưu cục bộ trong `.data/muse-desktop`; không chia sẻ thư mục đó. Đăng nhập Chrome của bản cũ không tự chuyển sang Electron; dữ liệu cũ không bị xóa. Launcher Windows chưa được chạy trên Windows thật.

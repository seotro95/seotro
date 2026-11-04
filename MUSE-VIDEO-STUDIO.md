# Muse AI Video Workstation 1.3.0 — một tài khoản

[Tải ZIP Windows/Linux/macOS](https://github.com/seotro95/seotro/raw/refs/heads/main/Muse-Video-Workstation.zip) · [Mã nguồn và hướng dẫn](muse-video-studio/README.md)

**Chỉ đăng nhập một tài khoản Muse. Bấm TẠO 10 VIDEO hoặc TẠO 10 ẢNH một lần, tool tự chạy cả bộ trên cùng phiên đó.** Không còn email từng ô, danh sách 10 tài khoản, gán riêng hoặc chọn tài khoản dùng chung.

1. Đóng máy chủ của bản cũ, giải nén ZIP mới. Cần Node.js 24+ và Chrome hoặc Edge.
2. Chạy `start.bat` trên Windows hoặc `bash start.sh` trên Linux/macOS có desktop.
3. Bấm **Kết nối Muse**, đăng nhập trong cửa sổ được mở rồi **Kiểm tra phiên**.
4. Nhập 10 prompt hoặc TXT/SRT, chọn ảnh/video, rồi bấm nút **Tạo 10** một lần.

Các cảnh được xử lý lần lượt để không lẫn phản hồi trong cùng phiên. Đây không phải cam kết Muse xử lý đồng thời 10 tác vụ. Cảnh chờ được ghi rõ; có thể dừng và tiếp tục phần chưa xong. Cấu hình gán tài khoản của bản cũ được bỏ qua khi mở dự án.

Giữ các chức năng: số dư token/credit có nhãn, ảnh hàng loạt 2K/4K, bật/tắt đồng nhất nhân vật, video từ prompt hoặc ảnh với mức 720p/1080p/2K/4K, chuyển bộ ảnh sang video, xem/tải kết quả và dự án JSON. Nếu Muse chưa hiển thị số dư hoặc trả tệp thấp hơn mức yêu cầu, tool báo rõ.

**Kết nối trình duyệt không chính thức; đã kiểm thử bằng trang giả lập, chưa xác minh trên tài khoản Muse thật.** Khả năng tạo media, tốc độ, hạn mức và đầu ra 4K do Muse quyết định. Không có dữ liệu phiên trong ZIP/Git. Thư mục phiên cũ trên máy bạn không bị tự xóa.

Xem [kết quả xác minh](muse-video-studio/VALIDATION.md). Launcher Windows chưa chạy trên máy Windows thật.

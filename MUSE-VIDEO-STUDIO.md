# Muse AI Studio 1.4.6 · Bản Windows đầy đủ

[Bản Windows x64 đầy đủ](Muse-AI-Studio-Windows-x64.zip) · [Mã nguồn đầy đủ](Muse-Video-Workstation.zip) · [Hướng dẫn](muse-video-studio/README.md)

1. Giải nén **toàn bộ** bản Windows vào một thư mục mới.
2. Mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần Node.js, npm, Chrome hoặc bản cũ.
3. Đăng nhập Muse ngay trong tool, bấm **← Về Studio** rồi **Kiểm tra phiên**.
4. Nhập prompt hoặc TXT/SRT, chọn ảnh/video, bấm **TẠO 10 ẢNH / VIDEO**.

Không chép `.data`, `.env`, `node_modules` hoặc tệp chương trình từ bản cũ. Gói mới có runtime và các thư viện cần thiết; tạo hồ sơ đăng nhập mới khi chạy. Thanh trên và tiêu đề cửa sổ hiện **1.4.6**.

Bản này xử lý ô Message vẫn giữ nhãn `prehydration`, chuyển ô nhập sau ký tự đầu và kiểm tra giữ đủ prompt trước khi nhấn gửi. Rich editor đang hiện được ưu tiên. Nếu Muse chưa xác nhận nhận prompt, tool báo riêng và không tự gửi lại.

Một tài khoản, tối đa 10 luồng ảnh/video của tool; hạn mức thực tế, mô hình, độ nét và khả năng tạo media do Muse quyết định. Kết nối giao diện không chính thức. Kiểm thử dùng dịch vụ giả lập; chưa xác minh tự động trên tài khoản Muse thật. Xem [kết quả kiểm thử](muse-video-studio/VALIDATION.md).

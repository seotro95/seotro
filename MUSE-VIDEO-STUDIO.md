# Muse AI Studio 1.7.0 · Hai chế độ tài khoản

[Bản Windows x64 đầy đủ](Muse-AI-Studio-Windows-x64.zip) · [Mã nguồn](Muse-Video-Workstation.zip) · [Hướng dẫn](muse-video-studio/README.md)

Bản 1.7.0 thêm **Cổng API** để công cụ cùng máy điều khiển Studio, **Xóa toàn bộ** thư viện và mặc định **hai luồng** khi dùng một tài khoản (sau khi xác minh hai hội thoại riêng). Xem [hướng dẫn API](muse-video-studio/API-AUTOMATION.md).

Giải nén toàn bộ gói vào thư mục mới, mở **Muse AI Studio.exe**. Không cần bản cũ, Node.js, npm hoặc Chrome riêng.

- **1 tài khoản · tối đa 10 luồng**: giữ chế độ cũ, cả 10 ô dùng Muse 01. Chọn số luồng và kiểm tra các hội thoại riêng trước khi bật song song.
- **10 tài khoản · mỗi tài khoản 1 luồng**: Muse 01 cho ô 01, Muse 02 cho ô 02…; cookie và dữ liệu đăng nhập tách biệt. Bấm Tạo 10 để gửi đồng thời trên những tài khoản đã xác minh.

Bấm **Quản lý 10 tài khoản**, nhập danh sách email/tên (mỗi dòng một tài khoản) hoặc nhập TXT; đăng nhập từng tài khoản trong tool. Danh sách chỉ đặt nhãn, không thay thế xác thực. Khi mở lại, bấm **Kiểm tra 10 phiên** để đọc lại các phiên đã lưu. Không nhập mật khẩu, OTP, cookie/token vào danh sách.

Giữ nguyên xem ảnh trong Studio, lịch sử từng ô, Tạo/Dừng riêng, TXT/SRT, đồng nhất nhân vật, ảnh → video, lưu thư mục thường, đánh số tiếp và dùng các chức năng khác trong khi tạo. Không chuyển chế độ tài khoản giữa một tác vụ Muse đang chạy.

Kiểm thử dùng dịch vụ mô phỏng cục bộ; Muse quyết định tốc độ và quyền tạo nội dung trên tài khoản thật. Không tự đổi tài khoản khi hết hạn mức hoặc gửi lại yêu cầu. Xem [kết quả kiểm thử](muse-video-studio/VALIDATION.md).

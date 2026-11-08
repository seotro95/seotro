# Muse AI Studio 1.10.0 — bản Windows đầy đủ

1. Đóng bản Studio cũ. Giải nén toàn bộ ZIP 1.10.0 vào thư mục mới, rồi mở **Muse AI Studio.exe**.
2. Nếu đã có tài khoản ở bản cũ: mở **Tài khoản Muse → Chuyển dữ liệu bản cũ**, chọn **thư mục chứa EXE cũ**. Tool sao chép cả hồ sơ tài khoản, nhãn, thư viện, số thứ tự tải và cấu hình API sang nơi lưu mới, rồi tự mở lại. Hồ sơ gốc và hồ sơ hiện tại được giữ; không chép đè chúng. Bạn cũng có thể chọn trực tiếp thư mục hồ sơ `resources/app/.data/muse-desktop` của bản cũ.
3. Chọn **nhiều tài khoản · mỗi tài khoản một luồng**, **10 ô**. Nhập prompt/TXT/SRT và bấm tạo.
4. Trong **Tài khoản Muse**, bấm **Lưu tất cả tài khoản** nếu muốn ghi ngay. Mỗi tài khoản hiện thời điểm lưu riêng; app còn tự lưu sau xác minh, khi cookie thay đổi, định kỳ và trước khi thoát.

## Video đã có trên Muse nhưng tool cứ chờ

Bản trước đợi `readyState`/metadata của trình phát và đợi nút Stop biến mất. Một số video có `preload=none`, hoặc Muse còn viết phần chữ sau khi video đã xong, nên tool có thể chờ đến timeout dù tệp đã có.

Bản 1.10 lấy nguồn video/thẻ source/liên kết tải trong **đúng lượt trả lời của cảnh**, tải và kiểm tra cấu trúc tệp MP4/MOV/WebM, không cần bạn bấm Play. Phần lưu phiên/đọc số dư không chặn đường khởi chạy render. Mười tài khoản vẫn gửi mười yêu cầu độc lập; không tự gửi lại prompt để tránh tạo trùng.

## Lưu đủ các tài khoản và đổi thư mục cài

Gói Windows đầy đủ lưu mặc định trong **`%LOCALAPPDATA%\Muse AI Studio`**, độc lập với thư mục giải nén EXE. Mở bản đầy đủ mới ở thư mục khác vẫn dùng lại nơi lưu này. Nút **Mở nơi lưu tài khoản** cho biết vị trí đang sử dụng. Gói mã nguồn chạy `npm start` vẫn dùng thư mục `.data` hiện có; biến `MUSE_DESKTOP_DATA` nếu đã cấu hình vẫn được ưu tiên.

Mỗi tài khoản có partition và bản lưu mã hóa riêng. Phần mã hóa Windows không gọi hàm chọn keyring chỉ dành cho Linux; dùng API mã hóa hệ điều hành phù hợp. Các dữ liệu phiên không xuất vào log, dự án JSON hoặc MCP.

Chỉ nhập email vào danh sách chưa phải đăng nhập: email là nhãn phân công. Từng tài khoản cần được xác minh một lần. Tool tự khôi phục các phiên **còn hiệu lực**; không kéo dài hạn đăng nhập do Muse quyết định. Phiên đã hết hạn/bị thu hồi, hoặc chưa được bản cũ ghi lại, cần đăng nhập lại tài khoản đó. Giữ cùng máy và tài khoản Windows để đọc dữ liệu mã hóa.

Bản đầy đủ có Electron/Node và thư viện; không cần Node.js, Chrome riêng hoặc bản cũ để chạy mới. Chức năng đồng bộ, proxy tùy tài khoản, 20/30/40 ô, thư viện, tải thư mục và cổng API/MCP được giữ. Tốc độ render ở phía Muse vẫn phụ thuộc dịch vụ; phần sửa này xử lý tool chậm nhận tệp đã có. Kiểm thử dùng dịch vụ giả lập, chưa thao tác tài khoản Muse thật của bạn trong cloud này.

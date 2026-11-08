# Muse AI Studio 1.9.0 · Tối đa 40 ô / luồng yêu cầu

[Cập nhật bản 1.8.0 → 1.9.0](Muse-AI-Studio-Update-1.9.0.zip) · [Cách cập nhật, giữ tài khoản](muse-video-studio/CAP-NHAT-1.9.md) · [Bản Windows x64 đầy đủ](Muse-AI-Studio-Windows-x64.zip) · [Mã nguồn](Muse-Video-Workstation.zip) · [Hướng dẫn](muse-video-studio/README.md) · [API](muse-video-studio/API-AUTOMATION.md) · [Codex MCP](muse-video-studio/MCP-CODEX.md) · [MIT](muse-video-studio/LICENSE)

Giải nén toàn bộ vào thư mục mới rồi mở **Muse AI Studio.exe**. Không cần bản cũ, Node.js hoặc Chrome riêng.

- **Số luồng: 20 / 30 / 40** hiện đúng 20 / 30 / 40 ô theo thứ tự. Nút Tạo, tiến độ, nhập TXT/SRT và tải thư mục dùng đúng số ô.
- Thu nhỏ rồi mở rộng giữ prompt/kết quả; lưu lại lựa chọn khi mở lại. Có thể thay đổi riêng Số ô để chạy một kịch bản dài bằng ít luồng hơn.
- **Một tài khoản**: tối đa 40 hội thoại đã kiểm tra. Nếu Muse chưa hỗ trợ hội thoại độc lập, giữ lựa chọn và chạy hàng đợi theo số luồng thực sự dùng được, có cảnh báo rõ ràng.
- **Nhiều tài khoản**: tối đa 40 tài khoản, mỗi tài khoản một ô/một luồng. Nhập danh sách email/tên rồi đăng nhập từng phiên trong tool.
- **Mã nguồn mở MIT + MCP**: Codex trên cùng máy có thể đọc/sửa ô, tạo/dừng và lưu kết quả. Có nút sao chép cấu hình MCP, hướng dẫn và mẫu TOML.
- Giữ cổng API cùng máy, Tạo/Dừng từng ô, lịch sử, xem ảnh trong Studio, xóa toàn bộ thư viện và tải thư mục với số thứ tự tăng tiếp.

Số render thực sự cùng lúc do Muse quyết định. Kiểm thử dùng dịch vụ mô phỏng; không khẳng định tài khoản thật có thể chạy 40 render. Phiên chat cloud không kết nối trực tiếp cổng 127.0.0.1 trên máy Windows của người dùng. Xem [xác minh](muse-video-studio/VALIDATION.md).

Bản 1.9: nút đồng bộ BẬT/TẮT và chọn từng ô, cài đặt/ảnh riêng; phiên lưu mã hóa và tự khôi phục; proxy HTTP/HTTPS hoặc SOCKS5 không mật khẩu tùy tài khoản. Mỗi tài khoản dùng lại tab Muse đã tải, giảm mở trang/xác minh thừa.

# Cập nhật Muse AI Studio 1.8.0 lên 1.9.0

Gói `Muse-AI-Studio-Update-1.9.0.zip` dùng cho bản Windows đầy đủ 1.8.0 đã tải trước đây. Không cần cài Node.js hoặc tải lại runtime. Giữ nguyên thư mục cũ để tiếp tục dùng dữ liệu đã đăng nhập.

1. Hoàn tất hoặc dừng các lượt tạo, rồi đóng **toàn bộ cửa sổ Muse AI Studio**.
2. Giải nén gói cập nhật vào một thư mục tạm. Không chạy ngay trong WinRAR/ZIP.
3. Chạy **CAP_NHAT.bat**. Chọn **thư mục cũ có `Muse AI Studio.exe`**, không chọn `resources/app`.
4. Đợi thông báo hoàn tất, rồi mở lại **EXE trong thư mục cũ**.

Updater kiểm tra SHA256, sao lưu các tệp mã sẽ thay thế vào `backup-code-*` và chỉ chép mã mới. Thư mục **`resources/app/.data`** được giữ tại chỗ, gồm hồ sơ đăng nhập từng tài khoản, thư viện ảnh/video, prompt, khóa API, thư mục xuất và số thứ tự tải. `.env` cũng không bị thay thế. Không xóa hoặc gửi thư mục `.data` cho người khác.

Nếu dùng bản mã nguồn `npm start`, giải nén mã nguồn mới đè lên thư mục mã cũ, giữ nguyên `.data` và `.env`, rồi chạy `npm.cmd install` và `npm.cmd run build` trước khi mở lại. Cập nhật bằng BAT chỉ dành cho gói EXE 1.8.0/1.9.0.

## Đồng bộ thao tác

- **Đồng bộ thao tác: BẬT**: chọn ô bằng checkbox **Đồng bộ** trong từng cảnh. Thay cài đặt trên thanh đầu hoặc gán ảnh sẽ áp dụng cho các ô đã chọn. **Đồng bộ ngay từ ô N** chép cả cài đặt và ảnh từ ô đang chỉnh sang nhóm.
- **TẮT**: chọn **Ô đang chỉnh**, cài đặt/ảnh chỉ thay ở ô đó. Các ô khác giữ cài đặt riêng.
- **Tạo ô đã chọn / Dừng ô đã chọn** điều khiển nhóm. Nút Tạo/Dừng trong từng ô vẫn điều khiển riêng; TẠO N ở đầu vẫn tạo mọi ô đang bật và đủ điều kiện.
- Tác vụ đang chạy dùng bản chụp cài đặt lúc bắt đầu. Bạn có thể sửa, nhập prompt, xem và tải kết quả cho lượt sau.

## Phiên đăng nhập và tốc độ nhiều tài khoản

Mỗi tài khoản vẫn có hồ sơ riêng. Bản mới ghi thêm cookie phiên và sessionStorage vào kho mã hóa của hệ điều hành (Windows DPAPI), ngay khi xác minh và trước khi thoát. Lần mở lại tự tải các hồ sơ đã lưu, không tự gửi prompt. Cần giữ đúng thư mục, máy và tài khoản Windows. Nếu Muse thu hồi/hết hạn phiên, yêu cầu OTP mới hoặc phiên đã mất trước khi cập nhật thì phải đăng nhập lại tài khoản đó; tool không kéo dài hạn phiên của Muse.

Chế độ nhiều tài khoản dùng lại **một tab Muse đã tải của mỗi tài khoản** thay vì mở thêm trang và xác minh thêm một lần cho mỗi render. Các tài khoản dùng chung một kết nối điều khiển nhưng cookie/hồ sơ vẫn tách riêng. Mỗi ô hiện giai đoạn Kiểm tra phiên / Chờ Message / Muse đã nhận / Đang tải để phân biệt tool đang chuẩn bị với Muse đang xử lý. Không tự gửi lại prompt khi chưa rõ kết quả.

Thời gian tạo và số tác vụ phía máy chủ do Muse quyết định. Nhiều tài khoản không bảo đảm video render nhanh hơn: máy phải đủ RAM/CPU cho nhiều trang Muse và từng tài khoản phải có quyền tạo, hạn mức phù hợp. Bản sửa đã kiểm thử bằng dịch vụ giả lập; chưa đăng nhập hoặc render bằng tài khoản thật của bạn từ cloud này.

## Proxy tùy chọn

Trong **Tài khoản Muse**, bấm **Proxy luồng** ở tài khoản cần cấu hình, hoặc **Proxy Muse NN** ngay trong ô. Không dùng proxy thì để **Bật proxy riêng** tắt. Hỗ trợ `http://host:port`, `https://host:port`, `socks5://host:port`.

HTTP/HTTPS có thể nhập tên đăng nhập và mật khẩu ở các ô riêng; không đặt mật khẩu trong URL. SOCKS5 dùng không mật khẩu do giới hạn Chromium. Thông tin được lưu mã hóa trên máy, không đưa vào dự án JSON, log hay API/MCP. Đổi proxy khi đã dừng các lượt tạo; sau khi lưu bấm **Kiểm tra phiên**. Đổi proxy không xóa hồ sơ đăng nhập. Ở chế độ một tài khoản, mọi luồng dùng proxy Muse 01; ở chế độ nhiều tài khoản, mỗi tài khoản dùng proxy riêng.

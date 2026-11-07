# Mã nguồn mở và điều khiển bằng Codex/MCP trên cùng máy

Ứng dụng Muse AI Studio được phát hành theo **MIT** tại `LICENSE`. Mã nguồn đầy đủ có trên GitHub và trong `Muse-Video-Workstation.zip`. Có thể đọc, sửa và tự build theo README. Electron, Playwright, React và các thư viện khác giữ giấy phép riêng đi kèm gói.

Bản 1.8.0 có server **MCP Streamable HTTP** tại `http://127.0.0.1:8790/mcp`, cùng khóa Bearer với API. Trợ lý đọc các ô và gửi lệnh qua đúng chức năng Studio dùng, gồm sửa prompt, chọn số ô, tạo/dừng, đọc thư viện và lưu bộ kết quả vào thư mục. Không cần trợ lý bấm tọa độ chuột hoặc truy cập cookie/mật khẩu Muse.

## Thiết lập trên máy Windows chạy Studio

1. Giải nén gói đầy đủ, mở `Muse AI Studio.exe` và đăng nhập Muse.
2. Bấm **Thư mục lưu** để chọn nơi tải ảnh/video. Các lệnh lưu tiếp theo tự dùng thư mục này và đánh số tăng tiếp.
3. Bấm **Cổng API → Bật / Áp dụng cổng**, rồi **Sao chép khóa**.
4. Đặt khóa vào biến môi trường `MUSE_STUDIO_KEY` của ứng dụng Codex trên máy này. Không dán khóa vào cuộc trò chuyện hoặc GitHub.
5. Bấm **Sao chép cấu hình Codex MCP** trong Studio. Thêm đoạn đó vào tệp `%USERPROFILE%\.codex\config.toml` hiện có. Mẫu cũng có tại `CODEX-MCP.toml`.
6. Khởi động lại Codex để nhận biến môi trường và kết nối MCP. Studio cần giữ mở; xem danh sách công cụ MCP trong Codex để xác nhận có các công cụ `studio_*`.

Nếu cần đặt biến môi trường bằng Windows PowerShell, chạy đoạn sau trên **máy của bạn**; nhập khóa trong ô được che:

```powershell
$studioSecret = Read-Host 'Dán khóa API Studio' -AsSecureString
$studioValue = [System.Net.NetworkCredential]::new('', $studioSecret).Password
[Environment]::SetEnvironmentVariable('MUSE_STUDIO_KEY', $studioValue, 'User')
$env:MUSE_STUDIO_KEY = $studioValue
Remove-Variable studioValue, studioSecret
```

Mẫu cấu hình (đổi cổng nếu bạn đã chọn cổng khác):

```toml
[mcp_servers.muse_studio]
url = "http://127.0.0.1:8790/mcp"
bearer_token_env_var = "MUSE_STUDIO_KEY"
tool_timeout_sec = 600
```

Khóa không được ghi trực tiếp vào mẫu TOML. Sau **Đổi khóa API**, cập nhật lại biến môi trường và khởi động lại Codex. Nếu công cụ báo 401, kiểm tra khóa/biến môi trường; 503 nghĩa là Studio đang tải; 409 nghĩa là cần chờ trạng thái hiện tại hoặc hoàn tất đăng nhập.

## Các công cụ trợ lý có thể dùng

| Công cụ | Thao tác |
| --- | --- |
| `studio_status` | Đọc prompt, số ô, số luồng yêu cầu/thực tế, tài khoản đã xác minh, tiến độ và media |
| `studio_configure_layout` | Chọn 1–40 ô, số luồng, một/nhiều tài khoản và chế độ ảnh/video |
| `studio_set_scene` | Sửa prompt/bật/tắt một ô, gán ảnh đã lưu hoặc gỡ ảnh |
| `studio_create_batch` | Nhập bộ prompt hoặc TXT/SRT rồi tạo ảnh/video |
| `studio_run` | Bấm tạo/tạo lại các ô đã nhập, không thay prompt của các ô khác |
| `studio_stop` | Dừng một ô hoặc cả bộ |
| `studio_list_media` | Đọc các ID kết quả và batchId |
| `studio_save_results` | Lưu các kết quả đang chọn hoặc một bộ cụ thể vào thư mục trên máy |
| `studio_clear_library` | Xóa thư viện khi người dùng yêu cầu, có chuỗi xác nhận `DELETE_ALL_MEDIA` |

Lệnh tạo có thể tính phí theo Muse. Trợ lý nên đọc trạng thái trước, dùng `requestId` riêng cho một lần tạo, theo dõi `batchId` và chỉ tải khi có kết quả. Nếu timeout hoặc dịch vụ báo hạn mức, đọc lại tiến độ trước khi gửi lại. `studio_save_results` không trả byte video lớn vào hội thoại; nó lưu trên máy và trả thông tin thư mục/tệp. Lần đầu chưa chọn nơi lưu sẽ mở hộp thoại cần người dùng chọn.

Có thể yêu cầu Codex, ví dụ:

> Dùng Muse Studio MCP, mở 30 ô, nhập kịch bản tôi cung cấp, tạo video, theo dõi đến khi hoàn tất và lưu bộ về thư mục đã chọn. Báo đúng số luồng Muse đã xác minh; không tự gửi lại cảnh lỗi.

Hoặc:

> Đọc ô 17, sửa prompt theo yêu cầu mới của tôi rồi tạo lại riêng ô đó và lưu kết quả.

## Phạm vi truy cập

Bộ kết nối này dành cho **trợ lý/Codex chạy trên cùng máy Windows**, đúng lựa chọn của người dùng. ChatGPT trên web hoặc một chat cloud ở máy khác không tự truy cập được `127.0.0.1` này. Cần cấu hình kết nối MCP trong đúng ứng dụng trợ lý; mở mã nguồn không tự thêm công cụ vào phiên chat hiện tại.

Đăng nhập/OTP vẫn nhập trực tiếp trên trang Muse trong Studio. Tool không cấp quyền duyệt tệp tùy ý, chạy JavaScript/hệ thống hoặc đọc cookie. Số render thật cùng lúc và khả năng tạo ảnh/video do Muse quyết định; nếu không có hội thoại riêng thì tool giữ đủ ô và chạy hàng đợi theo số luồng đã xác minh.

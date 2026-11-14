# Muse AI Studio 1.12.2 — Khôi phục khi Studio vẫn dừng dù GPU đã tắt

Báo cáo từ máy người dùng trong 1.12.1 cho biết `STUDIO_RENDERER_EXITED` và `hardwareAcceleration: false`. Báo cáo cũ không có `reason` hoặc `exitCode`, vì vậy chưa xác định được nguyên nhân dừng. Đọc toàn bộ kho ảnh/video khi khởi động là một đường sử dụng nhiều bộ nhớ cần được kiểm tra; chưa có bằng chứng rằng đó là nguyên nhân trên máy này.

## Cách mở bản này

1. Đóng hoàn toàn Muse đang chạy.
2. Giải nén toàn bộ ZIP vào thư mục mới.
3. Mở **MO_STUDIO_KHOI_PHUC.bat**. Chế độ này tắt GPU và mở Studio mà chưa đọc kho ảnh/video cũ. Tài khoản và kịch bản vẫn dùng hồ sơ hiện có. Các tệp và kho kết quả cũ không bị xóa hoặc chuyển đi.
4. Nếu vẫn lỗi, bấm **Sao chép chẩn đoán Studio** và gửi báo cáo mới. Báo cáo có `lastExit.reason`, `exitCode`, `exitCodeHex`, bước khởi động, phiên bản Electron/Chromium/Windows và số liệu RAM hệ thống. Không thu thập đường dẫn, tên tài khoản hay nội dung kịch bản.

Trên màn hình lỗi cũng có nút **Khôi phục Studio** để bỏ qua việc đọc thư viện mà không khởi động lại ứng dụng. Nút này không thay đổi thiết lập GPU của tiến trình đang chạy. Bản thường mở bằng **Muse AI Studio.exe** như trước và đọc lại kho kết quả cũ.

## Thay đổi và giới hạn

- Giữ lý do dừng do Electron cung cấp, mã thoát dạng số/thập lục phân và bước gần nhất. Phân biệt rõ trường hợp Electron báo hết bộ nhớ; không suy đoán hết RAM chỉ từ mã lỗi chung.
- Chế độ khôi phục không đọc/giải mã thư viện cũ lúc mở. Có nhãn cố định trên giao diện để giải thích vì sao lịch sử cũ chưa hiện. Các kết quả mới vẫn được lưu vào cùng kho.
- Chế độ khôi phục làm mới bộ đệm JavaScript đã biên dịch của riêng Studio bằng `clearCodeCaches`. Không xóa cookie, localStorage, IndexedDB hoặc dữ liệu của các tài khoản Muse. Báo cáo cho biết thao tác làm mới cache có hoàn tất không.
- Vô hiệu hóa **Xóa toàn bộ** và từ chối lệnh xóa toàn bộ qua API trong chế độ khôi phục để tránh xóa lịch sử chưa được hiển thị.
- Tải lại/khôi phục vẫn bị chặn khi có tác vụ tạo nội dung đang chạy.
- Kiểm thử bằng kho cục bộ và Muse giả lập. Chế độ khôi phục được kiểm tra mở được khi thao tác đọc kho cũ bị chặn, và kho/kịch bản cũ vẫn đọc lại được trong chế độ thường. Cần thử trên máy người dùng để xác định kết quả và nguyên nhân thực tế.

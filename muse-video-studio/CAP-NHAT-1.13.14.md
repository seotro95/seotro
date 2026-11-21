# Muse AI Studio 1.13.14 — xử lý prompt tool còn lại trong ô Message

Bản Windows đầy đủ. Đóng bản cũ, giải nén ZIP mới và mở Muse AI Studio.exe. Giữ dữ liệu tại %LOCALAPPDATA%\Muse AI Studio.

## Lỗi MUSE_DRAFT_EXISTS khi bấm tạo lại

- Ghi nhận chính xác nội dung tool nhập trước mỗi thao tác, cả ký tự kích hoạt ô Message và toàn bộ prompt. Nếu ô Message hiện lại nội dung đó sau khi gửi hoặc huỷ trước khi gửi, tool nhận biết nội dung của chính mình thay vì coi đó là bản nháp mới của người dùng.
- Kiểm tra bản nháp ngay khi chuẩn bị tài khoản. Không báo sẵn sàng rồi mới phát hiện ô Message đang bị chặn.
- Chuẩn bị ô Message và nhập prompt dùng chung khoá của từng tài khoản, tránh một ô dọn nội dung trong khi ô khác đang soạn. Các yêu cầu đã gửi vẫn tạo song song theo lựa chọn.
- Khi bạn tự sửa hoặc xoá nội dung đang soạn, tool giữ thay đổi đó và dừng. Nội dung giống marker, ký tự '[' hoặc prompt từ một trang vừa tải lại không tự được coi là nội dung thuộc tool.
- Nếu đã thử Enter nhưng chưa xác nhận được Muse nhận yêu cầu, tool không tự Enter lần hai. Kiểm tra lịch sử hoặc dùng Nhận lại từ Muse.

## Prompt còn lại từ bản 1.13.13

Ở ô báo MUSE_DRAFT_EXISTS, bấm **Dọn bản nháp tool**. Tool chỉ xử lý khi toàn bộ dấu theo dõi và nội dung cảnh khớp đúng prompt của ô đó trên đúng tài khoản, hoặc nguyên vẹn prompt của lượt cũ đã được xác nhận trong lịch sử.

- Nếu Muse đã nhận lượt cũ, nút chính chuyển sang **Nhận lại từ Muse** để lấy tệp đã tạo.
- Nếu chỉ dọn được bản nháp chưa gửi, prompt và tên trong Studio được giữ; bạn có thể bấm Tạo lại cảnh khi muốn gửi lượt mới.
- Dọn bản nháp không tự nhấn Enter, không tạo ảnh/video và không xoá ảnh đính kèm hoặc nội dung chưa xác minh. Tài khoản khác vẫn có thể chạy.

Giữ giới hạn chờ 250 giây, các chế độ một hoặc nhiều tài khoản, số ô đã chọn, sửa nhận ảnh, nhập nhiều TXT/SRT, tên tệp, hàng chờ và nút xoá toàn bộ video của bản 1.13.13.

Các kiểm tra dùng Muse mô phỏng qua Chromium/Electron và EXE Windows. Có kiểm tra hai nhóm 6 video liên tiếp, bản nháp cũ được giữ lại ở textarea/rich editor, nội dung người dùng sửa, yêu cầu chưa xác nhận và xử lý đúng tài khoản Muse 02/cảnh 58. Chưa truy cập tài khoản Muse thật của người dùng.

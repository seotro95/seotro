# Muse AI Studio 1.13.3 — sửa fetch failed và lỗi chờ xác nhận

Bản Windows x64 đầy đủ. Không cần bản cũ, Node.js hoặc Chrome cài riêng. Đóng bản cũ, giải nén toàn bộ ZIP vào thư mục mới rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Hồ sơ, kịch bản và thư viện tiếp tục ở `%LOCALAPPDATA%\Muse AI Studio`.

## Kết nối tạo nội dung

Ảnh lỗi thực tế hiển thị `fetch failed`. Bản trước gửi lệnh tạo nội dung từ tiến trình desktop tới API nội bộ bằng global fetch rồi chỉ hiển thị lỗi chung. Bản này dùng một HTTP client riêng cho đúng máy chủ Studio trên `127.0.0.1`, không dùng proxy của Muse hoặc cấu hình global fetch. Thời hạn chờ nội bộ dài hơn thời hạn xử lý của máy chủ; không dùng giới hạn chờ header mặc định của fetch. Không tự phát lại một yêu cầu bị mất kết nối vì Muse có thể đã nhận.

Lỗi kết nối mới có mã riêng: `MUSE_LOCAL_CONNECTION_FAILED`, `MUSE_LOCAL_CONNECTION_LOST`, `MUSE_LOCAL_TIMEOUT`, `MUSE_LOCAL_RESPONSE_INVALID`. Lỗi do Muse trả về vẫn giữ nguyên mã để phân biệt.

## Tránh chờ sai trong cùng chat

- Đặt mã nhận diện đầu tin nhắn để phần hiển thị thu gọn vẫn giữ thông tin xác nhận.
- Sau khi Muse đã xác nhận, tiếp tục nhận đúng tệp theo mã riêng kể cả khi dòng người dùng cũ bị ẩn khỏi giao diện. Không lấy ảnh/video cũ hoặc đoán thứ tự kết quả.
- Nếu không xác nhận được thao tác gửi, kết thúc đúng thời hạn xác nhận, kể cả khi tác vụ khác còn hiển thị đang xử lý. Không giữ các ô sau chờ đến hết thời hạn tạo video.

Nếu Muse trả lời rõ rằng cần làm rõ prompt, tool hiện `MUSE_PROMPT_CLARIFICATION` thay vì tiếp tục chờ ảnh/video. Ví dụ các chữ thử tên tệp như `fadhah` hoặc `gsjsj` nên được thay bằng mô tả cảnh khi kiểm tra tạo nội dung.

## Sao chép lỗi

Mỗi ô lỗi có **Sao chép lỗi** và **Tải lỗi TXT**. Bản desktop ghi clipboard bằng cầu nối cục bộ; bản web tải TXT thay thế nếu trình duyệt chặn clipboard. Báo cáo có phiên bản, thời điểm, số ô, tài khoản theo số thứ tự, trạng thái và lỗi gốc; không chủ động thêm prompt, nhãn email hoặc proxy. Phần mã lỗi cũng có thể chọn chữ trực tiếp.

Giữ các chức năng 1.13.2: một tài khoản gửi nhiều tin nhắn cùng chat, tối đa 6 yêu cầu đang xử lý trong chế độ này, 10 ô giữ đủ và chờ chỗ trống; chuyển tuần tự khi không chạy song song được; tên TXT/SRT, bộ đếm tên thiếu, proxy IP và khôi phục Studio.

## Kiểm chứng

Kiểm thử cố tình làm global fetch báo `fetch failed` với nguyên nhân `UND_ERR_HEADERS_TIMEOUT` và đặt proxy kế thừa không dùng được: HTTP client cục bộ vẫn gửi được 10 yêu cầu chờ đồng thời. Kiểm tra ngắt kết nối, hủy riêng, thời hạn chờ, JSON lỗi và không gửi trùng. Kiểm thử Electron/EXE áp dụng cùng tình huống fetch bị hỏng, cùng các luồng tạo ảnh/video và lưu tên. Kiểm tra thêm tin nhắn thu gọn, ẩn dòng người dùng và clipboard/TXT.

Các kiểm thử dùng dịch vụ mô phỏng, không dùng tài khoản hoặc credit Muse thật. Ảnh `fetch failed` chưa cung cấp mã lỗi hệ thống bên trong; báo cáo mới giữ được thông tin để phân biệt nếu máy vẫn gặp lỗi kết nối.

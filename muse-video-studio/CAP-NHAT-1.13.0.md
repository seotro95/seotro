# Muse AI Studio 1.13.0 — tên tệp, nhiều ô mỗi tài khoản và IP proxy

Bản Windows x64 đầy đủ, phát triển từ 1.12.2. Giải nén toàn bộ ZIP vào thư mục mới rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần cài Node, Chrome hoặc bản cũ. Dữ liệu tiếp tục ở `%LOCALAPPDATA%\Muse AI Studio`; giữ nguyên nơi này. Các chế độ tải lại/khôi phục Studio và chẩn đoán lỗi khởi động của 1.12.2 vẫn có trong bản mới.

## Đặt tên theo mục lớn trong TXT/SRT

Tool tự nhận mục lớn `[1] TÊN NHÂN VẬT — MÃ PHIM`, `[2] ...`, hoặc `1. TÊN CẢNH` có nội dung bên dưới. Nếu mục lớn chứa các mục con `PROMPT CHAN DUNG` và `PROMPT TOAN THAN`, tool tách hai prompt và lấy tên mục lớn kèm loại ảnh. Các mục mô tả giọng nói hoặc ghi chú nhân vật không bị biến thành prompt tạo ảnh.

Ví dụ từ tệp hồ sơ: mục `[1] AIKO TANAKA — JDR001` tạo tên `AIKO TANAKA — JDR001 — CHAN DUNG.png` và `AIKO TANAKA — JDR001 — TOAN THAN.png`. Nếu tiêu đề có tên phim tiếng Nhật, phần đó được giữ trong tên. Tệp mẫu 10 nhân vật được nhận thành 20 prompt tạo ảnh, giữ nguyên toàn bộ nội dung hai prompt của từng người.

Có thể ghi tên trực tiếp trong TXT hoặc nội dung từng cue SRT:

```text
Tên video: Cảnh mở đầu.mp4
Prompt: Toàn cảnh ngôi đền lúc bình minh, máy quay tiến chậm.
```

Cũng nhận `Tên ảnh:`, `Tên tệp:`, `Name:`, `Filename:`, `Title:`. Tên là dữ liệu tải về, được tách khỏi phần prompt gửi Muse. Mỗi ô hiển thị **Tên tệp ảnh/video**, có thể sửa mà không cần tạo lại kết quả. Tên và prompt được lưu trong dự án; kết quả lưu trong thư viện cũng giữ tên gốc. Khi xem lại kết quả cũ trong lịch sử, tên đi cùng kết quả đó được khôi phục.

Nếu không có tên: tải thành `1.png`, `2.png` hoặc `3.mp4`... Bộ đếm dùng chung ảnh/video, tiếp tục sau khi tải nhiều lần hoặc mở lại tool. Tệp có tên không tiêu thụ số tự động. Tên trùng trong cùng bộ được thêm `(2)`, `(3)`; mỗi lần tải cả bộ tạo thư mục riêng để giữ các bộ cũ. Ký tự không hợp lệ trên Windows được đổi thành `_`; đuôi tệp theo định dạng thực tế. Ảnh được xuất PNG như các bản trước.

## 1–40 tài khoản, 1–10 ô mỗi tài khoản

- Chọn **Một tài khoản** hoặc **Nhiều tài khoản**.
- Chọn **Ô chạy / tài khoản** từ 1 đến 10. Mặc định yêu cầu 6.
- Chế độ nhiều tài khoản có **Số tài khoản** và checkbox chọn các hồ sơ cụ thể. Có nút nhanh **10 tài khoản × 6 ô**: bố trí 60 ô, mỗi tài khoản được gán sáu ô.
- Ví dụ: một tài khoản × sáu ô = sáu tác vụ video đồng thời; mười tài khoản × sáu ô = 60 tác vụ đồng thời; tối đa bố cục 40 × 10 = 400 ô.
- Có thể giữ nhiều prompt hơn số luồng; một ô xong sẽ nhường chỗ cho ô chờ cùng tài khoản. Ẩn/thu gọn bố cục giữ dữ liệu các ô cũ. Có thể thay tài khoản riêng trong từng ô; khi đó phân phối thực tế theo tài khoản của từng ô.
- Bộ xếp hàng và backend đều đã bỏ khóa cũ “mỗi tài khoản nhiều-account chỉ một luồng”. Mỗi tài khoản dùng các hội thoại riêng đã xác minh, với giới hạn riêng; một tài khoản chậm hoặc một ô bị hủy không khóa các tài khoản khác.

Có thể chọn số ô riêng cho từng tài khoản trong bảng chọn: ví dụ Muse 01 chạy 2 ô, Muse 02 chạy 6 ô, Muse 03 chạy 10 ô. Tổng ô bằng tổng lựa chọn từng tài khoản. Đổi ô mặc định cho cả nhóm hoặc bấm preset 10 × 6 sẽ áp dụng lại đồng đều; số ô riêng được lưu khi mở lại.

Bố cục là số ô yêu cầu chạy. Muse vẫn quyết định hạn mức, credit và số tác vụ dịch vụ chấp nhận. Nếu không xác minh được hội thoại độc lập, tool báo số ô thực tế đã sẵn sàng và giữ phần còn lại trong hàng chờ; không báo giả là đang chạy đủ sáu và không tự gửi lại prompt đã được Muse nhận.

## IP proxy của từng tài khoản

Trong **Quản lý tài khoản**, mỗi hồ sơ có ô **IP proxy** và nút **Kiểm tra IP**. Bật/lưu proxy rồi bấm kiểm tra. IP được đo bằng chính phiên mạng/proxy của tài khoản đó, có thời điểm kiểm tra và lỗi riêng. Có thể kiểm tra cả trước khi đăng nhập Muse. Các ô dùng chung tài khoản dùng chung proxy và IP của tài khoản đó.

IP hiển thị là IP ra Internet mà dịch vụ kiểm tra quan sát, có thể khác địa chỉ máy chủ proxy. Chưa đo hoặc đo lỗi sẽ hiện trạng thái tương ứng, không lấy IP mạng trực tiếp thế vào. Đổi/tắt proxy xóa kết quả IP cũ; mở lại tool cần kiểm tra mới. Thông tin đăng nhập proxy vẫn mã hóa trên máy, không xuất trong bảng trạng thái. Phép đo không gửi cookie phiên Muse đến dịch vụ IP.

## Kiểm tra trước khi giao

Có kiểm tra parser/tên tệp, giới hạn 40 tài khoản/10 ô, bộ xếp hàng 60 tác vụ, hủy độc lập, xuất thư mục và duy trì bộ đếm. Kiểm thử trình duyệt thật bằng dịch vụ mô phỏng xác nhận sáu yêu cầu video đồng thời trên một tài khoản, sáu hội thoại khác nhau và hủy một còn năm. Kiểm thử giao diện xác nhận 10 × 6 gửi đủ 60 yêu cầu. Kiểm thử Electron đo hai IP khác nhau qua hai proxy có mật khẩu và không gửi cookie.

Các kiểm thử dùng fixture, không dùng credit Muse và không chứng nhận hạn mức của tài khoản Muse thực tế. Gói Windows được build và kiểm tra bằng workflow Windows; xem trạng thái workflow đi kèm release. Việc thêm nhiều ô không giải quyết mọi nguyên nhân renderer crash trên từng máy Windows; chế độ khôi phục của 1.12.2 được giữ để chẩn đoán.

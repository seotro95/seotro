# Muse AI Studio 1.13.5 — nhiều tài khoản và giảm tải giao diện

Bản Windows x64 đầy đủ, gồm các sửa lỗi đọc phản hồi và tải media của 1.13.4. Không cần bản cũ, Node.js hoặc Chrome cài riêng. Đóng tool cũ, giải nén toàn bộ ZIP vào thư mục mới rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Dữ liệu tài khoản, kịch bản và thư viện giữ ở `%LOCALAPPDATA%\Muse AI Studio`.

## Cấu hình 60 ô hoặc hơn

Chọn **Nhiều tài khoản**, số tài khoản **10**, **Ô chạy mỗi tài khoản: 6** để có **60 ô**. Có thể chọn 12 × 6 = 72 hoặc nhiều tài khoản hơn, tối đa 40 tài khoản. Mỗi tài khoản có lựa chọn 1–10 ô; khi cùng chat chỉ được xác minh tối đa sáu yêu cầu, các ô thêm vẫn được giữ đủ và chờ chỗ trống. Tài khoản chưa đăng nhập/không đủ quyền không được coi là đã sẵn sàng.

Sáu ô trong mỗi tài khoản được gửi mà không đợi kết quả ô trước. Các tài khoản có hàng chờ riêng, một tài khoản chậm không chiếm lượt của tài khoản khác. Các tên TXT/SRT, prompt và tệp lưu được giữ như cũ. Chuyển tuần tự khi đã xác định không chạy song song được; yêu cầu đã nhận nhưng không rõ kết quả không tự gửi lại.

## Rút ngắn phần việc của tool

- Chuẩn bị tối đa ba tài khoản đồng thời thay cho chuẩn bị lần lượt. Các thao tác thay đổi phiên và gửi render vẫn được khóa trong lúc chuẩn bị; không chạy trùng bước chuẩn bị trên cùng tài khoản.
- Nếu trang đăng nhập đã xác minh không có New chat, dùng thẳng cùng chat. Không mở bốn trang thử vô ích cho mỗi tài khoản.
- Dùng lại khung đã xác định khi tìm ô Message, giảm truy vấn DOM/handle mỗi lần chuyển cảnh tuần tự và giữ đúng iframe.
- Ghi lựa chọn số luồng nối tiếp để việc chuẩn bị đồng thời không giẫm lên cùng một tệp cấu hình tạm.
- Không nạp metadata/decoder của hàng chục video chỉ để hiển thị danh sách; video tải để phát khi người dùng bấm Play. Ảnh xem trước nạp khi đến vùng nhìn thấy; Chromium bỏ qua vẽ/bố trí các thẻ ngoài màn hình mà vẫn giữ đủ prompt và ô trong DOM.
- Dùng sáu lượt tải/giải mã media chung cho toàn bộ tài khoản, tránh hàng chục canvas/file lớn xử lý đồng thời. Ngân sách này chỉ áp dụng sau khi Muse trả kết quả; không hạ 60/72 yêu cầu tạo thành sáu yêu cầu. Tác vụ hủy trong hàng chờ tải không bắt đầu tải.

Tool có thể giảm thời gian chuẩn bị, gửi và lấy kết quả. Thời gian render, số tác vụ Muse thực sự nhận, hạn mức và tốc độ mạng vẫn do dịch vụ/tài khoản quyết định; không cam kết mọi tài khoản tạo xong trong một phút.

## Sửa lỗi chờ và tải media

Giữ toàn bộ thay đổi ở [CAP-NHAT-1.13.4.md](CAP-NHAT-1.13.4.md): phân biệt gửi tin nhắn với khởi chạy video; đọc câu trả lời Muse khi thiếu mã tệp; hiển thị phản hồi và tải trạng thái TXT ngay khi còn chờ; yêu cầu công cụ có sẵn bắt đầu tạo, báo thông số thực tế; ưu tiên ảnh/player thật, đọc source con, giữ URL thật và tải qua đúng Electron session khi fetch trong trang bị chặn. Liên kết sandbox không có media thật thay thế được báo lỗi cụ thể, không để ô chờ hết mười phút. Phần lỗi giữ chi tiết HTTP/định dạng thay vì che hết trong MUSE_MEDIA_UNREADABLE.

## Kiểm chứng và giới hạn

Bài kiểm thử qua Chromium dùng 12 phiên đăng nhập độc lập, mỗi phiên một trang và sáu tin nhắn; giữ toàn bộ kết quả để chứng minh đủ 72 yêu cầu đã đến trước khi trả bất kỳ video nào. Trả kết quả đảo thứ tự và so sánh bytes riêng cho từng cảnh. Kiểm tra thêm giao diện 10 × 6 = 60, giới hạn từng tài khoản, hủy riêng, tên sau khi tải/mở lại, quyền thay đổi phiên lúc chuẩn bị, hàng chờ tải sáu lượt và đóng gói EXE Windows.

Các bài kiểm tra dùng dịch vụ mô phỏng và không dùng credit Muse thật. Báo cáo 1.13.3 chưa chứa nguyên văn câu trả lời Muse trên máy người dùng; bản này hiển thị và lưu được phản hồi để phân biệt việc Muse chưa tạo nội dung với lỗi lấy kết quả.

# Muse AI Studio 1.13.4 — đọc phản hồi Muse và sửa tải ảnh/video

Bản Windows x64 đầy đủ. Đóng bản cũ, giải nén toàn bộ ZIP vào thư mục mới, mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần bản cũ, Node.js hoặc Chrome cài riêng. Giữ dữ liệu ở `%LOCALAPPDATA%\Muse AI Studio`.

## Hai báo cáo thực tế

- Video: `TIMEOUT` sau 10 phút; người dùng cho biết cuộc trò chuyện có prompt và câu trả lời nhưng chưa có video.
- Ảnh: `MUSE_MEDIA_UNREADABLE` nhưng bản trước che mất chi tiết tải/giải mã.

Tin nhắn đã xuất hiện không chứng minh một tác vụ video đã khởi chạy. Bản này dùng trạng thái **Đã gửi tin nhắn · chưa xác minh tạo nội dung**, hiển thị phản hồi gần nhất của Muse và cho tải trạng thái TXT ngay khi còn chờ.

## Đọc câu trả lời, không bỏ qua văn bản thiếu mã tệp

Bản trước chỉ xử lý một số phản hồi cùng chat khi Muse lặp lại mã nhận diện. Nếu Muse hỏi xác nhận, không hỗ trợ mô hình hoặc yêu cầu làm rõ mà không lặp mã, các ô tiếp tục chờ. Bản này đọc phản hồi mới sau lúc gửi, loại phần lịch sử cũ và phân biệt câu trả lời của cảnh với ngữ cảnh chung. Lỗi có mã và trích đoạn đã che URL/email; không tự gửi lại yêu cầu đã được nhận.

Không dùng một khoảng yên lặng ngắn để kết luận tác vụ nền thất bại: câu trả lời đang tạo nội dung vẫn được chờ. Báo cáo gồm số phản hồi, số media mới nhìn thấy, có khớp media hay chưa và tình trạng streaming. `TIMEOUT` được phân biệt với thao tác Dừng của người dùng.

Prompt gửi Muse yêu cầu thực hiện tạo ngay bằng công cụ có sẵn. Tên mô hình và thông số là mục tiêu; nếu công cụ không nhận đúng tên/tham số, dùng thông số được hỗ trợ và báo thông số thật thay vì chỉ trả lời kế hoạch. Kích thước file thực tế tiếp tục được kiểm tra và ghi Chưa đạt yêu cầu khi thấp hơn lựa chọn. Tool không cam kết Muse hỗ trợ mọi mô hình trong danh sách.

## Chọn đúng nguồn media

- Ưu tiên ảnh/trình phát thật, không ưu tiên một liên kết chỉ vì nhãn có mã tên tệp.
- Đọc cả `<source>` của video chưa được bấm Play.
- Loại liên kết giao thức không tải được như `sandbox:` khỏi đường tải trực tiếp. Giữ nguyên URL thật do Muse cung cấp, không yêu cầu Muse đổi tên vật lý hoặc tự tạo đường dẫn. Tên TXT/SRT vẫn được áp dụng khi lưu trên máy.
- Nếu fetch trong trang bị chặn mạng/CORS hoặc trả 401/403, bản desktop thử tải qua đúng Electron session của tài khoản đó, dùng cookie/proxy hiện có. Không mở quyền Node hoặc cầu nối tải tệp cho trang Muse; giữ webSecurity. Chỉ tải lại media, không gọi lại tạo ảnh/video.
- Giữ kiểm tra định dạng, giải mã, giới hạn dung lượng và hủy tác vụ. Mã lỗi mới giữ chi tiết như HTTP, không phải media, URL không hỗ trợ hoặc lỗi giải mã thay vì một thông báo chung.

Giữ các chức năng tên TXT/SRT, bộ đếm tải, tài khoản, proxy IP, một chat tối đa sáu tác vụ đang chờ, 10 ô đủ nội dung và chuyển tuần tự khi đã xác định không chạy song song được.

## Giới hạn kiểm chứng

Kiểm thử tái hiện phản hồi từ chối/xin xác nhận không mang mã, liên kết sandbox che ảnh thật, video có source con và tải ảnh khi fetch của trang bị làm lỗi. Kiểm tra bằng Chromium/Electron và tệp EXE đóng gói trên Windows với dịch vụ mô phỏng; không dùng tài khoản hoặc credit Muse thật. Chưa có nguyên văn câu trả lời Muse trên máy người dùng để kết luận lý do cụ thể của video chưa khởi chạy; báo cáo trạng thái mới lưu được dữ kiện này.

# Muse AI Studio 1.13.7 — nhận video có chú thích tách riêng

Bản Windows x64 đầy đủ. Đóng hẳn tool cũ, giải nén toàn bộ ZIP vào thư mục mới rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần bản cũ, Node.js hoặc Chrome cài riêng. Dữ liệu trong `%LOCALAPPDATA%\Muse AI Studio` được giữ.

## Sửa đúng cấu trúc Muse đang trả về

Báo cáo 1.13.6 đã có năm nguồn video, 11 phản hồi và các nhãn CLIP, nhưng tool báo `MUSE_BATCH_UNMATCHED`. Người dùng xác nhận: video ở khung riêng, dòng CLIP nằm trong lời trả lời bên dưới. Bản cũ chỉ tìm nhãn bên trong khung chứa media nên bỏ sót cấu trúc này; thông báo “thiếu nhãn” và tự hạ về một luồng chưa đúng nguyên nhân.

Bản này nhận thêm cặp **khung media và lời hoàn thành CLIP liền bên dưới** trong cùng lượt. Video hoàn thành trước hay sau vẫn về đúng ô nhờ nhãn trên chú thích, không ghép theo số thứ tự xuất hiện. Chỉ ghép cặp có một nguồn media và một chủ sở hữu rõ ràng; không ghép hai danh sách video và tiêu đề rời rạc theo thứ tự, không đi xuyên tin nhắn người dùng, không nhận lại media lịch sử hoặc media có chú thích thuộc lượt khác.

Chờ chú thích đến muộn thay vì báo lỗi sau ba giây chỉ vì đã thấy video. Lỗi đối chiếu tệp không tự hạ số luồng như lỗi hạn mức chạy đồng thời. Giữ cách gửi tối đa sáu prompt trong một tin nhắn, các tài khoản chạy độc lập và giới hạn chờ 190/195/200 giây ở máy chủ/cầu nối/giao diện.

## Lấy lại năm video đã tạo ở bản 1.13.6

1. Giữ nguyên đầy đủ prompt, số ô và tên tệp đã dùng.
2. Chọn đúng tài khoản, ví dụ **Muse 10**. Trong **Đăng nhập Muse trong tool**, mở cuộc trò chuyện có năm video cũ và các nhãn CLIP. Nếu tin nhắn prompt đang thu gọn, mở rộng nó.
3. Trở về Studio, bấm **Nhận lại từ Muse** ở thanh thao tác để lấy các ô còn thiếu, hoặc **Nhận lại từ Muse · không tạo mới** tại ô lỗi.
4. Sau khi có kết quả, tải riêng hoặc lưu cả bộ như bình thường. Tên TXT/SRT được giữ; ô không có tên dùng bộ đánh số sẵn có khi tải.

Đây là API chỉ đọc kết quả đã có: tìm tin nhắn gốc có đúng số ô và toàn bộ prompt, đọc nhãn gốc và tải đúng tệp. Không gọi tạo nội dung, không nhấn Enter, không mở New chat, không ghi đè bản nháp hoặc sửa cài đặt số luồng. Nếu lịch sử không hiện, prompt đã thay đổi, liên kết hết hạn hoặc không xác định được tệp, báo lý do; không tự tạo lại để bù.

## Thông tin thực tế của tệp

Phản hồi được gửi cho biết Muse trả 720p dù yêu cầu 1080p và không xác nhận được model. Tool hiển thị kích thước thực tế đọc được từ tệp; 720p không được ghi thành 1080p. Kết quả thấp hơn mức yêu cầu vẫn tải được và có dòng **Chưa đạt yêu cầu**.

## Kiểm chứng và giới hạn

Bài kiểm tra tái hiện năm khung video và năm lời CLIP tách riêng thất bại với cách đọc cũ. Bản mới đối chiếu đúng năm video hoàn thành ngược thứ tự; chú thích chậm hơn ba giây vẫn được nhận. Kiểm tra nhận lại so sánh đúng từng byte của năm tệp gốc, giữ bản nháp và chứng minh không tăng số tin nhắn hay lệnh tạo. Kiểm tra giao diện giữ tên tải về, không chuẩn bị chat mới khi nhận lại và không gọi API tạo nội dung.

Bộ Windows gồm các kiểm tra cũ về TXT/SRT, nhiều tài khoản, proxy/IP, hủy, dự phòng tuần tự, media, 72 tác vụ và EXE đóng gói; bổ sung kiểm tra chú thích tách riêng và API nhận lại trên EXE. Các kiểm tra tự động dùng dịch vụ mô phỏng, không dùng tài khoản hoặc credit Muse thật. Chưa trực tiếp tải năm tệp từ máy người dùng; không cam kết tốc độ xử lý phía Muse. Giới hạn 200 giây vẫn là giới hạn chờ của tool.

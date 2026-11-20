# Muse AI Studio 1.13.6 — yêu cầu gộp và giới hạn chờ 200 giây

Bản Windows x64 đầy đủ. Đóng hẳn bản cũ, giải nén toàn bộ ZIP vào thư mục mới rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần bản cũ, Node.js hoặc Chrome cài riêng. Dữ liệu ở `%LOCALAPPDATA%\Muse AI Studio` được giữ.

## Những gì báo cáo thực tế cho thấy

Người dùng chạy một ô thì tạo được. Khi chạy sáu ô trong cùng chat, Muse chưa có video hoàn thành nhưng tool hiển thị số ảnh/video trong cuộc trò chuyện và chờ hơn 200 giây. Vì vậy không thể coi số media nhìn thấy trong toàn bộ lịch sử là số kết quả mới, hoặc coi tin nhắn đã gửi là tác vụ render đã được nhận.

## Một yêu cầu Muse chứa tối đa sáu prompt

Bản trước gửi các tin nhắn riêng liên tiếp ngay khi thấy dòng người dùng. Bản này thu các ô cùng lượt của một tài khoản thành **một tin nhắn**, yêu cầu tạo các tệp độc lập, mỗi tệp giữ thời lượng của prompt; không ghép thành một phim dài. Các tài khoản vẫn chạy độc lập: 10 × 6 = 60 ô; 12 × 6 = 72 ô.

Các chỉ dẫn chung giống hệt nhau được gửi một lần và áp dụng cho từng tác vụ; toàn bộ nội dung cảnh được giữ. Mỗi tác vụ có nhãn CLIP ngắn riêng cho lượt đó. Tool đối chiếu liên kết, thẻ media và đoạn/tiêu đề chứa nhãn; không còn chỉ phụ thuộc tên tệp UUID dài. Giữ URL thật do Muse trả về; tên TXT/SRT vẫn áp dụng khi lưu trên máy.

Chưa gửi lượt chat kế tiếp chỉ vì dòng người dùng xuất hiện: đợi có kết quả và phần trả lời kết thúc, để các tin nhắn không chen nhau trước khi công việc bắt đầu. Ảnh tham chiếu chung được gộp cùng nhau; ảnh tham chiếu khác nhau được giữ thành lượt riêng để không lẫn nhân vật. Nếu độ dài vượt giới hạn thật của ô nhập Muse, chưa gửi và tự chuyển sang từng ô, giữ đủ prompt.

Nếu Muse báo rõ lỗi nhận đồng thời ở đúng tác vụ, các lượt chưa gửi chạy tuần tự. Không đoán thứ tự media thiếu nhãn, không tự tạo lại yêu cầu đã nhận nhưng chưa rõ kết quả. Trường hợp không ghép được sẽ hiện lý do thay vì chờ vô hạn.

## Chỉ đếm nguồn media mới

Chụp mốc URL trước mỗi lượt, bỏ media lịch sử ngay cả khi ứng dụng vẽ lại các DOM node. Bỏ kết quả có nhãn của lượt khác; gộp URL trùng giữa liên kết và player. Nội dung trả lời cũ cũng được loại khỏi phần phản hồi mới. Ảnh thumbnail của video không được coi là một lượt tạo ảnh.

Số hiển thị là **nguồn media mới**, không phải xác nhận đã tạo thành công. Chỉ ghi nhận kết quả sau khi tải và kiểm tra tệp. Liên kết chờ tệp/404 được thử lại có giãn cách trong cùng giới hạn thời gian; chỉ tải lại tệp, không gọi lại tạo nội dung.

## Giới hạn cứng của người dùng: 200 giây

- Máy chủ kết thúc chờ sau **190 giây**.
- Cầu nối HTTP trong desktop có giới hạn **195 giây**.
- Giao diện có watchdog **200 giây**, kể cả khi một transport không trả về sau khi hủy. Giới hạn của ô đang chạy bao gồm chuẩn bị ảnh, API, giải mã và chờ lưu; bước chuẩn bị nhóm tài khoản cũng có giới hạn 200 giây.
- Quá hạn hiện lỗi, giữ prompt và tên tệp. Không ghi là người dùng bấm Dừng và không tự gửi lại một yêu cầu chưa rõ kết quả. Nếu đã có media hợp lệ nhưng lưu thư viện bị treo, giữ kết quả để tải và đánh dấu chưa lưu trên ổ đĩa.

Đây là giới hạn chờ của tool, không phải cam kết Muse sẽ hoàn tất video trong 200 giây hoặc hoàn lại credit. Tác vụ đã gửi có thể còn xuất hiện trong lịch sử Muse.

## Kiểm chứng

Kiểm tra bằng Chromium/Electron và EXE Windows: sáu prompt tạo một tin nhắn; bỏ media cũ bị vẽ lại và media muộn của lượt khác; ghép sáu video đảo thứ tự chỉ bằng nhãn CLIP, không có UUID trong tên tệp; 72 tác vụ của 12 tài khoản qua 12 tin nhắn; hủy riêng và Dừng tất cả; dự phòng tuần tự; giữ đủ tên TXT/SRT. Bài kiểm tra đồng hồ giao diện đẩy qua 200 giây với kết nối cố tình không trả lời, xác nhận hết loading, giữ prompt và không gửi lại.

Các bài kiểm tra dùng dịch vụ mô phỏng, không dùng tài khoản/credit Muse thật của người dùng. Chưa có nguyên văn phản hồi Muse trong trường hợp sáu ô không tạo video; gộp một yêu cầu là thay đổi cách gửi để tránh burst tin nhắn, không phải khẳng định đã kiểm tra năng lực của tài khoản thật.

# Muse AI Studio 1.13.13 — nhận ảnh và xoá toàn bộ video trong tool

Bản Windows đầy đủ, không cần thư mục bản cũ. Đóng tool cũ, giải nén ZIP mới và mở Muse AI Studio.exe. Dữ liệu vẫn ở %LOCALAPPDATA%\Muse AI Studio.

## Xoá tất cả video đã tạo

- Trong thanh Đồng bộ thao tác, bấm **Xoá tất cả video đã tạo** để xem số kết quả và xác nhận xoá toàn bộ video trong tool. Áp dụng cả khi Đồng bộ thao tác đang tắt hoặc không chọn ô nào.
- Xoá mọi phiên bản video trong thư viện, gồm các lượt cũ, ô đang ẩn và kết quả của các nhóm TXT/SRT trước. Giữ prompt, tên tệp, ảnh, ảnh tham chiếu, tài khoản, tệp đã tải ra máy và lịch sử Muse.
- Các mục hàng chờ đã hoàn thành không tự chạy lại sau khi video bị xoá. Mục không còn tệp được hiển thị rõ; ảnh còn lưu trong nhóm vẫn tải được.
- Nút xoá chờ các tác vụ tạo, nhận lại, nhập hàng chờ và tải tệp hoàn tất. Nếu giao dịch lưu trữ bị lỗi, các video và giao diện được giữ.

## Các trường hợp nhận ảnh được sửa

- Nhận liên kết View image/Open image, tên tệp ảnh trong chữ của liên kết và liên kết ảnh không có đuôi tệp trong URL khi đối chiếu được với một nhãn cảnh duy nhất.
- Nhận nút Download image trong khung ảnh riêng, khi nhãn CLIP nằm ở lời trả lời trước hoặc sau khung đó. Chỉ chấp nhận kết quả ghép duy nhất; không chia ảnh theo thứ tự xuất hiện.
- Nhận liên kết ảnh HTTP cùng miền qua thao tác tải của trình duyệt khi tải trực tiếp bị chặn, kể cả liên kết không có thuộc tính download. Giữ nguyên URL của Muse và giữ trang hội thoại.
- Không nhận liên kết tham khảo thông thường thành ảnh, không kích hoạt liên kết thực thi mã và không gửi lại yêu cầu tạo khi đang nhận tệp đã hoàn thành.

Nếu thao tác tải ảnh hết hạn trước khi nhận được tệp, tool ngừng các lần tải qua nút trên chính trang đó để tệp đến muộn không bị nhận sang ô khác. Bấm **Tải lại Muse** ở đúng tài khoản, mở đúng cuộc trò chuyện rồi **Nhận lại từ Muse**. Thao tác này không tạo thêm ảnh; tài khoản khác và đường tải tệp trực tiếp vẫn hoạt động.

Mỗi ảnh vẫn phải được giải mã và đo kích thước thật trước khi lưu. Lời báo ready và thông số trong câu trả lời không thay thế được tệp ảnh.

Giữ đường nhận video của bản 1.13.12, giới hạn chờ 250 giây, mặc định một tài khoản một luồng, các lựa chọn nhiều tài khoản/nhiều ô, tên tệp, nhập nhiều TXT/SRT và hàng chờ đã lưu.

## Kiểm tra

Kiểm tra nhận ảnh qua Chromium và Electron với các khung ảnh/nút tải tách khỏi lời chú thích, các liên kết không có đuôi ảnh và thao tác nhận lại từ lịch sử không tạo mới. Kiểm tra ba tài khoản có phiên riêng, mỗi tài khoản hai ảnh, và chạy lại các ca video đang có.

Các kiểm tra dùng dịch vụ mô phỏng; chưa truy cập tài khoản Muse thật của người dùng. Người dùng xác nhận phần video của bản 1.13.12 trả kết quả tốt; ảnh chụp mới có một số ảnh hoàn thành ở Muse 04 và Muse 09, các ô khác lỗi nhận tệp hoặc hết thời gian. Chưa có JSON lỗi mới hoặc địa chỉ liên kết ảnh thực tế để xác nhận toàn bộ nguyên nhân.

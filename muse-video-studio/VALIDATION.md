# Xác minh bản 1.3.0

## Kết quả trên Linux

- Cài lại bằng `npm ci --cache /workspace/.cache/seotro-npm --no-audit --no-fund` từ lockfile thành công.
- `npm run build`: TypeScript và Vite thành công. Cảnh báo `use client` của bộ icon trong app client-only không ngăn build.
- `npm test`: 7 bài parser/chuyển dự án cũ/kích thước/state, 7 bài máy chủ API trong một nhóm, 3 bài lệnh mở trình duyệt và 2 bài phân tích số dư đã qua, không bỏ qua bài nào.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge`: 9 kịch bản trong một nhóm đã qua. Dùng Chromium thật với trang Muse giả lập trên loopback và hồ sơ tạm.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`: **17/17** bài giao diện đã qua. Desktop 5 cột, mobile không tràn ngang.
- `node --check server.mjs`, `node --check muse-browser.mjs`, `node --check muse-balance.mjs`, `bash -n start.sh` và kiểm tra whitespace Git đã qua.

## Hành vi đã chứng minh bằng fixture

- Đăng nhập một tài khoản rồi bấm TẠO 10 VIDEO một lần: cả 10 yêu cầu dùng accountId=1. TẠO 10 ẢNH cũng gửi đủ 10 yêu cầu đến cùng tài khoản. Không còn ô email, danh sách tài khoản hoặc nút gán riêng.
- Mở dự án cũ có gán tài khoản 1–10 vẫn giữ đủ 10 prompt, bỏ các gán cũ và chỉ gửi accountId=1. Máy chủ và cầu nối từ chối tài khoản số 2 trở đi; chỉ tạo một hồ sơ trình duyệt và mở lại phiên đã lưu.
- Hàng đợi chạy tuần tự, bỏ cảnh tắt, giữ lỗi từng cảnh, dừng/tiếp tục không tạo lại cảnh hoàn tất và xóa trạng thái chờ sau khi dừng. Phiên chưa xác minh hoặc hết hạn không được gửi yêu cầu mới.
- Bảng số dư đọc nhãn token/credit và giá trị 0 tổng hợp đúng; không coi hạn mức ngữ cảnh, tỷ lệ, số không nhãn hoặc nội dung chat là số dư. Không đọc được thì trả null và hiển thị Chưa đọc được.
- Nhập hai cảnh SRT tạo đúng hai ảnh riêng, tắt khóa nhân vật không gửi ảnh chân dung, chỉnh prompt xóa kết quả cũ và gửi nội dung mới.
- Yêu cầu 4K nhưng tệp fixture là 640×360 được hiển thị là 640×360 và Chưa đạt yêu cầu 4K, kể cả metadata API giả nói 3840×2160. Kích thước ảnh lấy từ bytes giải mã được.
- Bộ ảnh chuyển sang video với sourceMode=image và đúng ảnh theo cảnh. Đổi chất lượng video hoặc chuyển tab giữ ảnh. Chỉ các cảnh có ảnh đầu vào được gửi trong chế độ ảnh→video.
- Ảnh tổng hợp hơn 8 MB được nén ở bản tham chiếu gửi video; bản ảnh gốc vẫn còn. Không giả lập đầu ra 4K bằng cách đổi nhãn hoặc phóng ảnh.
- Cầu nối chỉ lấy media sau tin nhắn mới có marker; không lấy video cũ, giữ bản nháp chưa gửi, kiểm tra lại đăng nhập trước gửi, giữ lỗi quota và bấm Stop khi dừng.
- Các bài kiểm tra API xác nhận các mức yêu cầu video/ảnh, giữ nguồn ảnh khi tắt khóa nhân vật trong ảnh→video và từ chối thiếu ảnh đầu vào trước khi gọi adapter.

## Giới hạn còn lại

- **Chưa đăng nhập/tạo ảnh/video hoặc đọc số dư trên Muse.ai thật.** Môi trường không có phiên người dùng và các lần truy cập trực tiếp Muse nhận CONNECT 403. Fixture không chứng minh dịch vụ thật hoặc gói tài khoản hỗ trợ tính năng nào.
- Cầu nối trình duyệt và các selector không phải API chính thức. Muse đổi giao diện có thể cần cập nhật. Bảng số dư chỉ hiện khi có vùng số dư rõ nhãn mà bộ đọc nhận diện được; không cam kết Muse công khai số token/credit cho mọi tài khoản.
- Model, khung hình, thời lượng và 2K/4K là yêu cầu trong prompt, chưa xác minh Muse thực hiện đúng. Chất lượng khuôn mặt, sự đồng nhất, độ nét thật và tên model không được suy ra từ số pixel.
- Kiểm thử headless Chromium cục bộ không chứng minh đăng nhập Chrome/Edge trên Windows thật. Launcher Windows chưa được chạy trên máy Windows thật.
- Không đọc/xuất cookie hay token thật; fixture dùng cookie tổng hợp. Không có dữ liệu phiên người dùng trong Git/ZIP.

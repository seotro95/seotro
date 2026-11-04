# Xác minh bản 1.4.1

## Kết quả trên Linux

- `npm ci --cache /workspace/.cache/seotro-npm --no-audit --no-fund` từ lockfile thành công. Runtime Electron 45.2.2 tải/cài bằng bộ cài chính thức với checksum bật.
- `npm run build`: TypeScript và Vite thành công. Cảnh báo `use client` của bộ icon không ngăn build.
- Lệnh `npm start` qua launcher phát hành đã mở ứng dụng trên Linux/Xorg với hồ sơ fixture mới, trả HTML/API đúng trạng thái và thoát sạch khi đóng cửa sổ. Không mở Chrome ngoài.
- `npm test`: 7 bài parser/chuyển dự án cũ/kích thước/state, 7 bài máy chủ API trong một nhóm, 3 bài lệnh mở trình duyệt dự phòng và 2 bài phân tích số dư đã qua, không bỏ qua bài nào.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge`: 13 kịch bản trong một nhóm đã qua, dùng Chromium thật với Muse giả lập trên loopback và hồ sơ tạm.
- `DISPLAY=:97 MUSE_ELECTRON_TEST_NO_SANDBOX=1 npm run test:desktop`: 5 kịch bản trong một nhóm đã qua, dùng Electron thật trên màn hình Xorg dummy. Cờ tắt sandbox chỉ áp dụng cho fixture trong cloud; launcher phát hành không dùng cờ này.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`: **17/17** bài giao diện đã qua. Desktop 5 cột, mobile không tràn ngang.
- Kiểm tra cú pháp Node cho server/cầu nối/desktop/launcher, `bash -n start.sh` và whitespace Git đã qua.

## Lỗi thực tế được tái hiện và sửa

- Log người dùng: `locator.waitFor: Timeout 15000ms exceeded`, locator đầu tiên trỏ vào textarea ẩn có `data-hatch-composer-prehydration-input="true"`.
- Thêm fixture đặt textarea đó trước editor rich text đang hiển thị. Chạy với mã cũ tái hiện đúng timeout 15 giây; chỉ ca hồi quy này thất bại trong khi các ca cũ vẫn qua.
- Sau sửa, chọn editor hiển thị và loại bỏ textarea prehydration, ca hồi quy qua và đúng một yêu cầu được gửi bằng editor thật. Ô prehydration giữ rỗng.
- Kiểm tra trang hydrate chậm: placeholder còn hiển thị nhưng không nhận prompt; timeout được đổi thành `MUSE_COMPOSER_NOT_READY`, không gửi yêu cầu. Khi editor thật sẵn sàng, gửi và nhận ảnh bình thường.
- Kiểm thử Electron còn phát hiện view ẩn có viewport 0×0, khiến editor rich text rộng 0 px. Đã đặt viewport bố cục cho từng worker trước khi tải Muse; không thay đổi mức yêu cầu ảnh/video.
- Cả nhóm Electron desktop chạy với textarea ẩn + editor rich text, gồm 10 ảnh đồng thời, 10 video từ ảnh, Stop và khôi phục phiên. Kiểm tra từng yêu cầu có viewport khác 0 và textarea prehydration vẫn rỗng.

## 10 luồng và đăng nhập nhúng đã chứng minh

- Một cửa sổ Electron chứa Studio và trang đăng nhập Muse giả lập. Không mở Chrome/Edge ngoài. Remote view không có `require`, `studioDesktop` hoặc `museTransport`. IPC từ Studio từ chối endpoint không được phép.
- Đăng nhập một lần trong view Muse, Về Studio và Kiểm tra phiên: đúng một tài khoản xác minh, embeddedLogin=true và maxConcurrency=10.
- Bấm TẠO 10 ẢNH: đủ 10 yêu cầu được gửi và 10 cảnh cùng trạng thái Đang tạo trước khi fixture trả kết quả đầu tiên. Tất cả xác thực bằng cùng phiên. Fixture trả 10 ảnh khác nhau; từng ảnh được so sánh với đúng yêu cầu của cảnh đó.
- Chuyển bộ ảnh sang video: đủ 10 cuộc trò chuyện đang xử lý đồng thời, mỗi cuộc nhận đúng một ảnh tham chiếu và dùng chung phiên. Kết quả hoàn tất được đặt vào 10 ô; view worker được đóng, giữ lại Studio và đăng nhập.
- Dừng cả bộ gửi hủy qua IPC tới cả 10 yêu cầu, fixture nhận đủ 10 lần Stop và các view worker được đóng. Số yêu cầu máy chủ trở về 0.
- Đóng/mở lại ứng dụng với cùng thư mục dữ liệu khôi phục phiên đã lưu và xác minh được mà không bấm đăng nhập lần nữa.
- Kiểm thử API giữ đồng thời 10 HTTP request đến adapter, từ chối request thứ 11. Một request xong chỉ giải phóng một chỗ, không làm mất trạng thái bận của 9 request còn lại. Thay đổi phiên khi còn tác vụ bị từ chối.
- Frontend cũng được kiểm tra với barrier: 10 yêu cầu ảnh trước khi trả kết quả, 9 cảnh đang bật xử lý song song và lỗi quota vẫn ở đúng cảnh. Dừng/tiếp tục giữ cảnh đã hoàn tất. Dự án cũ gán tài khoản 1–10 chỉ còn gửi accountId=1, giữ đủ prompt; ID 2+ bị từ chối.

Fixture giữ kết quả bằng hàng rào đồng bộ, không phụ thuộc tốc độ trả lời mẫu. Đây là kiểm tra đồng thời thực sự của các tác vụ trong tool, không chỉ đếm tổng 10 kết quả sau khi chạy tuần tự. Fixture không mô phỏng thời gian, hạn mức hay quyền tạo nội dung của Muse thật.

## Các chức năng khác được giữ

- Bảng số dư đọc nhãn token/credit, gồm giá trị 0 tổng hợp; không coi hạn mức ngữ cảnh, tỷ lệ, số không nhãn hoặc nội dung chat là số dư. Không đọc được thì trả null.
- SRT nạp đúng số cảnh, không cắt im lặng khi quá 10. Tắt khóa nhân vật không gửi chân dung; chỉnh prompt xóa kết quả liên quan và gửi nội dung mới.
- Yêu cầu 4K nhưng fixture 640×360 thì hiện kích thước thật và Chưa đạt yêu cầu 4K, kể cả metadata giả nói 3840×2160. Kích thước ảnh được đọc từ bytes giải mã.
- Ảnh→video giữ đúng nguồn ảnh kể cả khi tắt khóa nhân vật; bỏ ô thiếu ảnh. Đổi chất lượng video giữ ảnh. Ảnh gốc hơn 8 MB được giữ, chỉ bản tham chiếu gửi đi được nén.
- Cầu nối chỉ lấy media sau tin nhắn mới có marker, giữ bản nháp của tab đăng nhập, kiểm tra xác thực trước gửi, mở hội thoại riêng hoặc báo lỗi nếu không mở được, giữ lỗi quota.

## Giới hạn còn lại

- **Chưa đăng nhập, tạo ảnh/video hoặc đọc số dư trên Muse.ai thật.** Cloud không có phiên người dùng và truy cập trước đây nhận CONNECT 403. Không thể cam kết dịch vụ/gói tài khoản cho phép 10 render cùng lúc.
- Muse hoặc nhà cung cấp đăng nhập có thể không hỗ trợ view nhúng. Bản này không có API/OAuth chính thức để thay thế nếu đăng nhập bị từ chối. Không giả trạng thái đăng nhập và không nhập mật khẩu vào form tự chế.
- Selector, auth check và cầu nối là không chính thức; Muse đổi giao diện có thể cần cập nhật. Không bảo đảm công khai số dư token/credit cho mọi tài khoản.
- Mô hình, thời lượng, khung hình và 2K/4K là yêu cầu trong prompt; độ giống nhân vật, độ nét gốc và tên model cần kiểm tra trên kết quả thật.
- Kiểm thử Linux/Chromium/Electron không chứng minh launcher hoặc đăng nhập trên Windows thật. `start.bat` chưa được chạy trên máy Windows thật.
- Dữ liệu phiên chỉ là dữ liệu fixture tạm và được dọn sau test. ZIP/Git không chứa `.data`, `.env`, cookie hoặc token người dùng.

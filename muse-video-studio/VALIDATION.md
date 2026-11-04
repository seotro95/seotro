# Xác minh bản 1.4.4

## Kết quả trên Linux

- `npm ci --cache /workspace/.cache/seotro-npm --no-audit --no-fund` từ lockfile thành công. Runtime Electron 45.2.2 tải/cài bằng bộ cài chính thức với checksum bật.
- `npm run build`: TypeScript và Vite thành công. Cảnh báo `use client` của bộ icon không ngăn build.
- Lệnh `npm start` qua launcher phát hành đã mở ứng dụng trên Linux/Xorg với hồ sơ fixture mới, trả HTML/API đúng trạng thái và thoát sạch khi đóng cửa sổ. Không mở Chrome ngoài.
- `npm test`: 7 bài parser/chuyển dự án cũ/kích thước/state, 7 bài máy chủ API trong một nhóm, 3 bài lệnh mở trình duyệt dự phòng và 2 bài phân tích số dư đã qua, không bỏ qua bài nào.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge`: 21 kịch bản trong một nhóm đã qua (22 Node tests), dùng Chromium thật với Muse giả lập trên loopback và hồ sơ tạm.
- `DISPLAY=:97 MUSE_ELECTRON_TEST_NO_SANDBOX=1 npm run test:desktop`: 7 kịch bản trong một nhóm đã qua (8 Node tests), dùng Electron thật trên màn hình Xorg dummy. Cờ tắt sandbox chỉ áp dụng cho fixture trong cloud; launcher phát hành không dùng cờ này.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`: **18 ca đầu** qua trong lượt đầy đủ. Ca chẩn đoán Message mới chờ nhầm một toast không được chức năng tạo ra; sửa test để mở/đóng hộp tài khoản và giữ chi tiết lỗi ở bảng tài khoản, rồi chạy riêng ca này: **1/1 qua**. Không thay mã ứng dụng để xử lý lỗi trong test. Desktop 5 cột, mobile không tràn ngang đã qua.
- Kiểm tra cú pháp Node cho server/cầu nối/desktop/launcher, `bash -n start.sh` và whitespace Git đã qua.

## Trang trò chuyện và ô Message trong bản 1.4.4

- Tái hiện đường dẫn sai: trang đăng nhập ở `/chat`, nhưng worker mở `/` với dashboard không có editor thì `MUSE_COMPOSER_NOT_READY`. Dùng đường dẫn trang Muse đã xác minh thì kiểm tra được ô Message, không gửi nội dung. Không sao chép query hoặc fragment từ URL đăng nhập.
- Ca Chromium nhận ảnh mới và xác nhận ảnh tham chiếu trong iframe cùng miền. Cả việc tìm Message, New chat, theo dõi phản hồi mới và tải kết quả dùng đúng khung. Ô nhập của miền khác không được chọn.
- Ca chuyển hướng trang luồng từ miền fixture đã xác minh sang miền khác bị từ chối bằng `MUSE_WORKSPACE_ORIGIN` trước khi nhập/gửi prompt; không render và worker được đóng.
- Chẩn đoán thiếu editor chứa số lượng và trạng thái trang, che phần đường dẫn riêng tư. Ca hồi quy đưa email, token query/fragment giả và bản nháp riêng vào fixture; thông báo không chứa các dữ liệu đó, không có yêu cầu render phát sinh, worker được đóng.
- Electron thật: nút Kiểm tra ô Message gọi endpoint kiểm tra trang luồng, trả thành công với hai khung và không render. Sau đó 10 ảnh, 10 video từ ảnh và Stop đều chạy qua iframe ở đúng trang `/chat`; khôi phục phiên và popup đăng nhập vẫn qua.
- Đo trực tiếp Electron 1.4.3 cho thấy worker nền có viewport 1280×900 và `document.visibilityState=visible` trên Linux. Không quy lỗi cho trạng thái ẩn và không thay cơ chế hiển thị các view.

## Nút tạo và ô Message trong bản 1.4.3

- Ca UI dùng đúng trạng thái ảnh báo lỗi: `sessionAuthenticated=true`, `authenticated=false`, `composerReady=false`. Chạy với bundle 1.4.2 tái hiện nút TẠO 10 VIDEO vẫn disabled. Sau sửa, nút bật và thao tác Tạo cảnh gửi đúng accountId=1, nhận/phát được kết quả fixture.
- Một phiên được API xác minh giữ trạng thái kết nối khi ô soạn của tab đăng nhập bị ẩn hoặc không có. Ô soạn không được dùng làm bằng chứng xác thực.
- Bộ desktop chạy với trang đăng nhập không có editor khả dụng; cả 10 luồng tự mở New chat, tìm Message trong form ngoài khung Hatch cũ và nhận 10 ảnh đúng từng ô. Chuyển 10 ảnh sang video, Stop và khôi phục phiên đều qua.
- Kiểm thử cầu nối bao gồm ô Message đã hiện sẵn ngoài khung cũ, trang đầu vào phải mở New chat, ảnh tham chiếu trong form, và từ chối chọn ô Search hoặc một trong nhiều ô Message không rõ đích. Không gửi yêu cầu trong các trường hợp chưa xác định được ô nhập.

## Nhận kết nối sau đăng nhập trong bản 1.4.2

- Trước sửa, ca kiểm tra phiên đã lưu trong tab chưa hiển thị trả `authenticated=false`, dù phiên hợp lệ. Đã tái hiện lỗi này và sửa viewport của tab đăng nhập, không chỉ worker. Sau sửa xác minh được mà không phải hiện tab trước.
- Về Studio tự gửi một lần kiểm tra phiên. Kiểm thử đăng nhập trực tiếp và đăng nhập qua popup đều xác minh thành công; phiên được kiểm tra bằng API, không phụ thuộc ô soạn của tab đăng nhập.
- Kiểm tra phiên/API lỗi HTTP 503 hiển thị trạng thái không xác minh được; một ô soạn hiển thị không được dùng làm bằng chứng đăng nhập.
- Bản nháp trong trang có ô soạn bị ẩn không bị xóa để cập nhật phiên. Kiểm tra không gửi chat hoặc render; số yêu cầu tạo nội dung giữ nguyên qua các bước xác minh.
- Phản hồi kết nối hiển thị cố định ở bảng tài khoản. Ca UI kiểm tra phiên đã xác thực nhưng chưa có ô soạn ở tab đăng nhập vẫn gửi được yêu cầu; lỗi HTTP 503 chưa xác thực thì nút tạo khóa. Đóng toast không làm mất thông báo tại bảng tài khoản.

## Lỗi thực tế được tái hiện và sửa

- Log người dùng: `locator.waitFor: Timeout 15000ms exceeded`, locator đầu tiên trỏ vào textarea ẩn có `data-hatch-composer-prehydration-input="true"`.
- Thêm fixture đặt textarea đó trước editor rich text đang hiển thị. Chạy với mã cũ tái hiện đúng timeout 15 giây; chỉ ca hồi quy này thất bại trong khi các ca cũ vẫn qua.
- Sau sửa, chọn editor hiển thị và loại bỏ textarea prehydration, ca hồi quy qua và đúng một yêu cầu được gửi bằng editor thật. Ô prehydration giữ rỗng.
- Kiểm tra trang hydrate chậm: placeholder còn hiển thị nhưng không nhận prompt; timeout được đổi thành `MUSE_COMPOSER_NOT_READY`, không gửi yêu cầu. Khi editor thật sẵn sàng, gửi và nhận ảnh bình thường.
- Kiểm thử Electron còn phát hiện view ẩn có viewport 0×0, khiến editor rich text rộng 0 px. Đã đặt viewport bố cục cho từng worker trước khi tải Muse; không thay đổi mức yêu cầu ảnh/video.
- Cả nhóm Electron desktop chạy với textarea ẩn + editor rich text Message ngoài khung Hatch cũ, gồm 10 ảnh đồng thời, 10 video từ ảnh, Stop và khôi phục phiên. Kiểm tra từng yêu cầu có viewport khác 0 và textarea prehydration vẫn rỗng.

## 10 luồng và đăng nhập nhúng đã chứng minh

- Một cửa sổ Electron chứa Studio và trang đăng nhập Muse giả lập. Không mở Chrome/Edge ngoài. Remote view không có `require`, `studioDesktop` hoặc `museTransport`. IPC từ Studio từ chối endpoint không được phép.
- Đăng nhập một lần trong view Muse, Về Studio và Kiểm tra phiên: đúng một tài khoản xác minh, embeddedLogin=true và maxConcurrency=10.
- Bấm TẠO 10 ẢNH: đủ 10 yêu cầu được gửi và 10 cảnh cùng trạng thái Đang tạo trước khi fixture trả kết quả đầu tiên. Tất cả xác thực bằng cùng phiên. Fixture trả 10 ảnh khác nhau; từng ảnh được so sánh với đúng yêu cầu của cảnh đó.
- Chuyển bộ ảnh sang video: đủ 10 cuộc trò chuyện đang xử lý đồng thời, mỗi cuộc nhận đúng một ảnh tham chiếu và dùng chung phiên. Kết quả hoàn tất được đặt vào 10 ô; view worker được đóng, giữ lại Studio và đăng nhập.
- Dừng cả bộ gửi hủy qua IPC tới cả 10 yêu cầu, fixture nhận đủ 10 lần Stop và các view worker được đóng. Số yêu cầu máy chủ trở về 0.
- Đóng/mở lại ứng dụng với cùng thư mục dữ liệu khôi phục phiên đã lưu và xác minh được qua Kiểm tra phiên khi tab đăng nhập còn ẩn, không bấm đăng nhập lần nữa.
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

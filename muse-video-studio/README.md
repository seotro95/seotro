# Muse AI Studio 1.4.4 · Một tài khoản, 10 luồng đồng thời

Ứng dụng desktop React/TypeScript và Electron cho 10 cảnh ảnh/video. **Bản 1.4 thay cách chạy tuần tự bằng 10 cuộc trò chuyện độc lập trên cùng một phiên Muse. Trang đăng nhập Muse nằm trong cửa sổ tool; không cần cài hoặc mở Chrome/Edge riêng.**

Cầu nối giao diện này **không chính thức**. Đã kiểm thử đăng nhập, 10 luồng, tách kết quả và dừng tác vụ bằng Electron thật với dịch vụ Muse giả lập cục bộ. **Chưa đăng nhập, tạo ảnh/video hoặc đọc số dư trên Muse.ai thật**: cloud chưa có phiên người dùng và các lần truy cập muse.ai nhận CONNECT 403. Muse có thể giới hạn tác vụ đồng thời, từ chối đăng nhập nhúng hoặc thay đổi giao diện. Các kiểm thử không chứng minh gói tài khoản thực tế hỗ trợ 10 render cùng lúc.

## Trang luồng và kiểm tra ô Message trong bản 1.4.4

Mỗi luồng dùng đường dẫn trang Muse đã xác minh sau đăng nhập thay vì luôn mở lại trang gốc. Các tham số truy vấn và fragment không được sao chép từ URL đăng nhập. Nếu ô Message nằm trong iframe hiển thị cùng miền Muse, thao tác nhập, đính kèm ảnh, đọc phản hồi mới và Stop đều thực hiện trong khung đó. Không nhập vào khung của miền khác.

Trước khi chạy cả bộ, bấm **Kiểm tra ô Message** ở bảng tài khoản hoặc hộp **Tài khoản Muse**. Tool mở trang luồng riêng, xác minh phiên và tìm ô nhập mà không gửi prompt hay yêu cầu tạo nội dung; trang kiểm tra được đóng sau đó. Kết quả giữ ở bảng tài khoản. Nếu lỗi, mở **Chi tiết trang luồng**: chẩn đoán gồm miền, đường dẫn đã che phần riêng tư, trạng thái tải/hiển thị, kích thước và số ô nhập. Không thu nội dung chat, bản nháp, mật khẩu, cookie, token hoặc tham số URL.

Đã tái hiện bằng fixture: tài khoản đang ở `/chat` nhưng luồng mở `/` không có editor; dùng lại đường dẫn trò chuyện và xử lý trong iframe thì nhận được kết quả. Đây là sửa lỗi được kiểm chứng cục bộ; chưa xác nhận đây là nguyên nhân duy nhất trên Muse thật của người dùng.

## Sửa nút tạo bị khóa trong bản 1.4.3

Phiên Muse được API xác minh sẽ mở nút tạo ảnh/video ngay cả khi tab đăng nhập chưa hiển thị ô soạn. Mỗi cảnh mở cuộc trò chuyện riêng và tìm ô **Message** ở đó trước khi gửi prompt. Bản này bỏ điều kiện chờ ô soạn trên tab đăng nhập làm khóa cả Studio.

Bộ nhận ô nhập hỗ trợ textarea/ô rich text có nhãn Message và editor Lexical ngoài khung giao diện cũ. Khi trang đầu vào có nút/link New chat nhưng chưa có editor, luồng mở cuộc trò chuyện bằng nút đó. Không dùng ô tìm kiếm; nếu có nhiều ô phù hợp thì báo rõ và chưa gửi prompt. Ảnh tham chiếu được xác nhận ở đúng vùng soạn hoặc form trước khi gửi.

## Nhận phiên đăng nhập trong bản 1.4.2

Sửa trường hợp đã đăng nhập Muse nhưng Studio chưa nhận kết nối. Tab đăng nhập ẩn cũng được cấp kích thước bố cục; khi bấm **← Về Studio**, tool tự kiểm tra lại phiên. Đăng nhập qua popup cũng được xác minh khi quay về Studio. Tab đăng nhập và bản nháp được giữ nguyên; phần tạo nội dung dùng các cuộc trò chuyện riêng.

Ngay cạnh nút **Kiểm tra phiên** luôn có kết quả: đang kiểm tra, đã xác minh, hoặc chưa đọc được trạng thái phiên. Lỗi mạng/HTTP không bị coi là đăng nhập thành công. Nút tạo bật sau khi phiên được xác thực. Mỗi luồng kiểm tra ô nhập của riêng mình trước khi gửi prompt. Việc kiểm tra không gửi prompt hoặc render.

## Sửa lỗi ô soạn Muse trong bản 1.4.1

Khắc phục lỗi `locator.waitFor: Timeout 15000ms exceeded` khi Muse giữ `textarea[data-hatch-composer-prehydration-input="true"]` bị ẩn trước ô nhập thật. Tool lọc ô nhập đang hiển thị trước khi chọn, bỏ qua placeholder chưa hydrate và đợi ô soạn thật tải xong (tối đa 45 giây). Các khung xử lý nền được cấp kích thước bố cục để editor rich text không bị co về 0×0. Nếu trang vẫn chưa sẵn sàng, báo `MUSE_COMPOSER_NOT_READY` và chưa gửi prompt.

Đã tái hiện đúng lỗi bằng fixture có textarea ẩn trước editor rich text; bản cũ timeout và bản sửa đã qua kiểm tra. Ca desktop 10 ảnh/10 video cũng dùng bố cục này. Đây là xác minh lỗi DOM được báo, không thay thế kiểm tra render trên Muse thật.

Đóng hẳn tool cũ trước khi giải nén bản mới đè các tệp chương trình rồi chạy `start.bat`. ZIP không chứa `.data` hoặc `.env`, nên không xóa phiên/cấu hình hiện có. Không xóa hồ sơ đăng nhập để xử lý lỗi ô soạn này.

## Cài và chạy trên Windows

1. Cài Node.js 24+ trên Windows 10/11. Không cần Chrome/Edge cho bản desktop.
2. Đóng tool cũ. Giải nén ZIP mới vào một thư mục riêng, chạy `start.bat`.
3. Lần đầu cần Internet để cài các gói và tải runtime Electron chính thức. Bộ cài Electron kiểm tra checksum. Không đổi chính sách PowerShell; nếu chạy lệnh thủ công, dùng `npm.cmd`.
4. Bấm **Đăng nhập Muse trong tool**. Đăng nhập trực tiếp trên trang Muse/nhà cung cấp trong tab tích hợp. Nếu nhà cung cấp mở popup xác thực, popup vẫn thuộc ứng dụng.
5. Bấm **← Về Studio** để tool tự xác minh phiên. Khi hiện **Đã xác minh**, cả 10 ô có thể dùng cùng phiên đó. Có thể bấm **Kiểm tra phiên** để cập nhật thủ công; kết quả luôn hiện ngay bên cạnh.
6. Nhập 10 prompt hoặc nạp TXT/SRT. Chọn **Tạo ảnh hàng loạt** hoặc **Tạo video**, bấm **TẠO 10 ẢNH / TẠO 10 VIDEO**.

Tool bắt đầu các cảnh đủ điều kiện đồng thời và trả mỗi kết quả về đúng ô. Số luồng đang chạy hiện cạnh tiến độ. Dùng **Dừng tất cả luồng** để ngừng nhận kết quả và gửi Stop tới từng cuộc trò chuyện đang chạy. Muse vẫn có thể tính phí hoặc tiếp tục tác vụ đã nhận. Bấm Tạo 10 lại chỉ chạy phần chưa xong; có thể tạo lại riêng một cảnh. Cảnh tắt, prompt trống, cảnh đã hoàn tất hoặc thiếu ảnh nguồn trong chế độ ảnh→video được bỏ qua.

Các yêu cầu đều dùng tài khoản duy nhất, không có email/gán tài khoản từng cảnh. Khi mở dự án JSON cũ, các gán tài khoản được bỏ qua, prompt và bật/tắt vẫn giữ. Để chuyển kịch bản từ bản web cũ, xuất dự án JSON rồi mở trong bản desktop. Phiên đăng nhập Chrome của bản cũ không tự chuyển sang Electron: đăng nhập một lần trong bản mới. Thư mục phiên cũ không bị xóa.

Trên Linux/macOS có desktop, dùng `bash start.sh`. Chạy bằng lệnh:

```sh
npm ci
npm run build
npm start
```

`npm start` mở ứng dụng desktop. Đóng cửa sổ ứng dụng để dừng máy chủ và các luồng. Máy chủ chỉ lắng nghe 127.0.0.1, mặc định cổng 8788. Nếu cổng bị chiếm, đóng tool cũ hoặc đổi PORT trong `.env`.

## Ảnh, video và đồng nhất nhân vật

- TXT/SRT UTF-8 tối đa 2 MB; mỗi dòng/đoạn TXT hoặc khối SRT là một cảnh. Xem trước trước khi nạp; tối đa 10 cảnh mỗi bộ, không tự cắt nội dung vượt giới hạn.
- Tạo ảnh hàng loạt với mức yêu cầu 2K hoặc 4K. 2K là 2560×1440, 4K là 3840×2160 ở khung ngang; hoán đổi hai chiều khi dọc.
- Bật **Đồng nhất nhân vật** và chọn ảnh chân dung chung hoặc riêng từng ô để gửi ảnh tham chiếu. Tắt tùy chọn để theo prompt độc lập. Mỗi luồng là cuộc trò chuyện mới; không dựa vào trí nhớ hội thoại của luồng khác. Không có ảnh tham chiếu thì không bảo đảm cùng diện mạo nhân vật.
- Video từ prompt hoặc ảnh, mức yêu cầu 360p/720p/1080p/2K/4K. Ở chế độ Từ ảnh, ảnh vẫn được gửi khi tắt khóa nhân vật; chỉ gửi các ô có ảnh nguồn.
- **Chuyển bộ ảnh đã tạo sang video** giữ ảnh gốc và dùng đúng ảnh của từng cảnh. Đổi tab/chất lượng video giữ ảnh. Nếu ảnh tạo lớn hơn 8 MB, chỉ bản tham chiếu gửi đi được nén, giữ kích thước pixel; ảnh gốc vẫn tải được.
- Tải từng kết quả hoặc cả bộ, xem ảnh lớn, phát video thật, mở/xuất dự án JSON, AI Enhance và modifier chung.
- Bảng số dư đọc token/credit có nhãn từ giao diện Muse, gồm số 0 thực sự. Không đọc được thì ghi rõ; không đoán hoặc tự tính. Có thời điểm đọc và nút cập nhật.

Mô hình, thời lượng, khung hình và độ phân giải là **yêu cầu bằng lời trong prompt**, không phải tham số API được Muse xác nhận. Danh sách Omni/Veo theo mô tả người dùng, chưa xác minh trên dịch vụ thật. Tool hiển thị kích thước quan sát được; tệp thấp hơn mức yêu cầu được ghi **Chưa đạt yêu cầu**, không phóng ảnh hoặc đổi nhãn để giả 4K gốc. Độ giống nhân vật và chất lượng AI cần kiểm tra bằng kết quả thực tế.

Chỉnh prompt/ảnh/settings sẽ xóa kết quả liên quan để tránh dùng lại tệp không khớp. Ảnh/video chỉ giữ trong phiên; dự án JSON và localStorage chỉ lưu prompt, bật/tắt và settings. Tải kết quả cần giữ trước khi đóng.

## Đăng nhập và dữ liệu

- Trang Muse chạy trong view Electron riêng, không nằm trong iframe. Mật khẩu được nhập trực tiếp trên trang nhà cung cấp; tool không có form mật khẩu tự chế và không xuất cookie/token.
- Muse và các popup xác thực không được truy cập Node.js hoặc IPC của Studio. Context isolation, sandbox và web security được bật trong ứng dụng phát hành. Không tắt TLS verification.
- Một partition `persist:muse` lưu phiên ở `.data/muse-desktop` trên máy bạn. Không chia sẻ thư mục này hoặc đưa lên Git, ZIP, ảnh chụp/chat. Không đọc hồ sơ Chrome cá nhân.
- Mỗi cảnh tạo một view/hội thoại riêng trong cùng phiên, đóng khi hoàn tất hoặc dừng. Tool chỉ nhận media sau tin nhắn mới có marker, không lấy ảnh/video cũ để giả thành công.
- Trường hợp Muse tải lại một hội thoại cũ, tool thử nút New chat và yêu cầu hội thoại mới trước khi gửi. Không mở được thì báo `MUSE_NEW_CHAT_UNAVAILABLE`.
- Đường gửi desktop đi qua IPC giới hạn endpoint và máy chủ cục bộ, tránh giới hạn 6 kết nối HTTP/1 của trang web. Máy chủ giữ tối đa 10 yêu cầu đang hoạt động; hoàn tất một yêu cầu chỉ giải phóng một chỗ.
- Không cần `.env` cho đăng nhập desktop mặc định. Không gửi mật khẩu/cookie/token trong chat.

## Lỗi và giới hạn thực tế

- Không tải được runtime: kiểm tra Internet và quyền ghi thư mục tool rồi chạy `start.bat` lại. Không vô hiệu checksum hoặc TLS.
- `MUSE_LOGIN_REQUIRED`: mở tab đăng nhập trong tool, hoàn tất đăng nhập, Về Studio rồi Kiểm tra phiên.
- Nếu Muse/nhà cung cấp từ chối trình đăng nhập nhúng, bản này chưa có API/OAuth chính thức thay thế. Không giả trạng thái đăng nhập; cần phương thức xác thực được dịch vụ hỗ trợ.
- `MUSE_CONCURRENCY_LIMIT`: đã có 10 luồng cục bộ; đợi một luồng hoàn tất. Lỗi quota/429 do Muse trả được giữ ở đúng ô; không tự đổi tài khoản, tăng hạn mức hoặc retry hàng loạt.
- `MUSE_NEW_CHAT_UNAVAILABLE`, `MUSE_COMPOSER_NOT_READY`, `MUSE_COMPOSER_AMBIGUOUS`, `MUSE_ATTACHMENT_UNAVAILABLE`, `MUSE_UPLOAD_NOT_READY`: giao diện Muse có thể đã đổi hoặc chưa nhận ảnh. Chưa gửi prompt khi thiếu điều kiện bắt buộc.
- `MUSE_TIMEOUT`, `MUSE_NO_IMAGE`, `MUSE_NO_VIDEO`, `MUSE_MEDIA_UNREADABLE`: mở lịch sử trong tab Muse kiểm tra trước khi thử lại để tránh tạo trùng hoặc tính phí hai lần.

## Chế độ web và adapter nâng cao

`npm run start:web` hoặc `npm run dev` giữ cách phục vụ web cũ. Chế độ này dùng Chrome/Edge riêng để đăng nhập khi MUSE_TRANSPORT=browser. Giới hạn kết nối của trình duyệt có thể giảm số HTTP request chạy đồng thời; **dùng bản desktop mặc định để chạy đủ 10 luồng của tool**. Không mở `index.html` bằng `file://`.

`.env.example` mô tả các tùy chọn. `MUSE_DESKTOP_DATA` đổi thư mục dữ liệu Electron. `MUSE_BALANCE_SELECTOR` chỉ vùng số dư có nhãn, không dùng vùng chat. `MUSE_PROFILE_ROOT`, `MUSE_ACCOUNT_PROFILE`, `MUSE_BROWSER_CHANNEL` chỉ áp dụng cho đăng nhập trình duyệt ngoài của chế độ web. Không trỏ dữ liệu Electron vào hồ sơ Chrome cũ.

Nếu đã có adapter tương thích, dùng `MUSE_TRANSPORT=adapter`, `MUSE_ADAPTER_URL`, `MUSE_ADAPTER_TOKEN` nếu cần. Adapter xác thực **một** tài khoản, accountId=1; mọi ID khác bị từ chối. Không trỏ URL adapter vào trang chủ Muse.ai. Adapter cũng có thể nhận 10 yêu cầu đồng thời và phải tuân thủ hạn mức của nhà cung cấp. Đây là hợp đồng của ứng dụng, không phải API chính thức của Muse:

- `POST /video`: `{accountId:1,prompt,modelDisplayName,aspectRatio,durationSeconds,resolution,sourceMode,characterLock,referenceImage?}`. Kết quả `{base64,mimeType}` với MP4/WebM/QuickTime.
- `POST /image`: `{accountId:1,prompt,aspectRatio,resolution,characterLock,referenceImage?}`. Kết quả `{base64,mimeType}` với PNG/JPEG/WebP.
- `referenceImage`: `{base64,mimeType}`. Ảnh chỉ gửi khi cần; ảnh→video luôn cần nguồn ảnh.
- `POST /text`: `{accountId:1,prompt}` → `{text}`.
- Lỗi HTTP 4xx/5xx với `{error}`. Timeout 10 phút, mỗi yêu cầu tối đa 12 MB, phản hồi tối đa 150 MB. Token bearer chỉ có phía máy chủ.

## Kiểm thử và nguồn

```sh
npm run build
npm test
CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
npm run test:desktop
```

Test desktop cần màn hình/virtual display và runtime Electron (lần đầu: `node node_modules/electron/install.js`). Trên Linux cloud có thể dùng Xorg dummy/Xvfb. Môi trường kiểm thử không hỗ trợ sandbox có thể bật **riêng cho fixture** `MUSE_ELECTRON_TEST_NO_SANDBOX=1`; launcher phát hành không dùng cờ này.

Fixture desktop dùng một phiên giả lập và chặn kết quả cho tới khi cả 10 yêu cầu đã được gửi, rồi trả ảnh khác nhau để xác minh ánh xạ từng ô; đồng thời kiểm tra video từ ảnh, hủy cả 10 và lưu phiên sau mở lại. Test không gửi yêu cầu đến Muse thật. Xem `VALIDATION.md`. Launcher Windows chưa được chạy trên Windows thật.

**Chẩn đoán API → Kiểm thử giao diện** dùng clip/ảnh 640×360 có nhãn TEST CLIP/TEST IMAGE, không tạo nội dung AI và không chứng minh đăng nhập/hạn mức/chất lượng.

Nguồn: [Electron](https://github.com/electron/electron), [muse-mcp (không chính thức)](https://github.com/degokisss/muse-mcp), [Muse Gadget SDK](https://github.com/facebookincubator/muse-gadget-sdk). Cầu nối tự triển khai, không chạy mã community hoặc dùng SDK gadget để giả API tạo video.

Mỗi cloud task đã có môi trường riêng; dùng checkout hiện có, không tạo Git worktree cho setup. Snapshot không giữ tiến trình ứng dụng đang chạy.

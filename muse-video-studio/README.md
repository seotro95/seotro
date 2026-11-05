# Muse AI Studio 1.4.7 · Một tài khoản, 10 cảnh

Có bản Windows x64 đóng gói đầy đủ và bản mã nguồn. Trang đăng nhập Muse nằm trong cửa sổ tool. Mười cảnh dùng chung một phiên tài khoản và được gửi lần lượt để tránh trộn hội thoại.

## Bản Windows đầy đủ — không cần bản cũ

1. Giải nén **toàn bộ** ZIP Windows vào một thư mục mới, không chạy trong cửa sổ xem ZIP.
2. Mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Runtime Electron/Node và thư viện đã có trong gói; không cần cài Node.js, npm hay Chrome riêng.
3. Đăng nhập Muse trong tab tích hợp, quay **← Về Studio**, bấm **Kiểm tra phiên**.
4. Có thể bấm **Kiểm tra ô Message** trước khi tạo. Bước này tìm ô nhập trong trang luồng, không gửi prompt hoặc render.
5. Nhập 10 prompt hoặc TXT/SRT, chọn **Tạo ảnh hàng loạt** / **Tạo video**, bấm **TẠO 10 ẢNH / VIDEO**.

Không chép `.data`, `.env`, `node_modules` hoặc các tệp từ bản cũ. Gói tạo hồ sơ mới trong `resources/app/.data/muse-desktop`. Cần Internet và tài khoản Muse có quyền tạo nội dung tương ứng. Phiên bản **1.4.7** hiện trên thanh ứng dụng và tiêu đề cửa sổ. Bản đóng gói chọn cổng cục bộ trống lần đầu và giữ cổng đó khi mở lại để duy trì kịch bản đã lưu.

Cầu nối giao diện **không chính thức**. Kiểm thử dùng Chromium/Electron thật và dịch vụ giả lập cục bộ; chưa tự động tạo media hoặc đọc số dư trên Muse.ai thật. Người dùng xác nhận có thể gửi/nhận tin nhắn thủ công trong tab Muse của tool. Tài khoản thật có thể giới hạn render đồng thời, từ chối đăng nhập nhúng hoặc thay đổi giao diện. Các lựa chọn model, độ nét và thời lượng là yêu cầu bằng prompt, cần xác nhận bằng kết quả thật.

## Hội thoại chung, hàng đợi và ảnh tải xuống trong bản 1.4.7

Log `MUSE_NEW_CHAT_UNAVAILABLE` do tool tạo ra trước khi gửi prompt. Nó không chứng minh Muse từ chối tạo ảnh/video hoặc tài khoản hết hạn mức. Cầu nối đăng nhập hiện dùng một hàng đợi trên cùng tài khoản, mặc định một cảnh mỗi lượt, và có thể nối tiếp hội thoại hiện tại mà không yêu cầu New chat. Bấm Tạo 10 vẫn xử lý đủ các cảnh hợp lệ; giao diện phân biệt cảnh đang chạy với cảnh đang chờ. Dừng bộ cũng hủy các cảnh chưa được gửi.

Phản hồi chỉ được đọc sau marker của đúng yêu cầu và trước tin nhắn người dùng kế tiếp. Khi phát hiện các yêu cầu xen kẽ, tool dừng nhận kết quả thay vì ghép ảnh của cảnh khác. Ảnh được so dấu vân tay pixel với các cảnh đã nhận gần đây; ảnh trùng cảnh khác bị báo lỗi, không tính là hoàn tất và không tự gửi lại.

Ảnh được giải mã ở kích thước thật, WebP/JPEG/AVIF được chuẩn hóa thành PNG khi cần. Nút tải ảnh luôn xuất tệp PNG thực sự, gồm cả ảnh từ adapter; không chỉ đổi đuôi tệp. Không phóng ảnh để giả độ nét. Nếu tệp không giải mã được thì báo lỗi, không xuất dữ liệu hỏng.

Một tài khoản Muse vẫn có thể có giới hạn dịch vụ thực tế. Bản này không khẳng định 10 hội thoại của tài khoản Muse tách biệt hoặc 10 render cùng lúc được hỗ trợ. Adapter API có các yêu cầu độc lập vẫn có thể xử lý song song theo cấu hình kết nối.

Bản này cũng giữ sửa nhập Message: textarea hoạt động dù còn nhãn prehydration, chuyển editor sau ký tự đầu, giữ đủ prompt và chỉ nhấn gửi một lần. Rich editor hiển thị được ưu tiên; bản nháp ngoài yêu cầu được giữ nguyên.

## Chạy bản mã nguồn

Cần Node.js 24+. Giải nén mã nguồn vào thư mục mới, chạy `start.bat` trên Windows hoặc `bash start.sh` trên Linux/macOS có desktop. Lần đầu tải npm packages và runtime Electron chính thức, có kiểm tra checksum. PowerShell có thể dùng `npm.cmd` mà không đổi execution policy.

```sh
npm ci
npm run build
npm start
```

Máy chủ mã nguồn mặc định chỉ lắng nghe 127.0.0.1:8788. Bản desktop đóng gói dùng cổng trống. Đóng cửa sổ để dừng app. Giữ hoặc tải kết quả trước khi đóng; dự án JSON lưu kịch bản và thiết lập.

## Đóng gói từ mã nguồn

Môi trường build cần Node 24, `npm ci`, `npm run build` và Python 3. Windows ZIP dùng runtime Electron x64 chính thức, kiểm tra checksum từ package Electron đã khóa phiên bản. Chỉ sao chép app, bundle web, Playwright Core và giấy phép; không sao chép hồ sơ hoặc `.env`.

```sh
python3 scripts/package_portable.py --platform win32 --output /path/to/artifacts
python3 scripts/package_portable.py --platform linux --output /path/to/portable-check --no-zip
```

## Ảnh, video và đồng nhất nhân vật

- TXT/SRT UTF-8 tối đa 2 MB; mỗi dòng/đoạn TXT hoặc khối SRT là một cảnh. Xem trước trước khi nạp; tối đa 10 cảnh mỗi bộ, không tự cắt nội dung vượt giới hạn.
- Tạo ảnh hàng loạt với mức yêu cầu 2K hoặc 4K. 2K là 2560×1440, 4K là 3840×2160 ở khung ngang; hoán đổi hai chiều khi dọc.
- Bật **Đồng nhất nhân vật** và chọn ảnh chân dung chung hoặc riêng từng ô để gửi ảnh tham chiếu. Tắt tùy chọn để theo prompt độc lập. Mỗi cảnh có prompt riêng; hội thoại có thể được dùng lại khi Muse không có New chat. Không có ảnh tham chiếu thì không bảo đảm cùng diện mạo nhân vật.
- Video từ prompt hoặc ảnh, mức yêu cầu 360p/720p/1080p/2K/4K. Ở chế độ Từ ảnh, ảnh vẫn được gửi khi tắt khóa nhân vật; chỉ gửi các ô có ảnh nguồn.
- **Chuyển bộ ảnh đã tạo sang video** giữ ảnh gốc và dùng đúng ảnh của từng cảnh. Đổi tab/chất lượng video giữ ảnh. Nếu ảnh tạo lớn hơn 8 MB, chỉ bản tham chiếu gửi đi được nén, giữ kích thước pixel; ảnh gốc vẫn tải được.
- Tải từng kết quả hoặc cả bộ, xem ảnh lớn, phát video thật, mở/xuất dự án JSON, AI Enhance và modifier chung.
- Bảng số dư đọc token/credit có nhãn từ giao diện Muse, gồm số 0 thực sự. Không đọc được thì ghi rõ; không đoán hoặc tự tính. Có thời điểm đọc và nút cập nhật.

Mô hình, thời lượng, khung hình và độ phân giải là **yêu cầu bằng lời trong prompt**, không phải tham số API được Muse xác nhận. Danh sách Omni/Veo theo mô tả người dùng, chưa xác minh trên dịch vụ thật. Tool hiển thị kích thước quan sát được; tệp thấp hơn mức yêu cầu được ghi **Chưa đạt yêu cầu**, không phóng ảnh hoặc đổi nhãn để giả 4K gốc. Độ giống nhân vật và chất lượng AI cần kiểm tra bằng kết quả thực tế.

Chỉnh prompt/ảnh/settings sẽ xóa kết quả liên quan để tránh dùng lại tệp không khớp. Ảnh/video chỉ giữ trong phiên; dự án JSON và localStorage chỉ lưu prompt, bật/tắt và settings. Tải kết quả cần giữ trước khi đóng.

## Đăng nhập và dữ liệu

- Trang Muse chạy trong view Electron riêng, không nằm trong iframe. Mật khẩu được nhập trực tiếp trên trang nhà cung cấp; tool không có form mật khẩu tự chế và không xuất cookie/token.
- Muse và các popup xác thực không được truy cập Node.js hoặc IPC của Studio. Context isolation, sandbox và web security được bật trong ứng dụng phát hành. Không tắt TLS verification.
- Một partition `persist:muse` lưu phiên ở `.data/muse-desktop` trong thư mục app trên máy bạn (Windows đầy đủ: `resources/app/.data/muse-desktop`). Không chia sẻ thư mục này hoặc đưa lên Git, ZIP, ảnh chụp/chat. Không đọc hồ sơ Chrome cá nhân.
- Mỗi cảnh tạo một view xử lý trong cùng phiên, dùng lại hội thoại khi cần và đóng view khi hoàn tất hoặc dừng. Tool chỉ nhận media sau tin nhắn mới có marker, không lấy ảnh/video cũ để giả thành công.
- Chế độ Muse mặc định không bắt buộc có New chat. Cảnh sau nối tiếp bằng marker mới, không đọc lại media của các lượt trước.
- Đường gửi desktop đi qua IPC giới hạn endpoint và máy chủ cục bộ, tránh giới hạn 6 kết nối HTTP/1 của trang web. Máy chủ giữ tối đa 10 yêu cầu đang hoạt động; hoàn tất một yêu cầu chỉ giải phóng một chỗ.
- Không cần `.env` cho đăng nhập desktop mặc định. Không gửi mật khẩu/cookie/token trong chat.

## Lỗi và giới hạn thực tế

- Không tải được runtime: kiểm tra Internet và quyền ghi thư mục tool rồi chạy `start.bat` lại. Không vô hiệu checksum hoặc TLS.
- `MUSE_LOGIN_REQUIRED`: mở tab đăng nhập trong tool, hoàn tất đăng nhập, Về Studio rồi Kiểm tra phiên.
- Nếu Muse/nhà cung cấp từ chối trình đăng nhập nhúng, bản này chưa có API/OAuth chính thức thay thế. Không giả trạng thái đăng nhập; cần phương thức xác thực được dịch vụ hỗ trợ.
- `MUSE_CONCURRENCY_LIMIT`: đã có 10 cảnh đang xử lý hoặc chờ; đợi một cảnh hoàn tất. Lỗi quota/429 do Muse trả được giữ ở đúng ô; không tự đổi tài khoản, tăng hạn mức hoặc retry hàng loạt.
- `MUSE_NEW_CHAT_UNAVAILABLE`, `MUSE_COMPOSER_NOT_READY`, `MUSE_COMPOSER_AMBIGUOUS`, `MUSE_ATTACHMENT_UNAVAILABLE`, `MUSE_UPLOAD_NOT_READY`: giao diện Muse có thể đã đổi hoặc chưa nhận ảnh. Chưa gửi prompt khi thiếu điều kiện bắt buộc.
- `MUSE_SUBMIT_NOT_ACKNOWLEDGED`: tool chưa xác nhận Muse nhận prompt sau Enter; không tự gửi lại. Kiểm tra cuộc trò chuyện trước khi thử lại.
- `MUSE_TIMEOUT`, `MUSE_NO_IMAGE`, `MUSE_NO_VIDEO`, `MUSE_MEDIA_UNREADABLE`: mở lịch sử trong tab Muse kiểm tra trước khi thử lại để tránh tạo trùng hoặc tính phí hai lần.

## Chế độ web và adapter nâng cao

`npm run start:web` hoặc `npm run dev` giữ cách phục vụ web cũ. Chế độ này dùng Chrome/Edge riêng để đăng nhập khi MUSE_TRANSPORT=browser. Giới hạn kết nối của trình duyệt có thể giảm số HTTP request chạy đồng thời; **dùng bản desktop mặc định để xử lý toàn bộ 10 cảnh trong hàng đợi**. Không mở `index.html` bằng `file://`.

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
CHROMIUM_PATH=/usr/bin/chromium node tests/muse-serial.test.mjs
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
npm run test:desktop
# Sau khi chuẩn bị gói Linux, đặt MUSE_PORTABLE_EXECUTABLE rồi chạy:
node tests/portable.test.mjs
```

Test desktop cần màn hình/virtual display và runtime Electron (lần đầu: `node node_modules/electron/install.js`). Trên Linux cloud có thể dùng Xorg dummy/Xvfb. Môi trường kiểm thử không hỗ trợ sandbox có thể bật **riêng cho fixture** `MUSE_ELECTRON_TEST_NO_SANDBOX=1`; launcher phát hành không dùng cờ này.

Fixture độc lập quảng bá khả năng chạy song song để kiểm tra nhánh đó; đây không phải bằng chứng Muse thật có 10 hội thoại riêng. Kiểm thử serial và gói độc lập dùng lịch sử chung, không có New chat, xác minh đủ 10 ảnh qua hàng đợi và các tệp PNG tải về; đồng thời kiểm tra video từ ảnh, hủy cả 10 và lưu phiên sau mở lại. Test không gửi yêu cầu đến Muse thật. Xem `VALIDATION.md`. Runtime Windows được kiểm tra checksum và cấu trúc gói; cloud Linux không chạy được Windows EXE. Bản đóng gói Linux cùng bố cục được kiểm thử với hồ sơ mới.

**Chẩn đoán API → Kiểm thử giao diện** dùng clip/ảnh 640×360 có nhãn TEST CLIP/TEST IMAGE, không tạo nội dung AI và không chứng minh đăng nhập/hạn mức/chất lượng.

Nguồn: [Electron](https://github.com/electron/electron), [muse-mcp (không chính thức)](https://github.com/degokisss/muse-mcp), [Muse Gadget SDK](https://github.com/facebookincubator/muse-gadget-sdk). Cầu nối tự triển khai, không chạy mã community hoặc dùng SDK gadget để giả API tạo video.

Mỗi cloud task đã có môi trường riêng; dùng checkout hiện có, không tạo Git worktree cho setup. Snapshot không giữ tiến trình ứng dụng đang chạy.

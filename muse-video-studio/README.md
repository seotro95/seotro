# Muse AI · 10-Slot Video Workstation 1.1.0

Bản web độc lập React/TypeScript cho 10 phân cảnh. Bản 1.1.0 bổ sung **đăng nhập tài khoản Muse bằng cửa sổ Chrome/Edge riêng**, gửi prompt/ảnh và lấy video mới hiển thị trong phản hồi. Đây là cầu nối trình duyệt **không chính thức**, không phải SDK/API được Muse cam kết hỗ trợ.

**Đã kiểm thử với trang giả lập cục bộ, chưa đăng nhập hoặc tạo video trên Muse.ai thật.** Môi trường phát triển chưa có tài khoản và bị proxy từ chối truy cập muse.ai (CONNECT 403). Người dùng cần đăng nhập và thử một cảnh trên máy của mình để xác minh với dịch vụ thật. Nếu Muse đổi giao diện, selector trong `muse-browser.mjs` có thể cần cập nhật.

## Mở tool và kết nối tài khoản

1. Cài **Node.js 24 trở lên** từ https://nodejs.org/ và **Google Chrome hoặc Microsoft Edge** trên máy chạy tool.
2. Giải nén ZIP vào thư mục mới. Windows: chạy `start.bat`; Linux/macOS: `bash start.sh` trên máy có giao diện đồ họa. Lần đầu cần Internet đến registry.npmjs.org để cài thư viện. Trình duyệt mở khi máy chủ sẵn sàng; giữ cửa sổ máy chủ chạy.
3. Trong tool, mở **10 Tài khoản Muse → Kết nối #1**. Tool mở Muse trong một hồ sơ Chrome/Edge riêng cho slot đó.
4. Đăng nhập Muse trực tiếp trong cửa sổ vừa mở, bao gồm xác minh tài khoản nếu dịch vụ yêu cầu. Quay lại tool và bấm **Kiểm tra phiên #1**. Tool cũng kiểm tra phiên định kỳ khi hộp quản lý tài khoản đang mở.
5. Chỉ khi thấy **Đã xác minh** mới tạo thử một cảnh. Nếu thành công, kết nối các slot tiếp theo và chạy hàng loạt.

Đăng nhập trong cửa sổ Chrome thông thường không đăng nhập hồ sơ riêng do tool mở. Mỗi slot có hồ sơ riêng; chỉ một cửa sổ hồ sơ được mở tại một thời điểm để giảm tài nguyên. Khi đổi slot, cửa sổ cũ đóng và phiên được giữ trên đĩa. Khi tạo cảnh, tool mở đúng hồ sơ của slot và kiểm tra lại phiên trước khi gửi. Hàng đợi chỉ chạy các slot đang bật và có phiên đã xác minh; các slot còn lại không được gửi yêu cầu.

Email trong bảng là nhãn bạn đặt. Việc đăng nhập được xác minh từ phiên trình duyệt, không dựa vào email hoặc sự tồn tại của thư mục hồ sơ. Khi khởi động lại máy chủ, bấm Kết nối/Kiểm tra phiên để xác minh các phiên đã lưu.

Nếu muốn chạy bằng lệnh:

```sh
npm ci
npm run build
npm start
```

Máy chủ mặc định ở cổng 8788, chỉ lắng nghe 127.0.0.1. Nhập địa chỉ mà cửa sổ máy chủ in ra nếu trình duyệt không tự mở. Không mở `index.html` qua `file://`. Ctrl+C dùng để tắt máy chủ; `Terminate batch job (Y/N)?` là câu hỏi của CMD khi nhận lệnh dừng.

## Dữ liệu và quyền riêng tư

- Mật khẩu nhập trực tiếp trên trang đăng nhập của Muse/nhà cung cấp, không nhập vào form của tool. Tool không xuất cookie hoặc token của trình duyệt.
- Phiên được Chrome/Edge lưu trong `.data/muse-accounts/slot-01` đến `slot-10` trên máy bạn. Không đưa thư mục này lên Git, ZIP, ảnh chụp hay chat. Không chia sẻ thư mục tool có chứa `.data` cho người khác.
- Tool dùng hồ sơ riêng; không đọc hồ sơ Chrome mặc định của bạn. Không dùng chung một hồ sơ với tiến trình Chrome khác.
- Prompt và ảnh được gửi đến Muse khi bấm tạo. Các yêu cầu có thể tiêu hạn mức của tài khoản theo chính sách Muse. Kiểm tra phiên không gửi chat hoặc render.
- Dừng sẽ ngừng hàng đợi và thử bấm Stop ở lượt đang chạy; không đảm bảo dịch vụ hoàn credit hoặc dừng tác vụ đã nhận.
- Không gõ chat thủ công trong cửa sổ Muse khi tool đang tạo video. Nếu phát hiện bản nháp chưa gửi hoặc lượt đang chạy, tool báo lỗi thay vì ghi đè/chuyển hồ sơ.

## Video, mô hình và ảnh tham chiếu

Mô hình, độ phân giải, thời lượng và khung hình trong UI được gửi cho Muse **dưới dạng yêu cầu trong prompt**, không phải tham số API được bảo đảm thi hành. Danh sách Omni/Veo lấy từ mô tả người dùng; chưa xác minh dịch vụ cung cấp đủ các lựa chọn đó. Muse quyết định khả năng thực tế. Video trả về hiển thị thời lượng và kích thước quan sát được để đối chiếu; chưa xác minh được tên mô hình thực sự đã sử dụng.

Ảnh tham chiếu được tải qua ô đính kèm trong Muse. Nếu không tìm thấy ô tải hoặc ảnh chưa xuất hiện, tool báo lỗi trước khi gửi prompt. Yêu cầu giữ diện mạo nhân vật không chứng minh độ giống giọng/mặt hoặc chất lượng R2V. Hãy xem kết quả thực tế.

Tool chỉ lấy video trong phản hồi sau tin nhắn mới có dấu nhận diện riêng; không lấy video cũ trong lịch sử để giả lập hoàn tất. Nếu Muse chỉ trả văn bản, lỗi, quá hạn hoặc video không đọc được, cảnh không được đánh dấu thành công. Trường hợp video hiển thị nhưng chưa đọc được dữ liệu, mở cửa sổ Muse để tải trực tiếp.

## Các thao tác khác

- 10 slot responsive; prompt và nhãn email sửa riêng; bật/tắt từng slot.
- Ảnh PNG/JPG/WebP tối đa 8 MB; chọn ảnh chung đồng bộ 10 cảnh, ảnh riêng, dùng lại và gỡ ảnh. Giới hạn upload thực tế của Muse có thể thấp hơn.
- TXT/SRT UTF-8 tối đa 2 MB, bỏ timestamp và số thứ tự; xem trước, 2 kịch bản mẫu, tối đa 10 cảnh. Ít hơn 10 cảnh thì các ô còn lại trống; quá 10 cảnh không bị âm thầm cắt bỏ.
- Hàng đợi tuần tự, bỏ cảnh đã hoàn tất và slot chưa sẵn sàng, tạo lại một cảnh, dừng/tiếp tục, nhật ký lỗi và gợi ý.
- AI Enhance gửi yêu cầu viết prompt tiếng Anh qua cùng phiên Muse của slot. Modifier chung được nối vào prompt tạo video.
- Player thật, tải một video hoặc tải tất cả tuần tự. Trình duyệt có thể hỏi quyền tải nhiều tệp.
- Tự lưu prompt, nhãn email, bật/tắt và settings trong localStorage; mở/xuất dự án JSON. Ảnh và video chỉ giữ trong phiên. Tải video cần giữ trước khi đóng trang.
- Chỉnh prompt/ảnh/settings xóa kết quả cũ để tránh dùng video không còn khớp. Đổi email/bật tắt không xóa video.

## Kiểm thử giao diện không tiêu render

Chọn **Chẩn đoán API → Kiểm thử giao diện**. Mọi cảnh dùng cùng clip 4s/360p/16:9 có nhãn `TEST CLIP - NOT AI GENERATED`. Chế độ này không tạo nội dung theo prompt, không dùng ảnh hoặc AI Enhance, không chứng minh phiên đăng nhập hay chất lượng AI.

## Xử lý lỗi thường gặp

- `MUSE_BROWSER_UNAVAILABLE`: cài Chrome hoặc Edge trên máy đang chạy máy chủ, không chỉ trên máy xem giao diện. Có thể đặt `MUSE_BROWSER_CHANNEL=msedge` trong `.env` để dùng Edge.
- `MUSE_LOGIN_REQUIRED`: bấm Kết nối cho đúng slot, hoàn tất đăng nhập trong cửa sổ tool mở, rồi Kiểm tra phiên.
- `MUSE_PROFILE_BUSY`: đóng cửa sổ/tiến trình khác đang dùng hồ sơ riêng đó. Không xóa dữ liệu đăng nhập để xử lý một lỗi khóa hồ sơ.
- `MUSE_DRAFT_EXISTS`/`MUSE_CHAT_BUSY`: xử lý bản nháp hoặc đợi lượt hiện tại trong Muse hoàn tất trước.
- `MUSE_ATTACHMENT_UNAVAILABLE`/`MUSE_UPLOAD_NOT_READY`: Muse đổi ô đính kèm hoặc chưa nhận ảnh. Kiểm tra cửa sổ Muse; không tự gửi prompt khi chưa có ảnh yêu cầu.
- `MUSE_TIMEOUT`/`MUSE_NO_VIDEO`: kiểm tra phản hồi của Muse trước khi thử lại để tránh tạo trùng. Cần quyền/hạn mức tạo video tương ứng trong tài khoản.

## Cấu hình tùy chọn

Không cần `.env` cho cách đăng nhập trình duyệt mặc định. Nếu cần, sao chép `.env.example` thành `.env` và khởi động lại máy chủ:

```dotenv
MUSE_TRANSPORT=browser
MUSE_BROWSER_CHANNEL=msedge
PORT=8788
```

`MUSE_PROFILE_ROOT` có thể đổi nơi lưu hồ sơ. Giữ nguyên thư mục đó để tái sử dụng phiên. Cầu nối chỉ điều khiển các trình duyệt nó tự mở, không gắn vào cổng debug của Chrome cá nhân.

### Adapter API riêng (nâng cao)

Nếu đã có adapter tương thích, đặt `MUSE_TRANSPORT=adapter`, `MUSE_ADAPTER_URL` và `MUSE_ADAPTER_TOKEN` nếu cần. Không trỏ URL adapter vào trang chủ Muse.ai. Adapter chịu trách nhiệm xác thực và ánh xạ `accountId` 1–10; khi dùng adapter, các nút đăng nhập trình duyệt không xuất hiện.

Backend gọi `POST {MUSE_ADAPTER_URL}/video` với:

```json
{"accountId":1,"prompt":"scene + modifier","modelDisplayName":"Omni 1.1 Flash","aspectRatio":"16:9","durationSeconds":4,"resolution":"360p","referenceImage":{"base64":"...","mimeType":"image/png"}}
```

`referenceImage` chỉ có khi bật ảnh tham chiếu. Kết quả: `{"base64":"...","mimeType":"video/mp4"}` (hoặc WebM/QuickTime). Text: `POST /text` với `{"accountId":1,"prompt":"..."}` → `{"text":"..."}`. Lỗi HTTP 4xx/5xx với `{"error":"..."}`. Timeout 10 phút, phản hồi tối đa 150 MB. Token thêm dưới dạng bearer trên máy chủ, không gửi ra frontend. Đây là hợp đồng adapter của ứng dụng, không phải tài liệu API chính thức của Muse.

## Kiểm tra và nguồn tham khảo

```sh
npm run build
npm test
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge
```

Các kiểm tra cầu nối dùng trang Muse giả lập cục bộ và hồ sơ tạm, không gửi chat/video đến Muse.ai. Test giao diện dùng adapter/phản hồi giả để kiểm tra trạng thái và payload. Không xem kết quả test giả lập là chứng minh đăng nhập hoặc render thật. Launcher Windows chưa được chạy trên Windows thật.

Tham khảo giao diện/protocol công khai: [muse-mcp (không chính thức)](https://github.com/degokisss/muse-mcp), [Muse Gadget SDK của facebookincubator](https://github.com/facebookincubator/muse-gadget-sdk). SDK gadget có quy trình ghép thiết bị riêng; bản Windows này sử dụng cầu nối trình duyệt tự triển khai, không dùng SDK gadget hoặc chạy mã thư viện community.

Mỗi cloud task đã có môi trường riêng; dùng checkout sẵn có, không tạo Git worktree cho setup. Để kiểm tra dịch vụ thật từ cloud cần truy cập Muse và phiên đăng nhập được xác thực; snapshot không giữ tiến trình trình duyệt đang chạy.

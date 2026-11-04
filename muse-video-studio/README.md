# Muse AI · 10-Slot Video Workstation 1.2.0

Bản web độc lập React/TypeScript cho 10 phân cảnh. Tool có **đăng nhập tài khoản Muse bằng cửa sổ Chrome/Edge riêng**, gửi prompt/ảnh và lấy video mới hiển thị trong phản hồi. Đây là cầu nối trình duyệt **không chính thức**, không phải SDK/API được Muse cam kết hỗ trợ.

**Đã kiểm thử với trang giả lập cục bộ, chưa đăng nhập hoặc tạo video trên Muse.ai thật.** Môi trường phát triển chưa có tài khoản và bị proxy từ chối truy cập muse.ai (CONNECT 403). Người dùng cần đăng nhập và thử một cảnh trên máy của mình để xác minh với dịch vụ thật. Nếu Muse đổi giao diện, selector trong `muse-browser.mjs` có thể cần cập nhật.

## Điểm mới ở bản 1.2.0

- **Một tài khoản dùng chung**: đăng nhập một hồ sơ Muse, bật Tự dùng chung cho ô chưa gán tài khoản. Các ô trống tự dùng phiên đã xác minh đầu tiên. Có thể chọn tài khoản dùng chung cụ thể hoặc gán riêng từng cảnh. Ô gán riêng không bị chuyển sang tài khoản khác nếu phiên đó hết hạn.
- **Bảng số dư token/credit** theo đúng tài khoản được hiển thị, kèm thời điểm đọc và nút cập nhật. Chỉ hiển thị số đọc được từ vùng số dư có nhãn trong Muse; nếu chưa đọc được thì ghi rõ, không tự tính hoặc coi là 0. Credit được ghi là credit, không đổi tên thành token.
- **Tạo ảnh hàng loạt** theo 10 prompt hoặc TXT/SRT, yêu cầu 2K/4K, tùy chọn Đồng nhất nhân vật. Khi tắt, ảnh tham chiếu không gửi và mỗi cảnh được yêu cầu bám prompt độc lập.
- **Tạo video từ prompt hoặc ảnh**; mức yêu cầu 720p, 1080p, 2K, 4K (có 360p cho kiểm tra nhanh). Có thể chuyển bộ ảnh đã tạo thành ảnh đầu vào video, giữ prompt và kết quả ảnh.
- **Kiểm tra kích thước thật**: đọc kích thước ảnh từ dữ liệu ảnh đã giải mã, không tin một nhãn metadata 4K. Video lấy metadata của player Muse. Tệp thấp hơn mức yêu cầu được ghi Chưa đạt yêu cầu; không nội suy rồi gắn nhãn là ảnh/video AI 4K gốc.

2K trong bản này nghĩa là QHD 2560×1440, 4K là UHD 3840×2160 ở khung ngang. Khung dọc hoán đổi hai chiều. Mức yêu cầu không bảo đảm Muse hỗ trợ đầu ra tương ứng; hãy xem nhãn kiểm tra và kích thước thật. Hoàn tất nghĩa là đã nhận một tệp hợp lệ, không phải chứng nhận chất lượng hay mô hình đã dùng.

## Mở tool và kết nối tài khoản

1. Cài **Node.js 24 trở lên** từ https://nodejs.org/ và **Google Chrome hoặc Microsoft Edge** trên máy chạy tool.
2. Giải nén ZIP vào thư mục mới. Windows: chạy `start.bat`; Linux/macOS: `bash start.sh` trên máy có giao diện đồ họa. Lần đầu cần Internet đến registry.npmjs.org để cài thư viện. Trình duyệt mở khi máy chủ sẵn sàng; giữ cửa sổ máy chủ chạy.
3. Trong tool, mở **10 Tài khoản Muse → Kết nối #1**. Tool mở Muse trong một hồ sơ Chrome/Edge riêng cho slot đó.
4. Đăng nhập Muse trực tiếp trong cửa sổ vừa mở, bao gồm xác minh tài khoản nếu dịch vụ yêu cầu. Quay lại tool và bấm **Kiểm tra phiên #1**. Tool cũng kiểm tra phiên định kỳ khi hộp quản lý tài khoản đang mở.
5. Chỉ khi thấy **Đã xác minh** mới tạo thử một cảnh. Nếu thành công, bật dùng chung và chạy các ô chưa gán bằng cùng tài khoản; chỉ kết nối thêm hồ sơ khi muốn dùng nhiều tài khoản.

Đăng nhập trong cửa sổ Chrome thông thường không đăng nhập hồ sơ riêng do tool mở. Mỗi slot có hồ sơ riêng; chỉ một cửa sổ hồ sơ được mở tại một thời điểm để giảm tài nguyên. Khi đổi slot, cửa sổ cũ đóng và phiên được giữ trên đĩa. Khi tạo cảnh, tool mở đúng hồ sơ của slot và kiểm tra lại phiên trước khi gửi. Hàng đợi chỉ chạy các cảnh đang bật, có prompt và định tuyến đến phiên đã xác minh. Ô trống không cần đăng nhập thêm khi bật dùng chung. Khi tắt dùng chung, ô chưa gán chỉ dùng được hồ sơ cùng số nếu hồ sơ đó đã xác minh.

Email trong bảng là nhãn bạn đặt. Việc đăng nhập được xác minh từ phiên trình duyệt, không dựa vào email hoặc sự tồn tại của thư mục hồ sơ. Khi khởi động lại máy chủ, bấm Kết nối/Kiểm tra phiên để xác minh ít nhất một phiên đã lưu. Lựa chọn dùng chung và gán tài khoản được lưu cùng dự án, còn thông tin xác thực không nằm trong dự án.

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

## Tạo ảnh theo prompt, TXT hoặc SRT

1. Chọn tab **Tạo ảnh hàng loạt**, mức 2K hoặc 4K và khung hình.
2. Nhập prompt vào từng ô hoặc **Nhập TXT / SRT → Nạp vào Studio / Nạp & Chạy các cảnh**. Mỗi dòng/đoạn TXT hay mỗi khối SRT là một cảnh. Tối đa 10 cảnh mỗi bộ; quá 10 cảnh không bị tự cắt mất nội dung.
3. Muốn giữ nhân vật: bật **Đồng nhất nhân vật**, chọn một chân dung chung hoặc ảnh riêng ở từng ô. Muốn tạo nhân vật độc lập theo prompt: tắt tùy chọn đó.
4. Bấm tạo từng cảnh hoặc chạy cả bộ. Ảnh có thể xem lớn, tải riêng hoặc tải toàn bộ.
5. Để làm video từ bộ ảnh, bấm **Chuyển bộ ảnh đã tạo sang video**, chọn chất lượng video và chạy. Có thể dùng nút **Dùng ảnh này tạo video** cho một cảnh. Chuyển tab hoặc đổi chất lượng video giữ lại ảnh đã tạo. Ảnh đã tạo lớn hơn 8 MB được nén riêng ở bản gửi làm tham chiếu (giữ kích thước pixel); ảnh gốc vẫn được giữ để tải. Giao diện báo rõ khi nén đầu vào.

## Video, mô hình và ảnh tham chiếu

Mô hình, độ phân giải, thời lượng và khung hình trong UI được gửi cho Muse **dưới dạng yêu cầu trong prompt**, không phải tham số API được bảo đảm thi hành. Danh sách Omni/Veo lấy từ mô tả người dùng; chưa xác minh dịch vụ cung cấp đủ các lựa chọn đó. Muse quyết định khả năng thực tế. Video trả về hiển thị thời lượng và kích thước quan sát được để đối chiếu; chưa xác minh được tên mô hình thực sự đã sử dụng.

Ở video Từ ảnh, hàng đợi chỉ gửi các cảnh có ảnh đầu vào hoặc ảnh đã tạo; cảnh chưa có ảnh được bỏ qua. Ảnh là khung hình đầu và vẫn được gửi nếu tắt khóa nhân vật. Ở Từ prompt hoặc chế độ tạo ảnh, ảnh chân dung chỉ được gửi khi bật Đồng nhất nhân vật. Ảnh tham chiếu được tải qua ô đính kèm trong Muse. Nếu không tìm thấy ô tải hoặc ảnh chưa xuất hiện, tool báo lỗi trước khi gửi prompt. Yêu cầu giữ diện mạo nhân vật không chứng minh độ giống nhân vật hoặc chất lượng R2V. Hãy xem kết quả thực tế.

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

Chọn **Chẩn đoán API → Kiểm thử giao diện**. Video dùng clip 4s/360p/16:9 có nhãn `TEST CLIP - NOT AI GENERATED`; ảnh dùng PNG 640×360 có nhãn `TEST IMAGE - NOT AI GENERATED`. Chế độ này không tạo nội dung theo prompt, không dùng ảnh hoặc AI Enhance, không chứng minh phiên đăng nhập hay chất lượng AI.

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

`MUSE_BALANCE_SELECTOR` là tùy chọn nâng cao để chỉ vùng số dư có nhãn nếu Muse đổi bố cục; vùng chat không được dùng để suy đoán số dư. Token/credit chưa được dịch vụ công khai qua API của bản này. `MUSE_PROFILE_ROOT` có thể đổi nơi lưu hồ sơ. Giữ nguyên thư mục đó để tái sử dụng phiên. Cầu nối chỉ điều khiển các trình duyệt nó tự mở, không gắn vào cổng debug của Chrome cá nhân.

### Adapter API riêng (nâng cao)

Nếu đã có adapter tương thích, đặt `MUSE_TRANSPORT=adapter`, `MUSE_ADAPTER_URL` và `MUSE_ADAPTER_TOKEN` nếu cần. Không trỏ URL adapter vào trang chủ Muse.ai. Adapter chịu trách nhiệm xác thực và ánh xạ `accountId` 1–10; khi dùng adapter, các nút đăng nhập trình duyệt không xuất hiện.

Backend gọi `POST {MUSE_ADAPTER_URL}/video` với:

```json
{"accountId":1,"prompt":"scene + modifier","modelDisplayName":"Omni 1.1 Flash","aspectRatio":"16:9","durationSeconds":4,"resolution":"360p","referenceImage":{"base64":"...","mimeType":"image/png"}}
```

`referenceImage` chỉ có khi bật ảnh tham chiếu. Kết quả: `{"base64":"...","mimeType":"video/mp4"}` (hoặc WebM/QuickTime). Ảnh: `POST /image` với `accountId`, `prompt`, `aspectRatio`, `resolution` (2k/4k), `characterLock` và `referenceImage` tùy chọn; trả về base64 và MIME PNG/JPEG/WebP. Video có thêm `sourceMode` (text/image), `characterLock`; sourceMode=image cần ảnh đầu vào. Text: `POST /text` với `{"accountId":1,"prompt":"..."}` → `{"text":"..."}`. Lỗi HTTP 4xx/5xx với `{"error":"..."}`. Timeout 10 phút, phản hồi tối đa 150 MB. Token thêm dưới dạng bearer trên máy chủ, không gửi ra frontend. Đây là hợp đồng adapter của ứng dụng, không phải tài liệu API chính thức của Muse.

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

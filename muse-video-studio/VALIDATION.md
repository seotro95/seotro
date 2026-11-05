# Xác minh bản 1.4.9

## Thay đổi

Nút **Tải tất cả** tạo và tải đúng một tệp ZIP chứa bản ảnh/video đang chọn ở mỗi ô đã có kết quả. Không lặp lại mười lượt tải riêng. Chưa đủ 10 kết quả thì chỉ thêm các cảnh đã có tệp, giữ đúng số cảnh. Các nút tải riêng và tải một bản trong lịch sử giữ chức năng cũ.

Ảnh được giải mã và xuất PNG thật; video giữ nguyên byte và đuôi đúng MIME. ZIP lưu các tệp không nén lại vì media đã nén, có CRC-32 và directory theo chuẩn ZIP. CRC đọc Blob theo từng chunk; không nối toàn bộ video thành một byte array lớn. Chỉ tạo một download sau khi chuẩn bị đủ các tệp; lỗi đọc/đóng gói không phát ra một bộ tải dở. Không gọi lại API Muse khi tải.

## Kiểm thử

- `npm run build`: qua TypeScript và Vite, không thêm dependency.
- `npm run test:e2e`: **28/28 qua**. Hai ca mới tạo bộ 10 ảnh và 10 video, một lần bấm phát đúng một download. Đọc ZIP bằng `zipfile` chuẩn của Python, kiểm CRC và 10 tên tệp đúng số cảnh. So pixel cả 10 ảnh PNG với nguồn WebP và so byte cả 10 video (mỗi tệp hơn 256 KB để đọc CRC nhiều chunk). Ca tải phần đã xong xác nhận ZIP chỉ chứa cảnh 02 và 07. Các ca tải riêng, lưu lịch sử và điều khiển cũ vẫn qua.
- `tests/portable.test.mjs`: **1/1 qua** trên executable Electron Linux đóng gói, hồ sơ mới và PATH không có Node/npm. Bấm tải riêng một ảnh rồi bấm Tải tất cả một lần: đúng hai download hoàn tất trên ổ đĩa, một PNG và một ZIP. Giải nén ZIP bằng thư viện chuẩn, kiểm CRC, đủ 10 ảnh 640×360 giải mã được, nội dung 10 ảnh khác nhau. Đóng/mở lại giữ đủ 10 kết quả trong thư viện và không render thêm.
- `npm test`: qua parser/state, máy chủ adapter, lệnh mở trình duyệt và đọc số dư. Kiểm tra whitespace Git qua. Kiểm thử máy chủ chạy trong môi trường cho phép loopback.

## Phạm vi

Các ca tạo media dùng dịch vụ Muse giả lập, không xác minh thêm khả năng tạo media, quota hay số luồng của Muse thật. Windows dùng runtime Electron 45.2.2 x64 chính thức có checksum, kiểm manifest SHA-256, ZIP CRC và PE x64; cloud Linux không chạy Windows EXE. Giữ sandbox, context isolation và web security của bản phát hành.

## Kết quả lịch sử trước 1.4.9

# Xác minh bản 1.4.8

## Hành vi mới

- Tạo/Dừng riêng từng cảnh; có thể thêm cảnh khi cảnh khác đang xử lý. Hủy cảnh chờ không gửi prompt; dừng cảnh đang chạy chỉ hủy AbortController/IPC request của cảnh đó. Nút Dừng tất cả vẫn giữ chức năng.
- Lịch sử ảnh và video riêng từng ô: thumbnail/biểu tượng, prompt, thời gian, chọn xem, tải đúng bản hoặc xóa từng bản. Kết quả mới được thêm, không ghi đè các bản trước. Lưu prompt, settings và ID ảnh tham chiếu để chỉ tự khôi phục kết quả còn khớp; chọn xem ảnh cũ không làm Tạo 10 bỏ qua prompt mới. IndexedDB lưu base64/MIME và thông tin media, tạo Blob URL mới khi mở lại. Không đóng gói hồ sơ hoặc dữ liệu người dùng vào ZIP.
- Khi lưu thất bại, vẫn giữ kết quả trong phiên và ghi rõ chưa lưu trên ổ đĩa; không xóa tự động kết quả cũ. Xóa do người dùng chỉ được phản ánh sau khi transaction IndexedDB hoàn tất.
- Chọn 1/2/3/5/10 luồng. Số lớn hơn 1 cần kiểm tra New chat bằng UI hiện có, các địa chỉ hội thoại phải khác nhau, có editor và mở lại đúng địa chỉ. Kiểm tra không gửi prompt tạo nội dung. Không tìm được thì giữ 1; không tự tạo route hoặc gửi 10 prompt vào hội thoại chung.
- Các tác vụ thuê riêng địa chỉ trong pool đã kiểm tra. Redirect hoặc phát hiện hội thoại chung hạ về 1; giữ ranh giới marker/phản hồi và kiểm tra ảnh trùng của 1.4.7. Đóng phiên hủy xác minh các địa chỉ đã lưu. Không tuyên bố kiểm tra route xác nhận hạn mức render thật.

## Kiểm thử thực hiện

- `npm run test:e2e`: **25/25 qua trên bundle cuối** sau bổ sung đối chiếu prompt/settings và nạp dữ liệu legacy bằng init script trước app (tránh race với autosave). Bốn ca điều khiển/lưu mới cũng từng chạy riêng: **4/4 qua**. Gồm Tạo ô khác khi đang chạy; dừng một ô giữ ô khác; hủy cảnh chờ không gửi request; capability check không render; hai ảnh khác màu và một video giữ sau reload, chọn đúng ảnh cũ, tải PNG, xóa một bản rồi reload vẫn đúng và không render lại.
- `tests/muse-parallel.test.mjs`: **5/5 Node tests qua** (bốn kịch bản và nhóm). Thiếu New chat, nút chỉ xóa root và số luồng không hợp lệ đều không render. Fixture 10 địa chỉ chat riêng chạy đủ 10 yêu cầu trước khi trả kết quả (peak=10), dừng một chỉ gửi một Stop, chín ảnh khác nhau còn lại hoàn tất. Redirect hạ về 1 trước khi gửi prompt mới. Bao gồm API account/concurrency và từ chối thay đổi lúc đang có tác vụ.
- `npm run test:desktop`: **8/8 Node tests qua** trên Electron thật. Trong một bộ 10 yêu cầu qua IPC, dừng cảnh 3 chỉ hủy một yêu cầu và giữ chín cảnh chạy; Dừng tất cả sau đó gửi Stop tới chín cảnh còn lại. Gồm đăng nhập nhúng, ảnh, video từ ảnh, lưu phiên và popup cũ. Fixture độc lập dùng flag test, không chứng minh Muse thật hỗ trợ 10 render.
- `tests/portable.test.mjs`: **1/1 qua**, executable Linux đóng gói, hồ sơ mới, PATH không có Node/npm. Tạo đủ 10 ảnh với peak=1 trên hội thoại chung không New chat; tải riêng một và tải bộ 10, cả 11 tệp PNG giải mã được và 10 ảnh của bộ khác nhau. Sau đóng/mở lại executable: giữ origin/cổng, kịch bản và đủ 10 kết quả trong thư viện; không gửi yêu cầu render mới. Chín ảnh còn khớp được tự hiện lại, cảnh 2 đã đổi prompt vẫn giữ ảnh cũ trong lịch sử và không đánh dấu đó là kết quả của prompt mới.
- `tests/muse-serial.test.mjs`: **6/6 qua**; `npm run test:browser-bridge`: **27/27 qua** sau sửa giữ thiết lập fixture khi đóng/mở phiên. `npm test`, TypeScript/build, kiểm tra cú pháp và whitespace Git đều qua. Không thêm dependency.

## Phạm vi

Kiểm thử sử dụng Muse giả lập với Chromium/Electron thật. Chưa có tài khoản Muse thật trong môi trường cloud; chưa xác minh 10 render đồng thời, quota, model, độ nét hoặc credit của người dùng. Gói Windows dùng Electron 45.2.2 x64 chính thức, kiểm checksum runtime, manifest SHA-256 và cấu trúc EXE/ZIP; cloud Linux không chạy Windows EXE. Bản phát hành giữ sandbox, context isolation và web security; cờ no-sandbox chỉ dùng trong fixture cloud.

## Kết quả lịch sử trước 1.4.8

# Xác minh bản 1.4.7

## Lỗi được sửa

- Người dùng cung cấp `MUSE_NEW_CHAT_UNAVAILABLE` cho ảnh và video. Đây là lỗi do tool tạo ra trước khi gửi prompt, không phải phản hồi quota/capacity từ Muse. Bản cũ giả định nhiều tab là các hội thoại độc lập.
- Mặc định cầu nối Muse dùng một hàng đợi FIFO, một cảnh mỗi lượt, tái sử dụng hội thoại đã có mà không bắt buộc New chat. Giao diện chạy bộ 10 cảnh và phân biệt đang chạy/đang chờ; hủy cảnh chờ không gửi prompt.
- Chỉ nhận phản hồi giữa marker của yêu cầu và tin nhắn người dùng kế tiếp. Khi thấy luồng khác trong cùng hội thoại thì dừng nhận để tránh ghép sai, chuyển các yêu cầu sau sang một luồng và không tự gửi lại các yêu cầu đã gửi.
- So SHA-256 các pixel đã giải mã, kèm kích thước: ảnh trùng cảnh khác trong các bộ gần đây không được tính hoàn tất. Có kiểm tra khi bấm chạy lại phần lỗi bằng batch mới.
- Giải mã ảnh ở kích thước thật, chuẩn hóa ảnh không phải PNG thành PNG. PNG đã hợp lệ giữ byte gốc và MIME đúng. Ảnh WebP bị gắn `application/octet-stream` được trả bằng byte PNG thực sự. Nút tải ảnh cũng xuất PNG cho đường adapter.

## Kiểm thử của bản hiện tại

- `tests/muse-serial.test.mjs`: **6/6 Node tests qua** (5 kịch bản và một nhóm). Hội thoại chứa lịch sử, không có New chat; 10 lời gọi đồng thời được xếp hàng và trả 10 ảnh khác nhau, đỉnh render là 1. Gồm hủy cảnh chờ, ảnh trùng trong/cross-batch, WebP sai MIME và không nhận ảnh sau lượt người dùng khác.
- `npm run test:browser-bridge`: **27/27 qua** với fixture độc lập quảng bá khả năng chạy song song. Đây là kiểm thử nhánh hỗ trợ nhiều hội thoại, không chứng minh Muse thật có khả năng đó.
- `npm run test:desktop`: **8/8 Node tests qua** trên Electron thật với fixture độc lập bật riêng `MUSE_TEST_PARALLEL=1`. Đăng nhập, 10 ảnh/video, Stop, phiên lưu và popup đều qua. Flag chỉ có tác dụng với fixture loopback, không bật cho Muse thật.
- `npm run test:e2e`: **21/21 qua**, gồm một cảnh chạy/chín cảnh chờ, định danh batch/scene, chế độ adapter/demo, import và các chức năng cũ. Ca WebP export chạy lại sau khi thêm đối chiếu pixel: **1/1 qua**, ảnh tải là PNG, kích thước 2×2 và các pixel khớp preview.
- `tests/portable.test.mjs`: **1/1 qua** trên executable đóng gói Linux, hồ sơ mới và PATH không có Node/npm. Muse giả lập có hội thoại chung, không New chat, xuất WebP. App tạo đủ 10 ảnh với đỉnh render là 1; tải riêng một ảnh và tải bộ 10 ảnh. Cả **11 tệp trên ổ đĩa** hoàn tất, có chữ ký PNG, giải mã thành công 640×360; 10 tệp của bộ có nội dung khác nhau. Đóng/mở lại giữ kịch bản và cổng.
- `npm test` và parser/core chạy lại đều qua; `npm run build`, kiểm tra cú pháp và whitespace Git qua. Gói phát hành vẫn bật sandbox; cờ no-sandbox chỉ dùng cho fixture cloud.

## Phạm vi xác minh

Windows dùng runtime Electron 45.2.2 x64 chính thức, đối chiếu checksum và cấu trúc PE; gói có app, bundle UI và Playwright Core. Không cần bản cũ, npm hay Node ngoài. Cloud Linux không chạy Windows EXE. Các kiểm thử dùng Muse giả lập và không có phiên Muse thật; số credit, chất lượng, quyền model và tốc độ thật phải xác minh trên tài khoản người dùng. Bản này không cam kết 10 render Muse đồng thời.

## Kết quả lịch sử trước 1.4.7

## Kết quả của bản hiện tại

- Người dùng xác nhận gửi/nhận tin nhắn thủ công được trong tab Muse của tool. Log vẫn có một ô prehydration đang hiện. Bản này hỗ trợ textarea đang hoạt động dù còn nhãn đó và trường hợp chuyển sang rich editor sau ký tự đầu.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge`: **27/27 Node tests qua** (26 kịch bản và một nhóm). Có ca textarea giữ nhãn cũ, emoji, chuyển editor sau nhập đầu, bản nháp, dữ liệu tham chiếu, media mới và 10 yêu cầu đồng thời. Ô inert không tạo kết quả giả và chỉ nhận đúng một Enter; tool báo chưa có xác nhận.
- `DISPLAY=:97 MUSE_ELECTRON_TEST_NO_SANDBOX=1 npm run test:desktop`: **8/8 Node tests qua** (7 kịch bản và một nhóm), với cả 10 luồng chỉ tạo rich editor sau input đầu tiên. Kiểm tra Message không render; 10 ảnh khác nhau, 10 video từ ảnh, Stop, lưu phiên và đăng nhập popup đều qua. Cờ tắt sandbox chỉ dùng trong fixture cloud.
- `tests/portable.test.mjs`: **1/1 qua** với executable đóng gói Linux, hồ sơ tạm mới, `PATH` không có Node/npm, `NODE_PATH` rỗng và không cấu hình PORT. Xác nhận `app.isPackaged=true`, phiên bản 1.4.6, cổng tự chọn và giữ ổn định, đăng nhập mới và tạo một ảnh qua ô Message giữ nhãn prehydration. Sau đóng/mở lại, kịch bản ở cảnh 2 vẫn giữ nguyên trên cùng origin.
- `npm test`: parser/state 7 ca, máy chủ 7 ca trong một nhóm, lệnh mở trình duyệt 3 ca, phân tích số dư 2 ca đều qua.
- `npm run build`, kiểm tra cú pháp Node/Python và whitespace Git đã qua. Cảnh báo `use client` của thư viện icon không ngăn build.
- Chromium có thể thêm dòng trống khi đọc `innerText` sau `fill`; đã đo trực tiếp. So sánh nội dung chuẩn hóa phần dòng trống hiển thị nhưng vẫn nhập văn bản gốc. Chưa đủ prompt hoặc nội dung đổi ngoài yêu cầu thì không Enter. Sau Enter chưa có xác nhận thì không tự gửi lại.

## Gói đầy đủ

- Runtime Windows x64 Electron 45.2.2 tải từ release chính thức và kiểm tra SHA-256 theo manifest của npm package đã khóa. App đã build, Playwright Core và giấy phép được sao chép vào `resources/app`; không cần npm install trên máy người dùng.
- `scripts/package_portable.py` tạo gói Windows/Linux, kiểm tra đường dẫn khi giải nén runtime và CRC của ZIP. `BUILD-MANIFEST.json` ghi phiên bản và SHA-256 từng tệp app.
- Không đưa `.data`, `.env`, phiên đăng nhập hoặc node_modules từ hồ sơ người dùng vào gói. Bản Windows tạo dữ liệu mới khi chạy và hiện phiên bản trong thanh ứng dụng.
- Cloud Linux không thực thi được Windows EXE. Kiểm thử executable độc lập dùng Linux và cùng bố cục app/dependency. Chưa tự động tạo nội dung trên Muse thật; tài khoản, model, hạn mức đồng thời và độ nét thực tế vẫn do dịch vụ quyết định.

## Các kết quả lịch sử trước 1.4.6

## Kích hoạt Message trong bản 1.4.5

- Log người dùng: `ready=complete`, `visibility=visible`, viewport 1280×900, `composerRoots=1`, `prehydration=1`, `visibleEditors=1` tại `https://muse.ai/`.
- Thêm fixture để ô prehydration hiện, editor rich text ẩn và chỉ khởi tạo khi ô Message được focus. Các chỉ số DOM giống log; bản 1.4.4 thất bại đúng `MUSE_COMPOSER_NOT_READY`, trong khi các ca cũ vẫn qua.
- Sửa bằng focus trực tiếp vào ô prehydration duy nhất đang hiện trong khung Muse, click bình thường nếu còn hiện; không fill hoặc Enter ở đó. Editor thật vẫn phải qua bộ chọn trước khi gửi prompt. Không thay mô hình, độ phân giải, xác thực hoặc giới hạn 10 luồng.
- Native còn phát hiện click-only không ổn định trong iframe của view nền: ô prehydration hiện, bộ đếm focus=0, chưa render. Phép đo riêng sau khi thêm focus: focus=1, editor thật hiện và fixture nhận đúng một yêu cầu. Không dùng force click hoặc giả sự kiện DOM.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge`: **24/24 Node tests qua** (23 kịch bản trong một nhóm), gồm giữ nguyên bản nháp prehydration, không gửi khi kích hoạt thất bại, textarea ẩn trước editor thật và 10 ảnh đồng thời.
- `DISPLAY=:97 MUSE_ELECTRON_TEST_NO_SANDBOX=1 npm run test:desktop`: **8/8 Node tests qua** (7 kịch bản trong một nhóm). Cả 10 luồng đều dùng Message cần focus để khởi tạo trong iframe: mỗi luồng focus đúng một lần, không có sự kiện nhập hoặc giá trị ở ô prehydration. Kiểm tra Message không render, 10 ảnh riêng, 10 video từ ảnh, Stop và khôi phục phiên đều qua. Cờ tắt sandbox chỉ dùng cho fixture cloud, không dùng trong launcher phát hành.
- `npm run build` bản 1.4.5, kiểm tra cú pháp Node và whitespace Git đã qua. Giao diện không thay đổi trong bản này; kết quả E2E 1.4.4 được giữ bên dưới làm kết quả nền, không ghi là đã chạy lại.

## Kết quả nền đã xác minh trên Linux

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

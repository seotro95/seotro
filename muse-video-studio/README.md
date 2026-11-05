# Muse AI Studio 1.6.0 · Hai chế độ, 10 cảnh

Có bản Windows x64 đóng gói đầy đủ và bản mã nguồn. Trang đăng nhập Muse nằm trong cửa sổ tool. Chọn một tài khoản dùng chung 10 ô hoặc 10 tài khoản tách biệt, mỗi tài khoản một ô. Mỗi ô có nút Tạo/Dừng riêng và lịch sử ảnh/video lưu trên máy. Có thể kiểm tra để bật tối đa 10 hội thoại song song.

## Bản Windows đầy đủ — không cần bản cũ

1. Giải nén **toàn bộ** ZIP Windows vào một thư mục mới, không chạy trong cửa sổ xem ZIP.
2. Mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Runtime Electron/Node và thư viện đã có trong gói; không cần cài Node.js, npm hay Chrome riêng.
3. Đăng nhập Muse trong tab tích hợp, quay **← Về Studio**, bấm **Kiểm tra phiên**.
4. Có thể bấm **Kiểm tra ô Message** trước khi tạo. Bước này tìm ô nhập trong trang luồng, không gửi prompt hoặc render.
5. Nhập 10 prompt hoặc TXT/SRT, chọn **Tạo ảnh hàng loạt** / **Tạo video**, bấm **TẠO 10 ẢNH / VIDEO**.

Không chép `.data`, `.env`, `node_modules` hoặc các tệp từ bản cũ. Gói tạo hồ sơ mới trong `resources/app/.data/muse-desktop`. Cần Internet và tài khoản Muse có quyền tạo nội dung tương ứng. Phiên bản **1.6.0** hiện trên thanh ứng dụng và tiêu đề cửa sổ. Bản đóng gói chọn cổng cục bộ trống lần đầu và giữ cổng đó khi mở lại để duy trì kịch bản đã lưu.

Cầu nối giao diện **không chính thức**. Kiểm thử dùng Chromium/Electron thật và dịch vụ giả lập cục bộ; chưa tự động tạo media hoặc đọc số dư trên Muse.ai thật. Người dùng xác nhận có thể gửi/nhận tin nhắn thủ công trong tab Muse của tool. Tài khoản thật có thể giới hạn render đồng thời, từ chối đăng nhập nhúng hoặc thay đổi giao diện. Các lựa chọn model, độ nét và thời lượng là yêu cầu bằng prompt, cần xác nhận bằng kết quả thật.

## Mới: 10 tài khoản, mỗi tài khoản một luồng

1. Bấm **Quản lý 10 tài khoản**. Dán danh sách email/tên quản lý, mỗi dòng một tài khoản, hoặc **Nhập TXT** rồi **Lưu danh sách** (tối đa 10).
2. Bấm **Đăng nhập** ở từng hàng Muse 01–10, hoàn tất email/OTP trên trang Muse trong tool, quay **Về Studio** và kiểm tra phiên. Nhập danh sách chỉ đặt nhãn, không tự xác thực; không nhập mật khẩu, mã OTP, cookie hoặc token vào danh sách.
3. Chọn **Chế độ tài khoản → 10 tài khoản · mỗi tài khoản 1 luồng**. Ô 01 dùng Muse 01, ô 02 dùng Muse 02… Các ô chưa xác minh có thông báo riêng và không tự mượn tài khoản khác.
4. Bấm **TẠO 10 ẢNH / VIDEO**. Tối đa 10 tác vụ đồng thời, mỗi tài khoản một tác vụ. Không cần kiểm tra New chat cho chế độ này. Khi mở lại, bấm **Kiểm tra 10 phiên** để đọc lại các phiên đã lưu.
5. Chuyển về **1 tài khoản · tối đa 10 luồng** để dùng tính năng cũ: mọi ô dùng Muse 01 và giữ lựa chọn số hội thoại song song riêng. Chỉ đổi chế độ khi các tác vụ Muse đã kết thúc.

Mỗi tài khoản có cookie, bộ nhớ trang, cửa sổ đăng nhập và luồng xử lý riêng. Nhãn/email trong danh sách không đổi danh tính phiên đã đăng nhập; muốn dùng tài khoản khác, đăng xuất/đăng nhập trực tiếp trong hàng tương ứng. Tool không kiểm chứng danh tính thật chỉ dựa vào nhãn.

Chế độ nhiều tài khoản có thể giảm việc chờ chung một tài khoản, nhưng thời gian tạo còn phụ thuộc Muse và quyền của từng tài khoản. Không tự chuyển tài khoản khi lỗi/hết hạn mức và không tự gửi lại yêu cầu. Chỉ dùng các tài khoản bạn có quyền sử dụng.

## Lưu thư mục, đa nhiệm và xem ảnh trong bản 1.6.0

- **Tải tất cả** lưu các bản đang chọn trực tiếp vào một **thư mục thường** trên máy. Lần đầu chọn thư mục gốc; các lần sau tự nhớ trên bản desktop. Mỗi bộ có thư mục mới chứa PNG/MP4/WebM/MOV đã đánh số, mở bằng File Explorer, không cần giải nén kết quả. Nút **Thư mục lưu** đổi nơi lưu. Nút tải riêng từng ảnh/video vẫn còn.
- Số thứ tự tăng liên tục cho tải riêng và lưu bộ; tên vẫn có số cảnh và mã bản cài. Ghi bằng chế độ tạo mới, không ghi đè; trùng thư mục thì tạo tên khác. Lỗi ghi giữ các tệp đã lưu, không xóa bộ cũ. Bản web dùng File System Access nếu trình duyệt hỗ trợ; nếu không, dùng executable desktop để lưu thư mục.
- Trong lúc tạo có thể đổi tab ảnh/video, chỉnh prompt/thiết lập, nhập TXT/SRT, chọn ảnh, xem/tải kết quả đã có và thêm tác vụ vào ô trống. **Mỗi tác vụ giữ prompt, ảnh và thiết lập tại lúc bấm Tạo**. Thay đổi sau đó áp dụng cho lượt mới; kết quả của prompt cũ vẫn nằm trong lịch sử, không gán nhầm cho prompt mới.
- AI Enhance dùng cùng hàng đợi, thực hiện được ở ô khác. Một ô có một tác vụ; mỗi tác vụ có Dừng riêng. Giới hạn tổng 10 tác vụ đồng thời, Muse còn tuân theo số luồng kết nối đã kiểm tra. Chỉ các thao tác thay đổi phiên/kết nối và render chẩn đoán bị khóa khi xung đột với yêu cầu đang chạy.
- Bấm ảnh mở cửa sổ xem **ngay trong Studio**, có Vừa cửa sổ/Kích thước gốc và tải ảnh. Không mở popup Blob vốn có thể hiện trắng.
- Chọn **Số luồng: 10** trước khi chạy để kiểm tra và bật mười hội thoại riêng. Tiến độ mới ghi số ô đang mở và số prompt đã hiển thị trên trang Muse, tách khỏi lúc kết quả hoàn tất. Trong chế độ một tài khoản, mười yêu cầu được gửi đồng thời khi kết nối có khả năng đó; Muse vẫn có thể xếp hàng render theo tài khoản. Đây không phải cam kết mười GPU/render thật đồng thời.

## Đăng nhập bằng mã xác nhận email trong bản 1.6.0

1. Mở **Đăng nhập Muse trong tool**, nhập email và yêu cầu mã.
2. Giữ trang Muse đang chờ mã. Nhập hoặc dán **mã mới nhất** vào chính ô mã xác nhận trên trang Muse, rồi bấm xác nhận.
3. Sau khi trang Muse hoàn tất đăng nhập, bấm **← Về Studio → Kiểm tra phiên**. Trạng thái chờ mã không được dùng để chạy tạo nội dung.

Tool tạm dừng kiểm tra phiên ngầm khi tab Muse đang mở. Nếu còn thấy ô `one-time-code`/OTP, kể cả sau đổi tab, tool giữ trạng thái **Đang chờ mã xác nhận** và không gửi thêm auth-check POST. Không đọc, lưu, điền thay hoặc gửi lại mã; challenge và phản hồi xác minh vẫn do trang Muse xử lý. Xin mã mới có thể làm mã cũ không còn dùng được.

Nếu nhập mã mới vẫn quay lại ô email, bấm **Chẩn đoán** trên thanh trên cùng rồi **Sao chép chẩn đoán**. Báo cáo chỉ gồm phiên bản, trạng thái đã xác minh và các phản hồi HTTP/lỗi mạng gần đây của bước đăng nhập. Không chứa email, OTP, mật khẩu, query, fragment, cookie hoặc nội dung request/response; các đoạn đường dẫn không công khai được che. Chẩn đoán thụ động, không gửi thêm yêu cầu xác thực và không gọi render. Có thể dùng báo cáo này để kiểm tra lỗi dịch vụ thực tế.

Kiểm thử mô phỏng đã xác nhận giữ được challenge, đổi tab, gõ/dán mã và xác minh cookie HTTP-only. Chưa có phiên Muse thật để khẳng định nguyên nhân mọi vòng lặp đăng nhập hoặc xác nhận tài khoản của người dùng.

## Đăng nhập bằng liên kết email (khi Muse gửi liên kết)

Bản này sửa trường hợp cửa sổ đăng nhập được mở trống (`about:blank`) rồi mới chuyển sang trang xác thực. Cửa sổ phụ vẫn chỉ dùng phiên Muse của tool, giữ sandbox và không có quyền Studio/Node.js. Trang đăng nhập hiện ngay khi mở, có nút **Tải lại Muse** để mở lại trang chính mà không xóa cookie, ảnh/video hay bộ đếm.

Nếu Muse gửi **liên kết đăng nhập**:

1. Trong tab Muse của tool, nhập email và yêu cầu một email đăng nhập mới.
2. Trong email, sao chép địa chỉ liên kết đăng nhập. Không cần mở nó bằng trình duyệt khác.
3. Trên thanh trên cùng của tool, bấm **Liên kết email**, dán liên kết vào cửa sổ trên máy rồi bấm **Mở trong tool**.
4. Hoàn tất bước xác minh Muse yêu cầu, bấm **← Về Studio** và **Kiểm tra phiên**. Chỉ bật tạo nội dung sau khi xác minh phiên thành công.

Liên kết có thể chỉ dùng một lần hoặc có thời hạn. Nếu đã mở ở trình duyệt khác hoặc báo hết hạn, yêu cầu email mới rồi làm lại. Nếu Muse gửi **mã xác nhận** hoặc yêu cầu mật khẩu, nhập trực tiếp trên trang Muse trong tool; không dán mã/mật khẩu vào ô Liên kết email.

Cửa sổ liên kết chỉ nhận HTTPS của Muse.ai hoặc miền phụ của Muse.ai. Địa chỉ được che trong ô nhập, xóa khỏi ô khi gửi và không ghi vào log/Studio API. Không gửi liên kết, mã xác nhận hoặc mật khẩu vào chat. Không chuyển cookie/token giữa Chrome và tool và không giả trạng thái đăng nhập. Kiểm thử dùng dịch vụ mô phỏng; thay đổi này không xác nhận mọi phương thức đăng nhập trên Muse thật đã hoạt động.

## Tự đánh số liên tục, tránh trùng tệp

Mỗi ảnh/video tải xuống có một số mới dùng chung giữa tải riêng, tải trong lịch sử và lưu bộ vào thư mục. Bộ đầu nhận 000001–000010, bộ sau nhận 000011–000020; tải một bản riêng tiếp theo nhận 000021. Số tiếp tục qua 001000 và lớn hơn, không quay lại 01 theo số ô và không cắt số khi dài hơn sáu chữ số.

Ví dụ tên `image-000001-scene-01-<mã-bản-cài>.png`, `video-001001-scene-03-<mã-bản-cài>.mp4`. Phần `scene-01` vẫn chỉ đúng ô của bạn; số đứng trước đó là số tải liên tục. Thư mục cũng ghi dải số đã cấp và cùng mã bản cài, nên tải lại cùng bộ vẫn có tên thư mục và tên tệp bên trong mới.

Bộ đếm lưu trên máy trong IndexedDB của cùng hồ sơ Studio, giữ khi đóng/mở lại. Transaction read/write cấp cả dải số một lần, tránh hai tab lấy trùng số. Dùng số nguyên BigInt lưu dưới dạng chuỗi, không mất chính xác ở số lớn. Mã ngẫu nhiên của hồ sơ phân biệt thư mục cài mới hoặc hồ sơ đã xóa dữ liệu; chúng bắt đầu bộ đếm riêng nhưng tránh dùng lại tên của bản cài khác. Nếu hủy tải, số đã cấp không được dùng lại.

Không cần nhập số hay bấm xác nhận thêm. Nút Tải tất cả lưu một bộ vào thư mục thường; thông báo hiện dải số của lượt vừa tải. Đổi tên không gọi lại Muse hoặc sửa nội dung tệp.

## Tạo/Dừng từng ô, lưu kết quả và chọn số luồng

- Mỗi ô có **Tạo cảnh này / Tạo lại cảnh**. Có thể thêm cảnh khi các cảnh khác đang xử lý; không thêm trùng cảnh đang chạy hoặc đang chờ.
- Khi chạy, nút của ô đổi thành **Dừng cảnh này**; khi chờ, nút là **Hủy cảnh chờ**. Chỉ hủy yêu cầu của ô đó, các ô khác tiếp tục. Nút Dừng tất cả vẫn giữ chức năng dừng cả bộ. Lệnh đã gửi tới Muse có thể vẫn tính phí dù đã yêu cầu dừng.
- Mỗi kết quả thành công được thêm vào **Kết quả đã lưu** trong đúng ô. Giữ cả các bản ảnh và video trước, có thời gian và prompt để phân biệt. Bấm thumbnail để xem, **Tải** để tải đúng bản, **Xóa** để xóa từng kết quả.
- Kết quả lưu trong IndexedDB của Studio, trên máy và trong hồ sơ của ứng dụng. Đóng/mở lại cùng bản cài và thư mục dữ liệu vẫn giữ. JSON chỉ xuất kịch bản/settings, không chứa thư viện media. Xóa dữ liệu ứng dụng, hồ sơ hoặc thư mục cài portable cũng xóa kho kết quả; chuyển sang thư mục cài mới không tự nhập kho của bản cũ.
- Khi không đủ dung lượng hoặc không ghi được IndexedDB, kết quả vẫn hiện trong phiên với nhãn **Chưa lưu trên ổ đĩa · hãy tải ngay**. Không tự xóa ảnh/video cũ để lấy chỗ.
- Chọn **Số luồng: 1 / 2 / 3 / 5 / 10** trên bảng tài khoản. Với số lớn hơn 1, tool mở New chat bằng nút có thật của Muse, yêu cầu địa chỉ hội thoại khác nhau và mở lại được. Kiểm tra không gửi prompt tạo nội dung. Không tìm được các địa chỉ riêng thì giữ 1 và báo lý do, không gửi 10 prompt vào cùng hội thoại.
- Các tác vụ song song dùng những địa chỉ đã kiểm tra, mỗi lượt giữ riêng một địa chỉ; không tự tạo đường dẫn Muse giả. Đổi route hoặc phát hiện prompt xen kẽ thì hạ xuống một luồng. Kiểm tra địa chỉ không chứng minh hạn mức render của tài khoản: Muse vẫn có thể giới hạn hoặc từ chối. Không tự lặp lại yêu cầu đã gửi và không bảo đảm 10 render thực sự đồng thời.

## Hội thoại chung, hàng đợi và ảnh tải xuống

Log `MUSE_NEW_CHAT_UNAVAILABLE` do tool tạo ra trước khi gửi prompt. Nó không chứng minh Muse từ chối tạo ảnh/video hoặc tài khoản hết hạn mức. Cầu nối đăng nhập hiện dùng một hàng đợi trên cùng tài khoản, mặc định một cảnh mỗi lượt, và có thể nối tiếp hội thoại hiện tại mà không yêu cầu New chat. Bấm Tạo 10 vẫn xử lý đủ các cảnh hợp lệ; giao diện phân biệt cảnh đang chạy với cảnh đang chờ. Dừng bộ cũng hủy các cảnh chưa được gửi.

Phản hồi chỉ được đọc sau marker của đúng yêu cầu và trước tin nhắn người dùng kế tiếp. Khi phát hiện các yêu cầu xen kẽ, tool dừng nhận kết quả thay vì ghép ảnh của cảnh khác. Ảnh được so dấu vân tay pixel với các cảnh đã nhận gần đây; ảnh trùng cảnh khác bị báo lỗi, không tính là hoàn tất và không tự gửi lại.

Ảnh được giải mã ở kích thước thật, WebP/JPEG/AVIF được chuẩn hóa thành PNG khi cần. Nút tải ảnh luôn xuất tệp PNG thực sự, gồm cả ảnh từ adapter; không chỉ đổi đuôi tệp. Không phóng ảnh để giả độ nét. Nếu tệp không giải mã được thì báo lỗi, không xuất dữ liệu hỏng.

Một tài khoản Muse vẫn có thể có giới hạn dịch vụ thực tế. Kiểm tra route chỉ xác minh các địa chỉ hội thoại riêng mở được, không chứng minh tài khoản được phép render 10 tác vụ cùng lúc. Adapter API có các yêu cầu độc lập vẫn có thể xử lý song song theo cấu hình kết nối.

Bản này cũng giữ sửa nhập Message: textarea hoạt động dù còn nhãn prehydration, chuyển editor sau ký tự đầu, giữ đủ prompt và chỉ nhấn gửi một lần. Rich editor hiển thị được ưu tiên; bản nháp ngoài yêu cầu được giữ nguyên.

## Chạy bản mã nguồn

Cần Node.js 24+. Giải nén mã nguồn vào thư mục mới, chạy `start.bat` trên Windows hoặc `bash start.sh` trên Linux/macOS có desktop. Lần đầu tải npm packages và runtime Electron chính thức, có kiểm tra checksum. PowerShell có thể dùng `npm.cmd` mà không đổi execution policy.

```sh
npm ci
npm run build
npm start
```

Máy chủ mã nguồn mặc định chỉ lắng nghe 127.0.0.1:8788. Bản desktop đóng gói chọn và giữ cổng cục bộ. Đóng cửa sổ để dừng app; kết quả đã lưu sẽ có lại khi mở cùng hồ sơ. Dự án JSON lưu kịch bản và thiết lập.

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
- Tải từng kết quả hoặc một thư mục cho cả bộ bằng một lần bấm, xem ảnh lớn, phát video thật, mở/xuất dự án JSON, AI Enhance và modifier chung.
- Bảng số dư đọc token/credit có nhãn từ giao diện Muse, gồm số 0 thực sự. Không đọc được thì ghi rõ; không đoán hoặc tự tính. Có thời điểm đọc và nút cập nhật.

Mô hình, thời lượng, khung hình và độ phân giải là **yêu cầu bằng lời trong prompt**, không phải tham số API được Muse xác nhận. Danh sách Omni/Veo theo mô tả người dùng, chưa xác minh trên dịch vụ thật. Tool hiển thị kích thước quan sát được; tệp thấp hơn mức yêu cầu được ghi **Chưa đạt yêu cầu**, không phóng ảnh hoặc đổi nhãn để giả 4K gốc. Độ giống nhân vật và chất lượng AI cần kiểm tra bằng kết quả thực tế.

Chỉnh prompt/ảnh/settings bỏ kết quả đang chọn khỏi ô để tránh coi tệp cũ là kết quả của prompt mới; các bản đã tạo vẫn còn trong Kết quả đã lưu để xem/tải. Khi mở lại, chỉ tự chọn kết quả còn khớp prompt, settings và ảnh tham chiếu. Chọn xem lại một bản cũ không làm Tạo 10 bỏ qua prompt mới. IndexedDB lưu media; dự án JSON và localStorage lưu prompt, bật/tắt và settings.

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

Nếu đã có adapter tương thích, dùng `MUSE_TRANSPORT=adapter`, `MUSE_ADAPTER_URL`, `MUSE_ADAPTER_TOKEN` nếu cần. Chế độ adapter giữ hợp đồng cũ với **một** tài khoản, accountId=1; chế độ 10 tài khoản dùng phiên Muse tích hợp/trình duyệt. Không trỏ URL adapter vào trang chủ Muse.ai. Adapter cũng có thể nhận 10 yêu cầu đồng thời và phải tuân thủ hạn mức của nhà cung cấp. Đây là hợp đồng của ứng dụng, không phải API chính thức của Muse:

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
CHROMIUM_PATH=/usr/bin/chromium node tests/muse-parallel.test.mjs
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
npm run test:desktop
node tests/multi-account.test.mjs
# Sau khi chuẩn bị gói Linux, đặt MUSE_PORTABLE_EXECUTABLE rồi chạy:
node tests/portable.test.mjs
```

Test desktop cần màn hình/virtual display và runtime Electron (lần đầu: `node node_modules/electron/install.js`). Trên Linux cloud có thể dùng Xorg dummy/Xvfb. Môi trường kiểm thử không hỗ trợ sandbox có thể bật **riêng cho fixture** `MUSE_ELECTRON_TEST_NO_SANDBOX=1`; launcher phát hành không dùng cờ này.

Fixture độc lập quảng bá khả năng chạy song song để kiểm tra nhánh đó; đây không phải bằng chứng Muse thật có 10 hội thoại riêng. Kiểm thử serial dùng lịch sử chung, không có New chat, xác minh đủ 10 ảnh qua hàng đợi. Kiểm thử gói độc lập chọn 10 luồng qua giao diện, xác minh 10 yêu cầu chồng lấp trong mười đường dẫn riêng trước khi nhận kết quả, xem ảnh ngay trong Studio, lưu thư mục thật và giữ dữ liệu/số thứ tự sau mở lại. Test desktop còn kiểm tra video từ ảnh và hủy từng cảnh/cả bộ. Test không gửi yêu cầu đến Muse thật. Xem `VALIDATION.md`. Runtime Windows được kiểm tra checksum và cấu trúc gói; cloud Linux không chạy được Windows EXE. Bản đóng gói Linux cùng bố cục được kiểm thử với hồ sơ mới.

**Chẩn đoán API → Kiểm thử giao diện** dùng clip/ảnh 640×360 có nhãn TEST CLIP/TEST IMAGE, không tạo nội dung AI và không chứng minh đăng nhập/hạn mức/chất lượng.

Nguồn: [Electron](https://github.com/electron/electron), [muse-mcp (không chính thức)](https://github.com/degokisss/muse-mcp), [Muse Gadget SDK](https://github.com/facebookincubator/muse-gadget-sdk). Cầu nối tự triển khai, không chạy mã community hoặc dùng SDK gadget để giả API tạo video.

Mỗi cloud task đã có môi trường riêng; dùng checkout hiện có, không tạo Git worktree cho setup. Snapshot không giữ tiến trình ứng dụng đang chạy.

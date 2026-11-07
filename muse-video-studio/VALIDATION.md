# Xác minh bản 1.8.0

## Kết quả thay đổi

- Giới hạn thống nhất 40 trong `limits.mjs`: giao diện, bộ điều phối, tài khoản, bridge HTTP/IPC, API/MCP, nhập kịch bản, bộ đếm tải và ghi thư mục. Chọn Số luồng 20/30/40 hiện đúng số ô, đánh số liên tục; nút Tạo, progress và Tải tất cả theo số ô. Số ô có thể đổi riêng để chạy kịch bản dài với ít luồng hơn.
- Giữ tối đa 40 bản nháp trong state/lưu dự án; thu nhỏ chỉ ẩn ô, không bỏ prompt/kết quả/lịch sử. Hỗ trợ đọc dự án v1 cũ 10 cảnh, mở lại bố cục đã chọn và tự mở thêm ô khi API/import có ID cao hơn.
- Lựa chọn số luồng không bị trả về 1 khi Muse không có hội thoại riêng. Giữ yêu cầu và số ô, hiển thị số thực tế/cảnh báo, chạy hàng đợi bằng số luồng đã xác minh. Không giả 30/40 render khi chỉ có một hội thoại chung; lỗi đăng nhập/kết nối vẫn chặn gửi. Có nút Kiểm tra luồng để thử lại.
- Kiểm tra hội thoại song song dùng tối đa bốn trang tạm mỗi lượt; từng URL do dịch vụ tạo vẫn được mở lại/xác minh, không dùng hai bản sao root làm hội thoại riêng. Đóng các trang tạm sau mỗi kiểm tra; chỉ giữ các worker cần khi tạo.
- Phát hành mã nguồn ứng dụng theo MIT. Thêm MCP Streamable HTTP tại `/mcp` trên cùng cổng API/Bearer key. Chín công cụ đọc trạng thái, đổi bố cục, sửa ô, tạo bộ/chạy ô đã nhập, dừng, đọc thư viện, lưu kết quả và xóa thư viện có xác nhận. Có CODEX-MCP.toml, MCP-CODEX.md và nút sao chép cấu hình không chứa khóa. Không cấp quyền shell/JavaScript/tệp tùy ý hoặc đọc cookie/OTP.
- MCP/API dùng chung idempotency cho tạo/chạy; MCP khai báo rõ công cụ chỉ đọc và công cụ xóa. Lệnh lưu dùng đúng exporter/thư mục đã chọn và bộ đếm của giao diện, có thể lọc batchId/output/sceneIds. API chỉ báo sẵn sàng sau khi thư viện và cấu hình đã tải, sửa trường hợp 409 ngay sau reload dù phiên Muse vẫn còn.

## Kiểm thử

- TypeScript/Vite build và `npm test` qua. Unit kiểm 40 yêu cầu trên server, chỉ giải phóng một chỗ khi một yêu cầu xong; 40 tài khoản độc lập mỗi tài khoản một lease; từ chối ID/count 41; nhập API 40 prompt/ID ô 40; lưu bản nháp ẩn; ghi đủ 40 tệp với số cảnh 20/30/40; giữ lựa chọn 30 và hàng đợi 1 khi private chat không hỗ trợ, không fallback khi hết phiên đăng nhập.
- Giao diện Playwright **42/42 qua**. Chọn 20/30/40 hiện đủ ô, giảm/tăng giữ prompt, reload giữ bố cục, quản lý đúng 40 tài khoản; nhập/tạo/xuất 40 ảnh và 40 video với số tải 1–80 liên tục. Mẫu cấu hình Codex trỏ đúng cổng và không chứa khóa. Giữ các ca đa nhiệm, ảnh tham chiếu, lịch sử/xóa thư viện và viewport cũ.
- Cầu nối Chromium **27/27**, hội thoại song song **5/5**, hàng đợi chung **6/6 qua**. Ca admission cũ được cập nhật đúng giới hạn 40: nhận 40 job, chạy 10 worker theo cấu hình test, từ chối job 41, giải phóng rồi nhận đủ 40 kết quả riêng. Không giữ giới hạn 10 giả trong test khiến chờ vô hạn.
- Electron từ nguồn **8/8**, OTP **4/4**, email/popup **4/4 qua** cho tương thích cũ. Các ca mới high-capacity từ nguồn và gói độc lập đều qua: xác minh 40 route, đóng trang kiểm tra, gửi **40 yêu cầu ảnh chồng lấp trước bất kỳ kết quả nào**, byte ảnh khớp đúng ô 20/30/40.
- Kiểm thử MCP trên executable Linux độc lập, PATH không có Node/npm: initialize, đọc trạng thái, đổi bố cục; `studio_create_batch` tạo **30 yêu cầu video chồng lấp**, tải byte MP4 đúng fixture; `studio_save_results` ghi đủ 30 tệp thật vào thư mục, tên đến scene-30, byte khớp. Sửa/chạy riêng ô 40 bằng MCP qua cùng các hàm giao diện. Bật thiếu New chat vẫn nhận bộ 20 ô và chạy ba prompt theo hàng đợi 1, không mất prompt ô 40 khi mở lại bố cục.
- Unit HTTP/MCP kiểm Bearer/Origin, initialize/protocol negotiation, notifications 202, tools/list/call, unknown method/tool, schema, idempotency, destructive annotation, xác nhận xóa, media MIME/bytes, lưu/bật/tắt/đổi khóa và không đổi khóa hoạt động khi ghi thất bại.
- Gói độc lập còn qua các ca tương thích 10 phiên riêng tạo ảnh/video, một phiên chọn 10 route và lưu thư mục/giữ số thứ tự, API tạo/dừng/xóa/reload/đổi khóa. Trên mã cuối, ca API sau reload qua lại; dữ liệu rỗng trong thư viện không còn bị hiểu là kết nối đã tải xong.

## Khả năng thao tác thay người dùng

Môi trường cloud của phiên này không có capability Desktop và không có công cụ cua_repl/open_in_codex; Companion snapshot không có trang. Thử HTTPS Muse.ai qua proxy được cấu hình trả HTTP 403 ở CONNECT; không bypass hoặc lấy cookie của người dùng. Không có kết nối tới cổng localhost trên máy Windows của người dùng, nên **chưa tạo/tải video Muse thật từ tài khoản của người dùng** trong phiên chat này.

Các ca tạo nội dung/xác thực bên trên là dịch vụ mô phỏng cục bộ, không phải Muse thật. Chứng minh được số worker, phân ô, tệp MP4 giải mã được và kết nối MCP/HTTP hoạt động, không chứng minh Muse cho một tài khoản chạy 40 render hoặc đảm bảo tốc độ/nội dung/chất lượng thật. Codex trên cùng máy có thể dùng bộ MCP sau khi người dùng bật API, đặt biến khóa và thêm cấu hình; mã nguồn mở không tự đăng ký công cụ vào chat cloud hiện tại.

Gói Windows dùng Electron 45.2.2 x64 chính thức, kiểm checksum, PE x64, manifest SHA-256 và CRC ZIP. Cloud Linux chạy gói Linux cùng mã; không chạy Windows EXE. Giữ sandbox, context isolation, web security; không thêm dependency.

## Kết quả lịch sử trước 1.8.0

# Xác minh bản 1.7.0

## Thay đổi

- Thêm cổng HTTP độc lập, người dùng bật/tắt/đổi cổng/đổi khóa ngay trong Studio. Chỉ bind `127.0.0.1`, Bearer key sinh ngẫu nhiên, không nhận Origin/cross-site hoặc Host ngoài loopback. Cấu hình/khóa lưu trong dữ liệu riêng, không ghi log hoặc đóng gói. API gửi bộ prompt/TXT/SRT/ảnh tham chiếu, đọc trạng thái, tải media bằng byte gốc đúng MIME, dừng từng ô/cả bộ và xóa thư viện có chuỗi xác nhận.
- Lệnh đi qua IPC chỉ nhận từ Studio; trang Muse không có preload này. Phản hồi có status/error rõ ràng qua đối tượng IPC, giữ đúng 400/409 khi đầu vào không hợp lệ/Studio bận. Không nhận mã JavaScript, đường dẫn tệp tùy ý hoặc đăng nhập Muse qua cổng API.
- POST bộ có Idempotency-Key: cùng khóa/nội dung trả lại cùng batchId, không chạy thêm; khác nội dung bị từ chối. Giữ tối đa 128 mục trong RAM, không hứa lưu qua khởi động lại. Media mới giữ batchId để công cụ bên ngoài đối chiếu đúng bộ.
- Nút Xóa toàn bộ dùng một transaction clear trong IndexedDB, chỉ thay giao diện/revoke URL sau commit. Giữ nguyên prompt, tài khoản, ảnh tham chiếu và bộ đếm tải; không xóa tệp đã xuất ra thư mục ngoài. Từ chối khi đang tạo/tải, có xác nhận trên giao diện và chuỗi xác nhận riêng trên API.
- Một tài khoản mặc định yêu cầu 2 luồng: trước khi chạy lần đầu, tự kiểm tra hai đường dẫn hội thoại độc lập rồi mới gửi prompt. Nếu kiểm tra không được, trả lỗi trước khi gửi. Không mở hai bản sao cùng hội thoại và gọi là hai luồng. Giữ lựa chọn 1/2/3/5/10 trên máy; chế độ 10 tài khoản vẫn một luồng mỗi tài khoản.

## Kiểm thử đã qua

- `npm run build`, TypeScript/Vite và `npm test` qua. Test API thật trên loopback kiểm Bearer, Origin, loopback bind, URL không chứa khóa, idempotency khi hai client gửi chồng lấp, media bytes/MIME, xác nhận xóa, đổi khóa thu hồi khóa cũ, lưu cấu hình bật/tắt qua tạo lại server và JSON không phải object bị từ chối. Test đầu vào kiểm TXT/SRT, giới hạn 10 prompt, ID ô, whitelist settings, nguồn ảnh/video. Test pool kiểm lưu lựa chọn một luồng khi mặc định mới là hai.
- Playwright giao diện **38/38 qua** trên build hiện tại. Thêm xóa cả ảnh/video sau xác nhận, hủy xóa giữ dữ liệu, lỗi transaction giữ kết quả và lịch sử, reload giữ thư viện rỗng. Kiểm hai yêu cầu chồng lấp và tám ô chờ; khi không có hội thoại thứ hai thì không gửi bất kỳ prompt nào. Các ca đa nhiệm, xem ảnh, lịch sử, thư mục và 10 tài khoản cũ đều qua.
- Electron desktop từ nguồn **8/8**, OTP **4/4**, liên kết email/popup **4/4 qua**. Giữ khả năng mười hội thoại trên một tài khoản khi người dùng đã chọn/kiểm tra mười, video từ ảnh, dừng từng ô/cả bộ và đăng nhập không xen auth-check vào challenge OTP.
- Kiểm thử HTTP → Electron → Studio → fixture Muse **1/1 qua**: bật cổng từ giao diện, không dùng cờ ép song song, mặc định 2; 4 prompt chạy theo hai đợt hai yêu cầu trước khi có kết quả. Gửi lại cùng Idempotency-Key không tạo trùng, tải byte ảnh khớp cảnh, đang chạy thì xóa trả 409. Xóa sau xác nhận giữ tệp ngoài và số tải tiếp 000002, reload giữ thư viện rỗng, dừng từng ô/cả bộ bằng HTTP, khởi động lại giữ cổng/khóa, đổi khóa thu hồi khóa cũ và tắt cổng ngừng nhận kết nối.

- Gói Linux độc lập **3/3 kịch bản qua**, hồ sơ mới, PATH không có Node/npm: (1) API thật qua Electron trên mã cuối kiểm hai luồng, idempotency, batchId trên media, tải byte đúng, xóa/reload/bộ đếm và lưu/đổi/tắt khóa/cổng; (2) 10 phiên riêng chạy 10 ảnh rồi 10 video đồng thời, chuyển về một tài khoản khi người dùng chọn một luồng, khởi động lại giữ phiên; (3) một tài khoản chọn mười hội thoại, xem ảnh không popup trắng, lưu thư mục thật, giữ thư viện/số thứ tự và lựa chọn mười luồng sau mở lại. Unit API còn kiểm lỗi ghi khóa không làm thay đổi khóa đang hoạt động.

## Giới hạn xác minh

Các ca tạo nội dung/xác thực dùng dịch vụ mô phỏng cục bộ, không phải tài khoản Muse thật của người dùng. Đã chứng minh hai yêu cầu đồng thời trên hai hội thoại riêng; chưa chứng minh tài khoản thật của người dùng có hai hội thoại hoặc Muse xử lý render nhanh hơn bao nhiêu. Khi Muse không hỗ trợ thì báo lỗi, không giả kết quả hoặc tự gửi lại.

Windows dùng Electron 45.2.2 x64 chính thức. Cloud Linux kiểm PE x64, checksum, manifest và CRC của gói Windows; không chạy Windows EXE. Sandbox, context isolation và web security giữ nguyên. Cổng tự động chỉ có trong bản desktop và dành cho công cụ trên cùng máy tính như người dùng đã chọn.

## Kết quả lịch sử trước 1.7.0

# Xác minh bản 1.6.0

## Hai chế độ tài khoản

- Thêm `MuseAccounts`: mười driver Muse độc lập, mỗi driver có hồ sơ/partition cookie và trang đăng nhập riêng. Muse 01 giữ đúng partition `persist:muse` và đường dẫn dữ liệu cũ. Muse 02–10 dùng các partition riêng; popup đăng nhập kế thừa đúng partition của tài khoản mở nó.
- Chế độ `multiple` gán ô N → tài khoản N, máy chủ giới hạn một tác vụ trên mỗi tài khoản; AI Enhance dùng cùng giới hạn. Không tự mượn tài khoản khác hoặc chuyển tài khoản khi lỗi/hết hạn mức. Mỗi yêu cầu giữ accountId/chế độ tại thời điểm bấm tạo. Chế độ `single` vẫn dùng tài khoản 01, giữ nguyên kiểm tra hội thoại riêng và tùy chọn tối đa 10 luồng cũ.
- Quản lý 10 tài khoản: dán/nhập TXT email hoặc tên quản lý, trạng thái và số dư từng tài khoản, đăng nhập/kiểm tra từng phiên và Kiểm tra 10 phiên sau mở lại. Danh sách chỉ đặt nhãn, không xác thực hay đổi danh tính phiên. Không thu thập mật khẩu, OTP, cookie hoặc token trong form danh sách.
- Chọn tài khoản trên bảng chính đồng bộ với tab Muse, liên kết email và chẩn đoán đăng nhập. Không thay đổi chế độ/phiên khi đang xử lý Muse. Các tính năng đa nhiệm, xem ảnh nội bộ, lịch sử, thư mục media và đánh số tiếp của 1.5.0 được giữ.

## Kiểm thử đã hoàn tất

- `npm run build`, `npm test` qua; không thêm dependency. Test pool xác nhận mười tài khoản nhận mười yêu cầu chồng lấp, từ chối yêu cầu thứ hai trên tài khoản bận, hủy một tài khoản giữ chín tài khoản khác, giải phóng lease và vẫn cho phép mười yêu cầu ở chế độ một tài khoản. Nhãn được lưu/đọc lại; tên trùng hoặc nội dung dạng email|password bị từ chối.
- Giao diện Playwright **34/34 qua**. Test mới nhập TXT đủ 10 nhãn, chỉ gửi tới 9 ô có phiên xác minh, đúng accountId=sceneId, báo tài khoản còn thiếu, khóa chuyển chế độ trong khi tác vụ đang chạy và giữ tùy chọn chế độ cũ sau reload. Tất cả ca xem ảnh, lịch sử/tải, đa nhiệm và lỗi từ 1.5.0 qua lại.
- Desktop từ nguồn **8/8 qua** cho chế độ một tài khoản: mười ảnh và mười video từ ảnh chồng lấp, dừng từng ô/cả bộ, giữ phiên và popup đăng nhập. Test mới nhiều tài khoản **1/1 qua**: mười cookie jar không kế thừa cookie của tài khoản trước, mười yêu cầu ảnh chồng lấp ở cùng route mà không cần New chat; byte ảnh khớp đúng tài khoản/cảnh. Chuyển chế độ cũ gửi video của ô 02 qua tài khoản 01. Khởi động lại và kiểm tra mười phiên giữ nhãn/cookie, không tạo thêm nội dung. Test nguồn cố định lại cổng local đã chọn để kiểm tra lưu thiết lập; bản đóng gói tự ghi nhớ cổng.
- Gói Linux độc lập **2/2 kịch bản qua**, PATH không có Node/npm, hồ sơ mới. Kịch bản mới đăng nhập mười phiên riêng, nhận đồng thời mười ảnh rồi mười video, không cần New chat, kiểm đúng cookie/byte media, chuyển lại chế độ một tài khoản và khởi động lại giữ đủ mười phiên/nhãn/chế độ. Kịch bản cũ chọn mười hội thoại trên một tài khoản, kiểm đủ mười yêu cầu chồng lấp, xem ảnh không popup trắng, lưu thư mục thật đủ mười PNG khác nhau, giữ thư mục/bộ đếm/lịch sử sau mở lại.
- Kiểm thử OTP **4/4** và liên kết email/popup **4/4 qua**: giữ challenge, chỉ mã mới nhất được chấp nhận, không xen auth-check khi đang nhập OTP và không đưa mã/email/cookie vào báo cáo chẩn đoán.

## Giới hạn xác minh

Các ca xác thực và tạo nội dung dùng dịch vụ mô phỏng cục bộ, không phải tài khoản Muse thật của người dùng. Kiểm thử chứng minh các phiên/cookie tách biệt và tool có thể gửi đồng thời mười yêu cầu; chưa xác minh Muse cho mười tài khoản thật xử lý nhanh hơn bao nhiêu. Muse vẫn quyết định quyền tạo nội dung, hạn mức, chất lượng và tốc độ của từng tài khoản.

Windows dùng Electron 45.2.2 x64 chính thức. Cloud Linux kiểm cấu trúc PE x64, checksum, manifest và CRC của gói Windows; không chạy Windows EXE. Sandbox, context isolation và web security được giữ nguyên.

## Kết quả lịch sử trước 1.6.0

# Xác minh bản 1.5.0

## Kết quả thay đổi

- **Tải tất cả** ghi PNG/video trực tiếp vào thư mục thường thay cho ZIP media. Chọn thư mục gốc lần đầu, desktop nhớ lựa chọn sau khi khởi động lại; mỗi lượt tạo thư mục bộ mới, mở bằng File Explorer. Nút Thư mục lưu đổi nơi lưu. Cả tải riêng và lưu bộ dùng chung bộ đếm liên tục, không ghi đè tệp cũ.
- **Đa nhiệm**: đổi tab ảnh/video, sửa prompt/thiết lập, nhập TXT/SRT, chọn ảnh/kết quả lịch sử, xem/tải media và thêm tác vụ ở ô trống trong lúc tạo. AI Enhance ở ô khác dùng cùng bộ điều phối. Mỗi tác vụ giữ bản chụp prompt/ảnh/thiết lập; kết quả luôn lưu lịch sử, chỉ tự chọn nếu còn khớp đầu vào hiện tại. Một ô có một tác vụ và nút Dừng riêng.
- **Xem ảnh** trong dialog của Studio, có vừa cửa sổ/kích thước gốc/tải ảnh và Esc. Không dùng popup Blob vốn có thể hiện trắng trong Electron.
- **Tiến độ Muse** ghi nhận số luồng đang mở và số prompt đã xuất hiện trong đúng hội thoại. Không nhận việc chọn 10 trong danh sách là bằng chứng đã gửi đủ 10 hoặc Muse đang render đồng thời.

## Kiểm thử

- `npm run build` và `npm test` qua. Thêm 2 ca ghi thư mục thật: nhớ nơi lưu, tạo thư mục khác khi trùng, từ chối đường dẫn tùy ý/tệp trùng, không ghi đè và xử lý hủy chọn thư mục.
- Giao diện Playwright: **33/33 qua**. Xác nhận ảnh lớn giải mã được, đổi kích thước/đóng bằng Esc/tải trong trình xem, không mở popup. Giữ yêu cầu ảnh/video trong lúc đổi tab/chất lượng, nhập kịch bản mới, chọn lịch sử và lưu thư mục; yêu cầu ban đầu vẫn giữ dữ liệu đã chụp. AI Enhance ở ô khác chạy cùng yêu cầu video. Kiểm tra lưu các byte ảnh/video, bộ đếm qua reload, lịch sử và các lỗi cũ.
- Cầu nối trình duyệt: **27/27 qua**; hàng đợi chung **6/6 qua**; chế độ hội thoại song song **5/5 qua**. Mười prompt được ghi nhận trước khi fixture trả bất kỳ kết quả nào, mười đường dẫn hội thoại khác nhau; hủy một cảnh không dừng chín cảnh khác. Tiến độ không chứa prompt hoặc URL.
- Desktop Electron từ nguồn: **8/8 qua**. Mười yêu cầu ảnh và mười yêu cầu video từ ảnh thực sự chồng lấp trước khi nhận kết quả; kết quả riêng đúng từng cảnh, dừng riêng/cả bộ, giữ phiên khi khởi động lại, đăng nhập popup và kiểm tra ô Message.
- Gói Linux độc lập: **1/1 qua**, hồ sơ mới, PATH không có Node/npm. Đăng nhập OTP fixture; chọn 10 qua giao diện và kiểm tra các đường dẫn riêng thật, không ép cờ song song. Đủ 10 yêu cầu hoạt động/chờ kết quả trước khi trả ảnh, 10 ảnh khác nhau. Đổi tab/chất lượng trong khi chạy, xem ảnh lớn không có cửa sổ mới. Lưu thư mục thật chứa 10 PNG giải mã được; không phát download ZIP. Khởi động lại giữ 10 bản lịch sử và thư mục gốc, tiếp tục đánh số 001011 rồi lưu bộ 9 ảnh vào thư mục mới; bộ cũ còn nguyên.
- Đăng nhập email/OTP: **4/4 + 4/4 qua**, gồm giữ challenge khi đổi tab, chỉ mã mới nhất được chấp nhận, cookie HTTP-only, liên kết email và popup trống. Không gửi yêu cầu tạo nội dung khi kiểm tra đăng nhập.
- Kiểm thử desktop được chạy riêng từng bộ. Khi chạy đồng thời nhiều bộ Electron/Chromium trong cloud, có lượt timeout; chạy tách riêng qua đầy đủ. Bước kiểm tra 10 hội thoại cần hơn 30 giây trên fixture có ô Message ban đầu, nên test gói chờ tối đa 90 giây cho bước này; không sửa hoặc bỏ qua kiểm tra hội thoại riêng trong sản phẩm.

## Giới hạn xác minh

Các ca tạo nội dung/xác thực là dịch vụ mô phỏng cục bộ, không phải tài khoản Muse thật. Đã chứng minh tool gửi 10 yêu cầu đồng thời khi có mười hội thoại riêng, chưa chứng minh Muse thật cho tài khoản người dùng chạy mười render cùng lúc. Không tăng hạn mức, tạo hội thoại giả, nhận ảnh cũ làm kết quả mới hoặc gửi lại tự động. Nếu Muse xếp hàng xử lý, tool vẫn phải chờ dịch vụ trả kết quả.

Windows dùng Electron 45.2.2 x64 chính thức, kiểm checksum, manifest SHA-256, ZIP CRC và PE x64. Cloud Linux không chạy Windows EXE; gói Linux cùng mã/bố cục đã được chạy thật. Sandbox, context isolation và web security giữ nguyên trong bản phát hành; không thêm dependency.

## Kết quả lịch sử trước 1.5.0

# Xác minh bản 1.4.12

## Phạm vi sửa theo thông tin mới

Người dùng xác nhận nhận mã OTP qua email và bị quay lại ô email sau nhập mã. Luồng này khác liên kết email ở 1.4.11. Kiểm thử OTP thông thường trên mã cũ qua 3/3; chưa có phản hồi HTTP từ Muse thật để kết luận nguyên nhân dịch vụ.

Mã cũ vẫn gửi auth-check POST từ kiểm tra trạng thái trong lúc challenge đang mở. Fixture phát hiện một POST sau đổi tab; khi mô phỏng dịch vụ làm đổi cookie pending ở anonymous check, kiểm thử giữ/nhập mã thất bại. Bản này tạm ngừng kiểm tra nền khi view Muse đang mở; khi còn trường OTP/one-time-code nhìn thấy, cả kiểm tra trực tiếp cũng giữ trạng thái awaiting_code, không gửi thêm POST. Sau trang xác nhận xong và quay về Studio mới xác minh lại. Không đọc giá trị, lưu hoặc tự điền/gửi OTP.

Thêm Chẩn đoán đăng nhập trên thanh trên. Bộ ghi thụ động chỉ giữ 24 sự kiện trong RAM: giờ, method đã giới hạn, route công khai hoặc [ẩn], status/lỗi mạng được lọc và boolean có Set-Cookie. Không đọc body, referrer hoặc giá trị header; bỏ query/fragment và che subdomain. Snapshot không có email, mã, cookie/token. Sao chép chỉ xảy ra khi người dùng bấm nút trong dialog; không gửi báo cáo ra ngoài và không tạo auth/render request.

## Kiểm thử

- `tests/otp.test.mjs`: **4/4 qua** sau sửa, với fixture từ chối challenge bị auth-check can thiệp. Đổi Studio/Muse giữ form và challenge, số auth-check khi đang pending bằng 0; chẩn đoán không phát thêm POST hoặc chứa email/mã/challenge; mã cũ bị từ chối, mã mới gõ/dán được, cookie HTTP-only xác minh thành công. Fixture dùng mã giả, không gửi email thật.
- `tests/login-diagnostics.test.mjs`: **3/3 qua** và đưa vào `npm test`. Header cookie/body là getter cố ý ném lỗi nếu bị đọc; recorder chỉ đọc metadata cho phép. Kiểm loại query/email/mã/fragment/path riêng, che subdomain, bỏ service khác, giới hạn 24 sự kiện và whitelist lỗi mạng.
- `npm run test:e2e`: **30/30 qua**, gồm awaiting_code không bật render, đầy đủ tải ZIP/số thứ tự/lịch sử và các chức năng cũ.
- `tests/login.test.mjs`: **4/4 qua**; `npm run test:desktop`: **8/8 qua**; `npm run test:browser-bridge`: **27/27 qua**. Fixture popup đóng sau 50 ms để tránh đóng target trước khi nhận xong sự kiện click; không sửa sản phẩm để làm chậm popup.
- `tests/portable.test.mjs`: **1/1 qua** trên executable Linux đóng gói, hồ sơ mới và PATH không có Node/npm. Đăng nhập bằng OTP thật trong trang fixture, không can thiệp challenge; tạo đủ 10 ảnh qua hàng đợi; ZIP CRC và ảnh giải mã được; mở lại giữ phiên/thư viện và bộ đếm tải tiếp 1011.
- `npm test`, TypeScript/Vite/build và whitespace Git qua. Không thêm dependency. Sandbox, context isolation và web security vẫn bật ở bản phát hành.

## Giới hạn xác minh

Tất cả ca xác thực trên là dịch vụ mô phỏng, không phải tài khoản Muse thật của người dùng. Việc anonymous auth-check làm mất challenge là chế độ fixture để bảo vệ luồng OTP, chưa được xác nhận là nguyên nhân tại Muse. Nếu vẫn quay lại email, cần báo cáo chẩn đoán đã lọc để biết HTTP/service error thực tế. Không giả xác minh hoặc vượt quy định nhà cung cấp. Windows dùng Electron 45.2.2 x64 chính thức, kiểm checksum, manifest SHA-256, ZIP CRC và PE x64; cloud Linux không chạy Windows EXE.

## Kết quả lịch sử trước 1.4.12

# Xác minh bản 1.4.11

## Phát hiện và sửa

Người dùng báo trang Muse mở nhưng đăng nhập lỗi/quay lại màn hình đăng nhập, chọn phương thức email hoặc liên kết email. Chưa có dòng lỗi từ dịch vụ thật nên không kết luận mọi vòng lặp đăng nhập đều do tool.

Tái hiện riêng trên mã 1.4.10: fixture mở `about:blank` rồi chuyển đến trang xác thực; Electron chặn cửa sổ, test thất bại với `Popup blocked`. Bản này cho phép cửa sổ trống theo luồng trình duyệt bình thường, vẫn dùng partition Muse có sandbox/context isolation/web security, không cấp preload Studio hoặc Node. Không đổi user agent hay vượt quy định xác thực của nhà cung cấp.

Thêm **Liên kết email**: người dùng yêu cầu email mới trên trang Muse, sao chép link và mở trong đúng phiên của tool. Form là cửa sổ cục bộ có IPC hẹp, che/xóa nội dung ô nhập, chỉ nhận Muse.ai/miền phụ qua HTTPS (fixture chỉ cùng origin loopback). Không gửi link qua Studio HTTP API, không ghi log URL hoặc query. HTTP lỗi hoặc link đã dùng báo cần kiểm tra/yêu cầu email mới; không giả trạng thái xác minh. Mã xác nhận/mật khẩu vẫn nhập trên trang Muse.

Trang đăng nhập được hiện trước khi tải xong; nút **Tải lại Muse** mở lại trang chính, giữ cookie và dữ liệu. Không xóa phiên, ảnh/video, lịch sử hoặc bộ đếm tải.

## Kiểm thử

- `tests/login.test.mjs`: **4/4 Node tests qua** (ba trường hợp và nhóm) sau khi baseline trước sửa thất bại. Kiểm popup trống/chuyển hướng, popup không có require/Studio/email IPC; link email dùng đúng cookie pending trong phiên Muse; từ chối miền khác, xóa ô nhập, không đưa giá trị nhạy cảm vào thông báo; callback đã dùng bị báo lỗi và không xác minh; link hợp lệ xác minh được; Tải lại giữ phiên, vẫn chặn file URL và không gửi yêu cầu tạo nội dung.
- `npm run test:desktop`: **8/8 qua** trên Electron thật, gồm đăng nhập nhúng, popup trực tiếp, kiểm tra Message, 10 ảnh/video fixture, dừng riêng và lưu phiên. `npm run test:browser-bridge`: **27/27 qua**; `tests/muse-serial.test.mjs`: **6/6 qua**. Không thay điều kiện xác minh tài khoản thành phỏng đoán từ editor/cookie profile.
- `tests/portable.test.mjs`: **1/1 qua**, executable đóng gói Linux, hồ sơ mới, PATH không có Node/npm. Đăng nhập mới bằng form Liên kết email đóng gói và cookie pending cùng phiên, tạo đủ 10 ảnh qua hàng đợi, tải ZIP có CRC và 10 ảnh giải mã được. Mở lại giữ phiên, thư viện, kịch bản và tải tiếp số 1011 mà không ghi đè.
- `npm test`, build TypeScript/Vite, kiểm cú pháp và whitespace Git qua. Không thêm dependency. Các cờ no-sandbox chỉ dùng ở fixture cloud, không ghi vào bản phát hành.

## Phạm vi

Các kiểm thử dùng Muse giả lập với Electron/Chromium thật. Chưa có phiên Muse thật để xác minh tài khoản người dùng hoặc lỗi dịch vụ cụ thể. Liên kết đã dùng/hết hạn phải yêu cầu mới; liên kết email qua miền ngoài Muse chưa được chấp nhận tự động. Không cam kết mọi cách xác thực hoạt động hoặc 10 render đồng thời. Windows dùng runtime Electron 45.2.2 x64 chính thức, đối chiếu checksum, manifest SHA-256 và CRC/PE x64; cloud Linux không chạy Windows EXE.

## Kết quả lịch sử trước 1.4.11

# Xác minh bản 1.4.10

## Thay đổi

Mỗi tệp tải riêng hoặc bên trong ZIP nhận một số tải mới dùng chung cho ảnh, video và lịch sử. Không đặt lại theo ô 01–10. Nút tải bộ vẫn phát một download ZIP, tên ZIP ghi dải số; thông báo ghi số đầu–cuối. Tên tệp vẫn giữ số cảnh. Mã 128 bit riêng của hồ sơ giúp phân biệt thư mục cài mới hoặc hồ sơ đã xóa dữ liệu.

Bộ đếm IndexedDB cấp dải số bằng một transaction read/write, chỉ trả dải sau khi commit. Các tab dùng chung bộ đếm; đóng/mở app giữ số. Dùng BigInt và chuỗi thập phân nên không cắt ở 1.000, không mất chính xác trên Number.MAX_SAFE_INTEGER. Lỗi đọc/ghi hoặc dữ liệu không hợp lệ không tự reset về 1; số đã cấp không tái sử dụng nếu hủy tải.

## Kiểm thử

- `npm run build`: TypeScript/Vite qua, không thêm dependency.
- `npm run test:e2e`: **29/29 qua**. Hai tab tải ảnh và video đồng thời với counter fixture 999 nhận đúng 1000 và 1001, không trùng. Counter fixture 9007199254740991 nhận đúng 9007199254740992 rồi 9007199254740993. Với từng loại ảnh/video, tải cùng bộ ba lần (có reload trước lần ba) nhận lần lượt 1–10, 11–20, 21–30: ba tên ZIP và 30 tên media khác nhau, namespace giữ nguyên. ZIP được kiểm CRC bằng zipfile chuẩn của Python; ảnh so pixel và video so byte như bản trước. Tải các ô 02/07 giữ đúng số cảnh với hai số tải mới.
- `tests/portable.test.mjs`: **1/1 qua** trên executable Electron Linux đóng gói, hồ sơ mới, PATH không có Node/npm. Counter fixture đặt 999: tải riêng nhận 1000, ZIP nhận 1001–1010. Không thêm tiền tố chống trùng từ test harness: lưu bằng tên thật của app. Sau đóng/mở executable, tải riêng nhận 1011; cả ba tệp trên ổ đĩa còn nguyên, không ghi đè. Gồm kiểm CRC và giải mã đủ 10 PNG 640×360 khác nhau; giữ thư viện/kịch bản và không gọi render thêm khi mở/tải lại.
- `npm test` và whitespace Git qua. Không thay đổi kết nối hay quyền tạo media của Muse.

## Phạm vi

Kiểm thử tạo nội dung dùng dịch vụ Muse giả lập. Gói Windows dùng Electron 45.2.2 x64 chính thức và kiểm checksum runtime, SHA-256 từng tệp app, CRC của ZIP và PE x64. Cloud Linux không thực thi Windows EXE. Giữ sandbox, context isolation và web security của bản phát hành. Bộ đếm thuộc cùng hồ sơ; cài vào thư mục/hồ sơ mới có bộ đếm và mã riêng.

## Kết quả lịch sử trước 1.4.10

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

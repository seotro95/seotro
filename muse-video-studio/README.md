# Muse AI Studio 1.13.6

Ứng dụng Windows tạo ảnh/video qua các tài khoản Muse riêng, nhập TXT/SRT và lưu kết quả trên máy. Xem [cách dùng bản mới](CAP-NHAT-1.13.6.md).

## Sửa kết nối nội bộ và báo lỗi

Lệnh tạo ảnh/video của bản desktop dùng kết nối HTTP riêng tới Studio trên máy, không đi qua global fetch/proxy hoặc thời hạn chờ header mặc định của fetch. Mã lỗi phân biệt mất kết nối, hết thời gian và phản hồi không hợp lệ. Mỗi ô có **Sao chép lỗi** và **Tải lỗi TXT**. Bản sửa cũng nhận được xác nhận gửi khi tin nhắn bị thu gọn và tiếp tục nhận kết quả khi Muse ẩn dòng người dùng cũ.

## Tên ảnh/video theo TXT/SRT

Tool nhận tên ở mục lớn `[1] TÊN`, `[2]TÊN`, `[ 3 ] TÊN`… (có hoặc không có dấu cách) hoặc `1. TÊN CẢNH` có prompt bên dưới. Hồ sơ nhân vật có `PROMPT CHAN DUNG` và `PROMPT TOAN THAN` được tách hai prompt; tên tệp lấy tên mục lớn kèm loại ảnh. Phần mô tả giọng nói và ghi chú không thành tác vụ tạo ảnh.

Có thể ghi trực tiếp trong TXT hoặc từng cue SRT:

```text
Tên video: Cảnh mở đầu.mp4
Prompt: Toàn cảnh ngôi đền lúc bình minh, máy quay tiến chậm.
```

Cũng nhận `Tên ảnh`, `Tên tệp`, `Name`, `Filename`, `Title`. Tên được tách khỏi prompt gửi Muse, hiển thị ở **Tên tệp ảnh/video** trong từng ô và có thể sửa mà không tạo lại kết quả. Tên trong dự án và kết quả thư viện được lưu khi mở lại.

Không có tên: `1.png`, `2.png`, `3.mp4`… Bộ đếm dùng chung ảnh/video, tiếp tục qua các lần tải và khởi động lại. Tệp có tên không tiêu thụ số tự động. Tên trùng trong cùng bộ thêm `(2)`, `(3)`; ký tự không hợp lệ trên Windows đổi thành `_`. Ảnh xuất PNG, video giữ đúng đuôi định dạng trả về. Mỗi lượt tải cả bộ tạo thư mục riêng.

## Tài khoản và ô chạy song song

Chọn **Một tài khoản** hoặc **Nhiều tài khoản**, số tài khoản 1–40 và số ô mỗi tài khoản 1–10. Nút **10 tài khoản × 6 ô** bố trí 60 ô. Có checkbox chọn các tài khoản cụ thể và lựa chọn tài khoản trong từng ô. Ô dùng chung tài khoản cùng dùng proxy của tài khoản đó.

Mỗi tài khoản có bộ đếm và giới hạn riêng. Bộ xếp hàng cùng backend cho phép sáu tác vụ đồng thời trên một tài khoản khi sáu hội thoại riêng đã được xác minh; không còn khóa một luồng ở chế độ nhiều tài khoản. Một ô kết thúc nhường lượt cho ô chờ; hủy một ô giữ các ô khác. Tối đa bố cục 400 ô (40 × 10).

Có thể chọn số ô riêng cho từng tài khoản trong bảng chọn: ví dụ Muse 01 chạy 2 ô, Muse 02 chạy 6 ô, Muse 03 chạy 10 ô. Tổng ô bằng tổng lựa chọn từng tài khoản. Đổi ô mặc định cho cả nhóm hoặc bấm preset 10 × 6 sẽ áp dụng lại đồng đều; số ô riêng được lưu khi mở lại.

**Muse quyết định hạn mức và credit thực tế.** Số ô cấu hình là yêu cầu, không tạo thêm quyền trên dịch vụ. Khi Muse không có New chat, tool gửi liên tiếp trong cùng cuộc trò chuyện và chờ kết quả đồng thời (tối đa 6 yêu cầu trong chế độ này). Nếu không dùng được các cách chạy song song hoặc lỗi ở ô chưa gửi, tool tự chuyển tài khoản đó sang một luồng, giữ toàn bộ ô chờ theo thứ tự. Chế độ một luồng dùng lại trang Muse đã đăng nhập. Prompt đã gửi nhưng kết quả chưa rõ sẽ không tự gửi lại; khi Muse báo rõ từ chối vì giới hạn đồng thời, tool thử lại một lần ở chế độ tuần tự. Với sáu ô, cả sáu trang New chat được giữ mở, nhập đủ prompt rồi mới gửi cùng lượt. Trang nháp chưa có URL cố định, đường dẫn dạng # và composer trong iframe đều được giữ đúng ngữ cảnh. Tool không tự gửi lại prompt đã được nhận.

TXT/SRT được nạp theo thứ tự vào các ô đang hiện. Kịch bản vượt số ô được chọn không tự cắt bỏ. Thu gọn/ẩn ô giữ dữ liệu; mở lại hoặc xuất/nhập dự án giữ tên, prompt, thiết lập và tài khoản. Bố cục cũ tới 40 ô vẫn được giữ; số luồng cũ lớn hơn 10 được đưa về tối đa 10 mỗi tài khoản và phần còn lại chờ.

## Proxy và IP

Trong **Quản lý tài khoản**, bật/lưu proxy riêng rồi bấm **Kiểm tra IP**. Mỗi tài khoản có ô IP, thời điểm kiểm tra và lỗi riêng. IP là địa chỉ ra Internet đo qua chính session/proxy của hồ sơ, có thể khác host của proxy. Không dùng IP trực tiếp làm kết quả thay thế khi proxy lỗi. Đổi/tắt proxy hoặc khởi động lại cần kiểm tra mới.

Proxy hỗ trợ HTTP/HTTPS có đăng nhập và SOCKS5 không mật khẩu. Thông tin proxy được mã hóa trên máy; bảng trạng thái không trả mật khẩu. Phép đo IP không gửi cookie phiên Muse. Các tài khoản có hồ sơ Chromium và bộ nhớ phiên tách biệt; nhãn email không tự xác thực hay thay danh tính tài khoản.

## Dùng bản Windows đầy đủ

1. Giải nén toàn bộ ZIP vào thư mục mới. Mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**; không chạy trong cửa sổ xem ZIP. Không cần cài Node.js, npm hoặc Chrome riêng.
2. Bấm **Đăng nhập Muse trong tool**, đăng nhập từng tài khoản cần dùng, quay **← Về Studio**, bấm **Kiểm tra phiên**.
3. Chọn số tài khoản và ô/tài khoản; nhập TXT/SRT, xem các tên nhận được và chọn ảnh/video.
4. Bấm Tạo cho toàn bộ hoặc từng ô. Có Tạo/Dừng riêng, AI Enhance, ảnh tham chiếu, đồng bộ thiết lập theo lựa chọn và thư viện kết quả.
5. Chọn **Thư mục lưu** rồi **Tải tất cả**, hoặc tải riêng từng kết quả.

Dữ liệu Windows mới ở `%LOCALAPPDATA%\Muse AI Studio`, không phụ thuộc thư mục giải nén EXE. Giữ thư mục này khi đổi phiên bản. Có **Lưu tất cả tài khoản**, trạng thái và thời điểm lưu từng hồ sơ. Nếu bản cũ lưu dữ liệu cạnh EXE, đóng bản cũ rồi dùng **Chuyển dữ liệu bản cũ**, chọn thư mục có EXE cũ; xem [hướng dẫn dữ liệu](BAN-DAY-DU-1.10.md). Muse có thể làm hết hạn phiên và yêu cầu đăng nhập lại.

Giữ các chức năng của 1.12.2: **Tải lại Studio**, chẩn đoán nguyên nhân/mã thoát/bước khởi động và **Khôi phục Studio**. Có `MO_STUDIO_KHONG_GPU.bat` và `MO_STUDIO_KHOI_PHUC.bat`; chế độ khôi phục giữ tài khoản/kịch bản và chưa tải thư viện cũ, không xóa tệp. Xem [khôi phục 1.12.2](RECOVERY-1.12.2.md).

## Phát triển, API và kiểm tra

Cần Node 24 trở lên. Chạy tại thư mục này:

```sh
npm ci
npm run build
npm test
npx playwright install chromium
npm run test:e2e -- tests/browser/names-concurrency-ip.spec.ts
npm run test:parallel-six
npm run test:proxy-desktop
npm run test:startup
npm run test:desktop
python scripts/package_portable.py --platform win32 --output PATH_TO_ARTIFACTS
```

Kiểm thử dùng fixture cục bộ: sáu video qua cầu nối trình duyệt, 60 ô qua giao diện, hai proxy xác thực qua Electron, tên TXT/SRT, bộ đếm qua reload, hủy riêng, phiên lưu và khôi phục renderer. Không dùng credit hoặc chứng nhận giới hạn tài khoản Muse thật. Workflow Windows kiểm tra cả gói EXE sau đóng gói; release nháp chỉ được tạo khi các bước bắt buộc đạt.

`npm start` mở desktop; `npm run start:web` mở máy chủ cục bộ. Có adapter HTTP riêng qua cấu hình `.env.example`; kiểm thử giao diện trả clip mẫu có nhãn và không tạo nội dung AI. Cầu nối Muse không chính thức, có thể cần điều chỉnh khi dịch vụ thay giao diện.

API/MCP cục bộ: [API-AUTOMATION.md](API-AUTOMATION.md), [MCP-CODEX.md](MCP-CODEX.md), [CODEX-MCP.toml](CODEX-MCP.toml). Chỉ bật khi cần điều khiển tool từ bên ngoài; khóa API được giữ trên máy. API nhập script cũng giữ tên và thứ tự ô. Giới hạn mới: 1–400 scene/tệp và 1–10 luồng yêu cầu mỗi tài khoản; tài khoản vẫn trong 1–40.

Giấy phép MIT; xem [LICENSE](LICENSE). Gói có giấy phép các thành phần đi kèm.

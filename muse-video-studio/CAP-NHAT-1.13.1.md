# Muse AI Studio 1.13.1 — gửi các ô cùng lượt trên một tài khoản

Bản Windows x64 đầy đủ. Giải nén ZIP vào thư mục mới, đóng bản cũ rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Dữ liệu tiếp tục ở `%LOCALAPPDATA%\Muse AI Studio`, gồm tài khoản, kịch bản và thư viện.

## Sửa việc chọn sáu ô nhưng gửi lần lượt

- Giữ mở từng trang Muse từ lúc chuẩn bị đến khi gửi, thay vì đóng trang kiểm tra rồi mở lại URL nháp. Giữ đúng đường dẫn dạng `#`, ngữ cảnh composer trong iframe và bộ nhớ phiên cần cho trang mới của cùng tài khoản.
- Với sáu ô đầu cùng tài khoản: mở sáu New chat, nhập đủ sáu prompt, rồi phát lệnh gửi cùng lượt. Không đợi video trước hoàn tất. Nếu chọn hai hoặc mười ô, cơ chế tương tự. Những ô vượt số luồng được bổ sung khi một ô kết thúc.
- Nếu không chuẩn bị đủ số ô đã chọn, dừng và báo lỗi trước khi gửi. Không tự chuyển sáu ô thành một luồng tuần tự. Muốn chạy một ô, chủ động chọn **1**.
- Tiến trình từng ô phân biệt **chờ các ô cùng lượt**, **đang gửi** và **Muse đã nhận prompt**. Thông tin trạng thái có thời điểm gửi/xác nhận, không chứa prompt hoặc URL riêng.
- Kết quả vẫn gắn theo dấu nhận diện từng yêu cầu. Phát hiện chung hội thoại thì dừng tài khoản đó để tránh lấy nhầm kết quả; không tự gửi lại.

## Tên từ TXT/SRT như tệp Troaimusic.txt

Nhận đủ các dạng `[1] nam`, `[4]thang`, `[ 1 ] tên`, kể cả khi trộn dấu cách trong cùng một tệp. Mỗi tiêu đề có một prompt bên dưới tạo đúng một ô theo thứ tự. Tên hiện ngay đầu ô và trong **Tên tệp ảnh/video**, được giữ qua mở lại và tải riêng/cả bộ: ví dụ `[1] nam` → `nam.png` hoặc `nam.mp4`. Cũng áp dụng khi tiêu đề nằm trong nội dung cue SRT. Số thứ tự của cue SRT và mốc thời gian không trở thành tên.

## Cách chạy sáu video

1. Đăng nhập và kiểm tra phiên Muse.
2. Chọn tài khoản, đặt **Ô chạy / tài khoản: 6**, bật sáu ô và nhập prompt.
3. Bấm Tạo. Tool chuẩn bị trang và nhập đủ prompt; sau đó sáu ô cùng chuyển sang gửi/đã nhận. Hủy riêng một ô giữ các ô khác.

Tên ảnh/video từ mục lớn TXT/SRT, đánh số liên tục khi thiếu tên, lựa chọn 1–10 ô riêng từng tài khoản, bố cục 10 tài khoản × 6 ô, IP proxy và chế độ khôi phục Studio đều được giữ.

## Kiểm chứng

Kiểm thử dùng Chromium/Electron thật với dịch vụ mô phỏng cục bộ. Kịch bản cố tình giữ ô nhập thứ sáu: năm ô còn lại không gửi sớm; khi thả ô thứ sáu, cả sáu yêu cầu tới trước bất kỳ kết quả nào. Có trường hợp URL nháp, hash, iframe, bộ nhớ phiên, hủy riêng và phát hiện chung hội thoại. Workflow Windows kiểm tra giao diện, proxy, khởi động và EXE sau đóng gói; chỉ tạo release khi các bước bắt buộc đạt.

Chưa dùng phiên Muse thật hoặc credit của bạn trong kiểm thử. Bản sửa điều khiển việc gửi đồng thời trong tool; thời điểm dịch vụ bắt đầu xử lý từng video vẫn phụ thuộc Muse và hạn mức tài khoản.

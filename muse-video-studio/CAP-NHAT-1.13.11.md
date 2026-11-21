# Muse AI Studio 1.13.11 — nhận tệp ảnh và video trên từng tài khoản

Bản Windows đầy đủ; không cần thư mục bản cũ. Đóng tool cũ, giải nén ZIP mới, mở Muse AI Studio.exe. Giữ dữ liệu ở %LOCALAPPDATA%\Muse AI Studio.

## Nhận ảnh bằng thao tác tải trên Muse

- Nhận các liên kết tệp nội bộ có dạng đường dẫn hoặc giao thức khác dạng sandbox:/mnt/data/. Với liên kết không dùng fetch trực tiếp được, tool kích hoạt đúng nút/liên kết tải hiện có trên trang Muse và nhận tệp qua phiên tài khoản đó.
- Nhận nút Download ảnh/video ngay cả khi trang chưa có thẻ img/video hoặc URL tải trực tiếp. Giữ thao tác click của trình duyệt cho các trình tải cần cử chỉ người dùng.
- Liên kết trả 404 hoặc tệp rỗng được thử lại có giới hạn để chờ tệp sẵn sàng; nếu còn lỗi, dùng thao tác Download có sẵn. Giữ việc nhận tệp đang chuẩn bị và không gửi lại yêu cầu tạo.
- Khi một đường dẫn HTTP mở trang xem tệp thay vì trả dữ liệu ảnh, thử thao tác tải gốc của chính liên kết đã đối chiếu. Không đoán API, không đọc đường dẫn file nội bộ trên máy và không gửi lại lệnh tạo.
- Chỉ lưu khi đã nhận và giải mã được tệp thật; kích thước lấy từ tệp. Lời “ready” hoặc dòng thông số không được coi là kết quả ảnh.
- Nếu một ô có liên kết lỗi, chỉ ô đó báo lỗi; các ô còn tạo tiếp tục nhận kết quả. Có chẩn đoán giao thức và loại nút/liên kết, không đưa URL đầy đủ hoặc tham số đăng nhập vào chẩn đoán.

## Ghép đúng video khi nhiều tài khoản trả mã khác nhau

- Nhận mã CLIP gốc ở đầu prompt, như CLIP 014 hoặc CLIP 020, bên cạnh mã theo dõi của tool. Mã rút gọn chỉ được dùng khi thuộc đúng lượt và xác định duy nhất một ô; không chia tệp theo thứ tự xuất hiện.
- Không dùng mã rút gọn khi có các lượt đang chồng lấn, mã mâu thuẫn hoặc nhãn đầy đủ của lượt khác. Giữ đối chiếu bằng nhãn đầy đủ trong các trường hợp này.
- Nhận lại từ lịch sử dùng đúng toàn bộ prompt, số ô và phạm vi lượt ban đầu; không gửi thêm tin nhắn hoặc tạo video mới.
- Thêm nút Sao chép trạng thái ngay khi ô đang chạy để lấy thông tin một lần bấm.

Giữ giới hạn chờ 250 giây, mặc định một tài khoản một luồng, các lựa chọn mở rộng sáu ô mỗi tài khoản, nhập nhiều TXT/SRT, hàng chờ theo số ô, tên tệp và kết quả của các nhóm trước.

Kiểm thử dùng dịch vụ mô phỏng có đăng nhập và tải tệp thật qua Chromium/Electron, gồm ba tài khoản mỗi tài khoản hai video, mã CLIP gốc khác số ô, các dạng liên kết nội bộ, nút tải riêng và chặn một liên kết mà không dừng ô còn lại. Không truy cập tài khoản Muse thật của người dùng; sự tương thích với mọi dạng trả lời của Muse không được coi là đã xác nhận chỉ từ kiểm thử mô phỏng.

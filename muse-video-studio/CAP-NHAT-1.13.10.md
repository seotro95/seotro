# Muse AI Studio 1.13.10 — bản Windows đầy đủ

## Bấm tạo lại ở nhiều ô

- Khi Muse đã trả lời rõ rằng tác vụ bắt đầu và ô Message sẵn sàng, tool cho gửi ô thêm vào mà không đợi tệp của ô trước hoàn tất; kết quả vẫn ghép theo nhãn riêng.
- Ô đang tạo không khóa nút Tạo lại, Tạo mới hoặc Nhận lại từ Muse của các ô khác.
- Có thể thêm ô ngay khi tài khoản đang chuẩn bị. Mỗi tài khoản chỉ chuẩn bị một lần trong cùng lượt; tối đa ba tài khoản chuẩn bị đồng thời.
- Giữ mặc định một tài khoản một luồng, mười tài khoản mười luồng. Ô thêm vào tài khoản đã kín luồng được xếp hàng; ở mục Một tài khoản có thể dùng sáu ô mỗi tài khoản và nhiều tài khoản như trước.
- Nút Dừng cảnh hủy đúng ô; Dừng tất cả hủy cả hàng chờ. Prompt, tên và kết quả đã lưu được giữ.
- Chuẩn bị tài khoản khác không chặn các tác vụ ở tài khoản đang chạy. Không thay đổi proxy hoặc phiên đang có yêu cầu.

## Nhiều tài khoản và thời gian chờ

- Chuẩn bị đồng thời trả đúng số luồng của từng tài khoản, không lấy nhầm số luồng từ tài khoản vừa được chọn sau cùng.
- Giữ riêng trang làm việc đã mở của từng hồ sơ và khôi phục lại sau khi mở tool. Đường dẫn được lưu cùng phiên mã hóa; không đưa các tài khoản đã đăng nhập về trang chủ thiếu ô Message nếu đã lưu trang làm việc hợp lệ.
- Kiểm tra ba phân vùng Electron riêng: cả ba tài khoản nhận lệnh video trước khi có kết quả, trả đúng tệp về đúng ô, và khôi phục đúng trang làm việc sau khi khởi động lại.
- Giới hạn chờ mới là **250 giây** cho ảnh/video, gồm chuẩn bị của lượt đầu. Trình kết nối nội bộ chờ tối đa 245 giây, bên xử lý chờ tối đa 240 giây để còn thời gian trả lỗi rõ ràng; phần thời gian chuẩn bị được trừ trước, không cộng thêm 250 giây mới.

## Hàng chờ nhiều TXT/SRT với ít ô

- Nhập tất cả tệp TXT/SRT cùng lúc; chọn **Lưu tất cả vào hàng chờ** để nhập trước, chưa gửi lệnh tạo.
- Chọn **Chạy theo số ô hiện có** để tự nạp từng nhóm prompt vào các ô đang mở. Ví dụ 125 prompt và 6 ô: xử lý đủ 125 prompt qua từng nhóm, không tăng bố cục thành 125 ô.
- Trong bảng hàng chờ, tích tệp cần chạy rồi bấm **Chạy mục đã chọn**, hoặc mở một tệp và bấm **Chạy tệp này**. Có thể bỏ chọn hoặc chọn riêng từng prompt.
- Hàng chờ lưu độc lập với các ô, hỗ trợ tổng số prompt lớn hơn 400. Tên, toàn bộ prompt, thứ tự và kết quả từng mục được giữ; các ô vẫn giữ giới hạn tài khoản/luồng đã chọn.
- Kết quả các nhóm trước được giữ trong thư viện khi ô nhận prompt tiếp theo. Dùng **Tải kết quả đã chọn** hoặc **Tải kết quả tệp** để lấy cả những nhóm đã rời khỏi các ô hiển thị. Hàng chờ và trạng thái được lưu trên máy; mở lại không tự gửi prompt đã chạy hay bị gián đoạn.
- Dừng tất cả ngừng cả việc nạp nhóm tiếp theo. Ngừng nạp thêm prompt cho các ô đang nhận chạy xong, giữ các prompt còn lại chưa chạy.

## Nhận ảnh và video

- Nhận liên kết tệp gốc dạng sandbox/attachment/artifact bằng thao tác tải có sẵn trên trang Muse. Chỉ dùng liên kết đã đối chiếu với đúng ô, nhận tệp thật qua phiên của tài khoản, giải mã và kiểm tra trước khi lưu.
- Không coi lời trả lời “ready” là tệp ảnh. Nếu Muse không cung cấp tệp tải được, báo lỗi riêng; không tự tạo lại hoặc tự chấp nhận nhân vật thay thế.
- Một ô bị từ chối tạo, kể cả phản hồi “could not be generated, no file was created”, không làm hỏng kết quả của các ô còn lại.
- Nhận nguồn ảnh đang tải chậm hoặc data-src; ưu tiên ảnh thật trước liên kết tải không hoạt động. Chặn liên kết ảo không có trình xử lý làm mất trang chat.
- Giữ kích thước thực tế; ảnh dọc hoặc độ phân giải thấp hơn yêu cầu vẫn báo đúng, không tự gắn nhãn 2K/4K.
- Nhận lại từ Muse chỉ lấy kết quả đã có, không gửi prompt mới.

## Dùng bản đầy đủ

Đóng bản đang chạy, giải nén ZIP ra thư mục mới, mở Muse AI Studio.exe hoặc BAT_DAU.bat. Không cần giữ thư mục bản cũ; dữ liệu dùng chung ở %LOCALAPPDATA%\Muse AI Studio. Giữ nhập nhiều TXT/SRT cùng lúc, tên theo prompt, tài khoản, proxy và thư viện.

Mỗi lượt xử lý vẫn có giới hạn chờ 250 giây. Thời gian tạo phía Muse và việc Muse cung cấp tệp thật nằm ngoài quyền điều khiển của tool. Kiểm thử dùng trang Muse mô phỏng có đăng nhập, tệp tải thật và ứng dụng Electron/EXE; không dùng credit của tài khoản Muse thực để xác nhận tốc độ hoặc nội dung đã tạo trong lịch sử của bạn.

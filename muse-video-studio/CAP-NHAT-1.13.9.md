# Muse AI Studio 1.13.9 — nhận nhãn trước/sau media, nhập nhiều TXT/SRT

Bản Windows x64 đầy đủ. Đóng hẳn bản cũ, giải nén toàn bộ ZIP vào thư mục mới rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần bản cũ, Node.js hoặc Chrome cài riêng. Dữ liệu trong `%LOCALAPPDATA%\Muse AI Studio` được giữ.

## Sửa đúng kiểu trả trong báo cáo 1.13.8

Báo cáo mới có năm nguồn video nhưng ghép được zero tệp. Sơ đồ phản hồi cho thấy các dòng như `- CLIP_002_1c6836bc:` đứng **trước** video, không có chữ “Done”. Các bản trước chưa bao quát kiểu trả này.

Bản này nhận nhãn riêng đứng trước hoặc sau media, nhãn dạng dấu gạch đầu dòng, nhãn không có câu báo hoàn thành, cùng các cấu trúc cũ có chú thích và thông báo tiến độ xen giữa. Không dùng chữ “Done” làm điều kiện bắt buộc để lấy tệp.

Tool lập các quan hệ có thể giữa nhãn và tệp trong các đoạn phản hồi kề nhau; giới hạn bởi nhãn khác và lượt người dùng. Chỉ nhận quan hệ một-một không có cách ghép khác tương đương. Không ghép theo số thứ tự cảnh hoặc thứ tự hoàn thành. Nguồn có tên/nhãn/thuộc tính xác định rõ được ưu tiên. Tệp đã tải và kiểm tra được giữ quan hệ với đúng ô khi phần giao diện Muse thay đổi; không dùng lại tệp đó cho ô khác. Trường hợp còn mơ hồ vẫn báo lý do, không tự gửi lại yêu cầu đã tạo.

Để lấy lại video cũ: giữ toàn bộ prompt, chọn đúng tài khoản và mở đúng cuộc trò chuyện trong **Đăng nhập Muse trong tool**, trở lại Studio rồi bấm **Nhận lại từ Muse**. Thao tác chỉ đọc và tải tệp đã có; các kết quả đang lưu được giữ. Giới hạn chờ **200 giây** không thay đổi.

## Tránh cộng dồn thời gian chờ và giảm xử lý thừa

Lượt đầu của mỗi tài khoản tính giới hạn 200 giây từ lúc bắt đầu chạy, gồm chuẩn bị tài khoản, xử lý ảnh đầu vào, API, tải/giải mã và chờ lưu thư viện. Ví dụ chuẩn bị mất 60 giây thì còn tối đa 140 giây. Phần thời gian còn lại được chuyển xuống máy chủ để không bắt đầu thêm một bộ đếm 190 giây sau bước chuẩn bị. Khi đã hết thời gian, không gửi thêm lệnh tạo. Các ô đang xếp hàng nhận thời gian riêng khi thực sự đến lượt; không tự tăng số luồng để đẩy nhanh chế độ mặc định.

Nhãn được trích trực tiếp thay vì liên tục tạo chuỗi lớn từ URL/base64. Danh sách prompt của các tệp được ghi nhớ trong giao diện và không phân tích lại mỗi lần cập nhật trạng thái. Giữ hàng tải/giải mã có giới hạn, tách với số tác vụ đang tạo tại Muse. Mục tiêu là nhận/tải ngay khi đã có đúng tệp, thay vì đợi đến timeout chỉ vì chưa nhận ra cách Muse trình bày.

Giới hạn này dừng chờ trong tool; không phải cam kết dịch vụ Muse luôn render xong trong 200 giây. Tác vụ đã được Muse nhận có thể còn xuất hiện trong lịch sử.

## Chọn nhiều tệp TXT và SRT trong một lần

Trong **Nhập TXT / SRT**, bấm **Chọn TXT / SRT** rồi chọn nhiều tệp cùng lúc. Có thể trộn TXT và SRT. Tệp được xếp theo tên có xét số, ví dụ `prompt-1`, `prompt-2`, `prompt-10`.

Mỗi tệp được phân tích riêng rồi mới ghép danh sách, nên số thứ tự SRT bắt đầu lại từ một hay các mục `[1] tên` trong tệp tiếp theo không làm lẫn prompt/tên của tệp trước. Có danh sách tệp, số prompt của từng tệp, tổng số prompt, và lựa chọn **Tệp đang chỉnh sửa** để sửa từng tệp trước khi nạp. TXT giữ cấu trúc nhiều dòng của prompt. Các tệp không có tên cảnh vẫn dùng bộ đánh số tải xuống sẵn có.

Khi nhập nhiều tệp vào bố cục liên tiếp và thiếu ô, tool mở thêm **ô xếp hàng** để nạp đủ nội dung, giữ nguyên số tài khoản và số luồng mỗi tài khoản. Không tự mở rộng một lựa chọn ô rời rạc/đã ẩn; cần chọn đủ ô trong trường hợp này. Tối đa 400 prompt mỗi lần nạp: nếu vượt, hiển thị tổng và khóa nút nạp, không tự cắt phần dư. Mỗi tệp tối đa 16 MB, tổng tệp tối đa 32 MB. Nếu có tệp lỗi, không nạp thiếu một phần của nhóm.

## Giữ nguyên hai chế độ theo yêu cầu

- **Mặc định:** mỗi tài khoản một luồng; 10 tài khoản chạy 10 luồng.
- **Mục Một tài khoản:** có thể chọn nhiều tài khoản và số ô trên mỗi tài khoản; 10 tài khoản × 6 ô = 60 ô đồng thời yêu cầu. Chọn số cao hơn khả năng Muse sẽ xếp hàng theo giới hạn đã xác minh.

Nhập nhiều tệp chỉ bổ sung nội dung/ô xếp hàng, không tự đổi hai chế độ, số tài khoản hoặc số luồng. Các kiểm tra Message, phiên, proxy/IP, hủy, khôi phục renderer và dự phòng tuần tự được giữ.

## Kiểm chứng và giới hạn

Tái hiện định dạng nhãn đứng trước năm media, không có “Done” hoặc UUID trong tên tệp: cách đọc cũ không ghép được, bản này đối chiếu đúng cả năm. Kiểm tra thêm nhãn đứng sau, nhãn đang chờ, nguồn mơ hồ, lượt người dùng, media lịch sử và giữ tệp đã tải với đúng ô. Kiểm tra trình duyệt thật dùng tệp MP4 riêng cho từng cảnh và so sánh đúng từng byte khi nhận lại, không phát sinh thêm tin nhắn/lệnh tạo.

Kiểm tra chọn TXT/SRT trộn chung, tên/cue bắt đầu lại ở từng tệp, sửa riêng một tệp, nhập 70 prompt vào nhóm 10 × 6 mà vẫn giữ cấu hình, và hiển thị đủ 401 prompt để từ chối nạp vượt giới hạn thay vì cắt còn 400. Bộ Windows tiếp tục kiểm tra chế độ mặc định, 60/72 tác vụ, phiên, proxy/IP, hủy, tải tệp và EXE đóng gói.

Kiểm tra đồng hồ giao diện: 60 giây chuẩn bị + 140 giây chờ tạo kết thúc ở mốc 200 giây, giữ prompt và chỉ một yêu cầu được gửi. Máy chủ cũng được kiểm tra với ngân sách còn lại ngắn, xác nhận hủy/giải phóng ô và không gửi lại yêu cầu.

Các bài tự động dùng dịch vụ mô phỏng, không dùng tài khoản hoặc credit Muse thật. Chưa trực tiếp tải năm tệp trong báo cáo từ máy người dùng; tốc độ và lựa chọn model/độ phân giải phía Muse phụ thuộc dịch vụ. Tool hiển thị kích thước thực tế và giữ giới hạn chờ 200 giây.

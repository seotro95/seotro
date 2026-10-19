# Voice Studio Riêng 1.6.0 · Windows 10/11 x64 Portable

Giải nén **toàn bộ ZIP** vào thư mục có quyền ghi, ví dụ `D:/VoiceStudio`, rồi mở **MO_TOOL.bat**. Giữ cửa sổ lệnh mở trong khi sử dụng; dùng Ctrl+C để tắt. Bản Portable đã có Python, FFmpeg, Nano và Turbo, dùng cục bộ với các giọng đi kèm.

## Nhập lời và khớp video

Nhập TXT/SRT UTF-8 hoặc Unicode UTF-16 của Windows, tối đa **1.000.000 ký tự**, 8 MB mỗi tệp. SRT giữ các mốc gốc; TXT có mốc phải xác định được mốc kết thúc. TXT không có mốc được đọc liên tục và xuất SRT dựa trên lời đọc thực.

Chọn **WAV** khi dựng video. Tool tự căn từng câu: câu dài đổi nhịp, câu ngắn giữ khoảng lặng. Câu bị ép quá nhanh cần nghe kiểm tra; tool báo lỗi khi không thể xử lý đầy đủ. Không tự bỏ hoặc viết lại lời. Nút **Tự căn và tiếp tục** dùng lại những mảnh đã tạo của tác vụ cũ.

Ví dụ `00:27:20,519 --> 00:27:23,671` có ô lời dài **3,152 giây**. Nếu đây là câu cuối, WAV giữ timeline từ 0 đến **27:23,671**. MP3 có thể có padding tùy phần mềm giải mã. Chi tiết TXT có mốc nằm trong `HUONG_DAN_CAN_MOC.txt`.

## Chọn tốc độ và giọng

Bản 1.6 sửa lỗi giọng Mai Anh/Turbo chỉ chạy một tác vụ. Chọn **Ưu tiên tốc độ → Tự đo và tối ưu CPU** để tối ưu giọng đang chọn. Nano và Turbo có cấu hình RAM/CPU và kết quả đo riêng. CPU Xeon E5 v4 dùng Turbo FP32; không ép INT8 trên CPU thiếu VNNI.

Bấm **Chuyển sang Nano và đo tốc độ** khi muốn so sánh bộ giọng nhanh. Chỉ nút đổi giọng chủ động mới chọn Nano; kịch bản giữ nguyên. Bản thu hiện rõ bộ giọng, số tác vụ/luồng và FP32 hoặc số bước Nano thực dùng.

- **Nhanh:** Nano 4 bước, nhiều tiến trình theo tài nguyên máy, bộ căn WSOLA. Cần nghe lại chất lượng.
- **Cân bằng:** Nano 8 bước. **Chất lượng:** Nano 16 bước; ưu tiên chất lượng thay vì số đo tốc độ.
- Nano và Turbo hỗ trợ tối đa **32 tác vụ CPU**. Máy 56 luồng / 28 lõi vật lý, đủ RAM bắt đầu ở 28 tác vụ × 1 luồng; tool không coi luồng ảo là lõi vật lý.
- Chọn **giọng Nano → Ưu tiên tốc độ → Tự đo và tối ưu CPU**. Tool thử nhiều cấu hình bằng lời thật và lưu cấu hình nhanh nhất đo được; số bước tạo giọng giữ theo chế độ đã chọn. Thử nhiều cấu hình lần đầu có thể mất vài phút.
- Bấm **Sao chép kết quả đo** để gửi số liệu, không kèm kịch bản riêng. Có thể dừng quá trình đo bằng nút Dừng tạo.
- Số đo dùng thời lượng lời đã tạo, loại khoảng lặng SRT. Kết quả phân biệt lượt nạp model và lượt model đã sẵn sàng; hãy kiểm tra cả kịch bản dài để xác nhận mốc 2 phút/1 giờ.
- Có 10 nhịp/thể loại: Tự nhiên, Tin tức, Review, Kể chuyện, Kinh dị nhịp chậm, Cổ tích, Thuyết minh, Quảng cáo, Chậm rãi, Sôi nổi.
- Gợi ý giọng dùng mẫu đọc tin tức/kể chuyện có sẵn. Sắc thái phụ thuộc mẫu giọng và dấu câu; bộ chọn thể loại điều chỉnh nhịp/nghỉ, không bảo đảm diễn xuất như người thật.
- `**từ nhấn**`, `[pause=0.8]` điều chỉnh chủ động. VieNeu nhận `[cười]`, `[thở dài]`, `[hắng giọng]` khi bạn tự thêm; tool không tự thêm các âm thanh này.

**Không bảo đảm đạt 30× thời gian thực hoặc tạo 1 giờ trong 2 phút.** Hiệu năng phụ thuộc CPU, RAM, giọng, độ dài đoạn và nạp model. Lượt đo ngắn chỉ là ước tính; nhiều tiến trình có thể chậm hơn nếu máy thiếu tài nguyên.

## Dữ liệu và phạm vi

Mẫu cá nhân, bản thu, lịch sử và model nằm trong **app/.data**. Sao lưu trước cập nhật. Giải nén sang thư mục mới; giữ bản cũ để bảo toàn dữ liệu. Gói không chứa lời, bản thu hoặc khóa của người dùng.

Tối đa **24 giờ** mỗi tác vụ. Một triệu ký tự có thể vượt thời lượng hoặc dung lượng đĩa; chia kịch bản để đọc hết. WAV mono 24 kHz dài 24 giờ cần khoảng 4,15 GB, chưa tính cache/tệp tạm. Tool báo khi không thể xuất đầy đủ.

Gói chỉ tạo âm thanh, không dựng video. Qwen quốc tế không được đóng gói. Giọng Windows chỉ hiện nếu máy có SAPI tương ứng. Giao diện chỉ mở trên máy cục bộ; không mở cổng dịch vụ ra Internet.

## Kiểm tra bản phát hành

Builder chỉ tạo ZIP sau kiểm tra Windows bằng Python đóng gói tại đường dẫn đã di chuyển: inference Nano/Turbo ngoại tuyến, nhịp tin tức bằng Nano, căn SRT với FFmpeg/WSOLA, giữ cao độ và phần đầu/cuối âm thanh thử, xuất WAV/MP3/TXT/SRT và khởi động giao diện HTTP. Kết quả mẫu lạnh/ấm nằm trong **PORTABLE-QA.json** và **BUILD_INFO.json**. Đây là số đo máy dựng gói, không phải cam kết với máy của bạn hoặc thử toàn bộ một triệu ký tự.

SHA256 của ZIP và manifest từng tệp đi kèm bản phát hành. Giấy phép Python, thư viện, FFmpeg và model được giữ trong gói. Không tắt TLS, checksum hoặc phần mềm bảo vệ để xử lý lỗi tải.

Nếu bạn chủ động dùng **bản mã nguồn**, có thể dùng Python 3.12 x64 cùng các BAT cài đặt của mã nguồn. Đây là quy trình khác; người dùng gói Portable chỉ cần giải nén và mở MO_TOOL.bat.

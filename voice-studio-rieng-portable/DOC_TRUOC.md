# Voice Studio Riêng 1.8.0 · Windows 10/11 x64 Portable

Giải nén **toàn bộ ZIP** vào thư mục có quyền ghi, ví dụ `D:/VoiceStudio`, rồi mở **MO_TOOL.bat**. Giữ cửa sổ lệnh mở trong khi sử dụng; dùng Ctrl+C để tắt. Bản Portable đã có Python, FFmpeg, Nano và Turbo, dùng cục bộ với các giọng đi kèm.

## Nhập lời và khớp video

Nhập TXT/SRT UTF-8 hoặc Unicode UTF-16 của Windows, tối đa **1.000.000 ký tự**, 8 MB mỗi tệp. SRT giữ các mốc gốc; TXT có mốc phải xác định được mốc kết thúc. TXT không có mốc được đọc liên tục và xuất SRT dựa trên lời đọc thực.

Chọn **WAV** khi dựng video. Tool tự căn từng câu: câu dài đổi nhịp, câu ngắn giữ khoảng lặng. Câu bị ép quá nhanh cần nghe kiểm tra; tool báo lỗi khi không thể xử lý đầy đủ. Không tự bỏ hoặc viết lại lời. Nút **Tự căn và tiếp tục** dùng lại những mảnh đã tạo của tác vụ cũ.

Ví dụ `00:27:20,519 --> 00:27:23,671` có ô lời dài **3,152 giây**. Nếu đây là câu cuối, WAV giữ timeline từ 0 đến **27:23,671**. MP3 có thể có padding tùy phần mềm giải mã. Chi tiết TXT có mốc nằm trong `HUONG_DAN_CAN_MOC.txt`.

## Chọn tốc độ và giọng

Bản 1.8 giữ giọng đang chọn và ghi nhớ chế độ tốc độ, ngôn ngữ cùng cấu hình CPU. Chọn **Ưu tiên tốc độ**, nghe mẫu và bấm **Đo tốc độ** để kiểm tra kết quả thực trên máy bạn. Bộ đo dùng câu thử đúng ngôn ngữ của giọng Việt/Anh và giọng mẫu quốc tế.

Câu SRT được tạo và căn trong nhiều tiến trình; bước xuất cuối vẫn ghép theo thứ tự mốc gốc. Các mảnh đã xong được giữ để tiếp tục, và bản thu chỉ hoàn tất khi đủ lời, đủ câu và đúng timeline.

Bộ giọng quốc tế dùng lại phần mã hóa mẫu, tránh xử lý lại cùng bản thu ở mỗi câu. Với đúng VoxCPM 2.0.3 trên CPU FP32, attention chỉ đọc phần cache đã có dữ liệu; phép tính và trọng số được giữ nguyên. **Nhanh** dùng 4 bước, **Cân bằng** 8 bước và **Chất lượng** 10 bước. Giảm số bước có thể thay đổi phát âm và sắc thái; hãy nghe mẫu trước bản dài.

Đo cùng 10 bước trên máy đám mây dùng 4 luồng cho thấy mẫu Nhật ngắn nhanh hơn khoảng **2,00 lần**, mẫu Thái khoảng **1,79 lần** sau tối ưu và tái sử dụng mẫu. Đây là hai câu thử dài 2–4 giây, chưa phải phép đo một giờ hoặc kết quả trên máy của bạn. Báo cáo chi tiết nằm trong **CPU-SHORT-SPEECH-BENCHMARK.json**. Mẫu Nhật 4 bước bị sai phần cuối khi kiểm tra bằng nhận dạng giọng nói tự động, nên lần mở đầu vẫn dùng Cân bằng; chọn Nhanh khi chấp nhận đánh đổi và đã nghe thử.

Số tiến trình quốc tế được giới hạn riêng theo RAM và lõi vật lý, tối đa 8; mỗi model FP32 được dự trù 16 GiB cùng khoảng trống cho hệ thống. Ví dụ 28 lõi vật lý và 128 GiB RAM còn đủ trống có thể chọn tối đa 7 tiến trình × 4 luồng. Nano/Turbo vẫn có giới hạn và phép tự đo riêng. Không áp số đo Nano cho giọng quốc tế.

Mai Anh/Turbo hỗ trợ nhiều tác vụ song song. Chọn **Ưu tiên tốc độ → Tự đo và tối ưu CPU** để tối ưu giọng đang chọn. Nano và Turbo có cấu hình RAM/CPU và kết quả đo riêng. CPU Xeon E5 v4 dùng Turbo FP32; không ép INT8 trên CPU thiếu VNNI.

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

## Thư viện giọng mẫu và giọng quốc tế

Bản 1.8 đọc thư viện giọng mặc định trong **app/voice-library**. Nếu có gói giọng riêng, cài gói cập nhật vào thư mục Portable đang dùng, sau khi đóng tool. Các giọng xuất hiện trong nhóm mẫu mặc định; bấm nghe thử để chọn. Mẫu và giọng cá nhân trong **app/.data/voices** vẫn được giữ. Các bản ghi âm riêng chỉ được đưa vào bản GitHub ở dạng mã hóa; mật khẩu được gửi riêng. Khi mở bộ 19 giọng, chỉ thư viện giọng được thêm, mã ứng dụng hiện tại được giữ để tránh quay lại bản cũ.

Mẫu tiếng Anh dùng Turbo đã đi kèm. Với mẫu tiếng Hàn, Nga, Nhật, Pháp, Tây Ban Nha và Thái, chạy **TAI_GIONG_DA_NGON_NGU.bat** một lần khi có Internet. Bộ cài tải model **VoxCPM2 khoảng 5 GB** cùng các thư viện CPU vào **runtime-international** riêng; cần thêm dung lượng cho thư viện, tệp tải tạm và quá trình cài đặt. Runtime Nano/Turbo hiện có được giữ nguyên. Giấy phép, nguồn và checksum model được lưu cùng bộ model.

Cài đặt và nạp model lần đầu có thể mất nhiều thời gian. Chỉ khi kiểm tra tạo lời thành công, giọng quốc tế mới báo sẵn sàng. Mở lại tool sau khi hoàn tất; những lần tạo tiếp theo dùng model cục bộ. Bộ này chạy CPU FP32, có cấu hình Nhanh/Cân bằng/Chất lượng cùng số đo riêng; không dùng số đo Nano/Turbo để suy ra tốc độ quốc tế hoặc cam kết 2 phút/1 giờ. Độ giống giọng và cảm xúc phụ thuộc mẫu, lời đọc và model; nghe kiểm tra trước khi dựng video.

## Dữ liệu và phạm vi

Mẫu cá nhân, bản thu, lịch sử và model nằm trong **app/.data**. Sao lưu trước cập nhật. Giải nén sang thư mục mới; giữ bản cũ để bảo toàn dữ liệu. Bản công khai không chứa lời hoặc khóa riêng; nếu kèm bộ giọng riêng thì bộ đó được mã hóa, không công khai bản thu ở dạng đọc được. Gói giọng riêng chứa các mẫu được đưa vào thư viện và cần được giữ riêng.

Tối đa **24 giờ** mỗi tác vụ. Một triệu ký tự có thể vượt thời lượng hoặc dung lượng đĩa; chia kịch bản để đọc hết. WAV mono 24 kHz dài 24 giờ cần khoảng 4,15 GB, chưa tính cache/tệp tạm. Tool báo khi không thể xuất đầy đủ.

Gói chỉ tạo âm thanh, không dựng video. Qwen quốc tế không được đóng gói. Giọng Windows chỉ hiện nếu máy có SAPI tương ứng. Giao diện chỉ mở trên máy cục bộ; không mở cổng dịch vụ ra Internet.

## Kiểm tra bản phát hành

Builder chỉ tạo ZIP sau kiểm tra Windows bằng Python đóng gói tại đường dẫn đã di chuyển: inference Nano/Turbo ngoại tuyến, nhịp tin tức bằng Nano, căn SRT với FFmpeg/WSOLA, giữ cao độ và phần đầu/cuối âm thanh thử, xuất WAV/MP3/TXT/SRT và khởi động giao diện HTTP. Kết quả mẫu lạnh/ấm nằm trong **PORTABLE-QA.json** và **BUILD_INFO.json**. Đây là số đo máy dựng gói, không phải cam kết với máy của bạn hoặc thử toàn bộ một triệu ký tự.

SHA256 của ZIP và manifest từng tệp đi kèm bản phát hành. Giấy phép Python, thư viện, FFmpeg và model đi kèm được giữ trong gói; bộ quốc tế tải riêng giữ giấy phép cạnh model. Không tắt TLS, checksum hoặc phần mềm bảo vệ để xử lý lỗi tải.

Nếu bạn chủ động dùng **bản mã nguồn**, có thể dùng Python 3.12 x64 cùng các BAT cài đặt của mã nguồn. Đây là quy trình khác; người dùng gói Portable chỉ cần giải nén và mở MO_TOOL.bat.

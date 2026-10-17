# Voice Studio Riêng 1.1 · Windows 10/11 x64

Công cụ tạo giọng từ văn bản, tách riêng khỏi video và dịch phụ đề. Mở giao diện bằng trình duyệt trên chính máy của bạn; giữ cửa sổ lệnh chạy nền khi sử dụng.

## Cài và mở

1. Giải nén **toàn bộ ZIP** vào thư mục được phép ghi, ví dụ `D:\Voice-Studio-Rieng`. Không mở các tệp BAT trực tiếp trong ZIP.
2. Cài **Python 3.12 bản 64-bit** từ https://www.python.org/downloads/windows/ nếu chưa có. Khi cài chọn **Add python.exe to PATH**.
3. Chạy **CAI_DAT.bat**. Bộ cài tạo môi trường Python riêng trong `.venv` và cài thư viện. Nếu chưa có FFmpeg/ffprobe, bộ cài tải FFmpeg Windows từ BtbN qua HTTPS và kiểm tra SHA256 theo manifest của nhà phát hành. Không cần quyền quản trị cho thư mục của tool.
4. Chạy **TAI_GIONG_VIET.bat** để tải và kiểm tra giọng Việt Nano. Cần Internet, thời gian tải và dung lượng đĩa. Thao tác này chỉ báo thành công khi mô hình chạy được mẫu thử; lỗi tải không được coi là đã cài giọng.
5. Chạy **MO_TOOL.bat**. Giao diện mở tự động. Nhập lời, chọn giọng hiển thị sẵn sàng rồi bấm tạo voice. Dùng **Ctrl+C** trong cửa sổ lệnh để tắt.

Nếu cần giọng Việt/Anh tiêu chuẩn và nhân bản giọng Việt, chạy thêm **TAI_GIONG_TIEU_CHUAN.bat** để tải VieNeu Turbo. **TAI_GIONG_QUOC_TE.bat** cài PyTorch CPU/Qwen và tải cả mô hình giọng có sẵn lẫn nhân bản quốc tế; cần thêm vài GB và xử lý trên CPU có thể chậm. Đây là bước tùy chọn, không bắt buộc cho giọng Việt Nano hoặc giọng Windows SAPI đã cài.

## Nhân bản tiếng Việt ưu tiên tốc độ · bản 1.1

1. Chạy **TAI_GIONG_NHAN_BAN_NHANH.bat** một lần. Bước này tải thêm các đồ thị mã hóa mẫu giọng Nano, khoảng 92 MB ngoài mô hình Nano cơ bản, rồi kiểm tra nhân bản thật. Không cần NVIDIA, PyTorch hoặc API key cho chế độ này.
2. Trong **Thư viện giọng**, thêm hoặc chọn đúng mẫu giọng cá nhân tiếng Việt đã được phép sử dụng. Mẫu đã lưu từ bản trước dùng lại được.
3. Ở màn hình tạo giọng, bấm **Ưu tiên tốc độ**. Tool giữ đúng mẫu giọng đã chọn, chuyển sang **Nhân bản Nano**, 4 bước, CPU tự động, WAV, nhịp tự nhiên 1× và không thêm nghỉ giữa các đoạn.
4. Có thể bấm **Đo tốc độ thực** để tạo một bài mẫu riêng. Nội dung editor của bạn được giữ nguyên. Kết quả gồm tốc độ thực đo trên máy, thời gian xử lý và ước tính cho một giờ; phép đo mẫu ngắn không chứng minh tốc độ của một bản thu một giờ.

Mẫu giọng được mã hóa một lần trong mỗi tiến trình và tái sử dụng cho các đoạn tiếp theo. Nhiều tiến trình xử lý các đoạn độc lập, sau đó ghép theo đúng thứ tự. Tool tự giới hạn tiến trình và luồng theo CPU/RAM khả dụng, tối đa 8 tiến trình. Với máy ít RAM hoặc ít lõi CPU, tốc độ có thể thấp hơn.

Nano 4 bước giảm độ tự nhiên/độ bám giọng so với cấu hình chất lượng cao hơn. Hãy nghe thử trước; có thể chọn 8/16 bước hoặc chuyển lại nhân bản tiêu chuẩn nếu cần. Chế độ nhanh vẫn dùng mẫu giọng của bạn, không tự thay bằng giọng có sẵn. Lựa chọn Nano nhân bản hiện chỉ áp dụng cho tiếng Việt. Các thiết lập kiểu kể chuyện, nhấn từ, tốc độ khác 1×, căn mốc SRT hoặc xuất MP3 có thể thêm chi phí xử lý.

## Cập nhật từ bản ZIP cũ

Tắt tool bằng Ctrl+C và sao lưu **app/.data** trước. Giải nén bản mới rồi chép các tệp mới vào cùng thư mục tool cũ, giữ nguyên **.venv** và **app/.data**. Các đoạn của tác vụ đang dở từ bản cũ chưa có fingerprint có thể phải tạo lại một lần để tránh dùng nhầm nội dung; bản thu đã xuất vẫn được giữ. ZIP không chứa các thư mục dữ liệu này nên không yêu cầu xóa chúng. Nếu dùng một thư mục mới hoàn toàn, cần cài thư viện lại và chuyển bản sao **app/.data** sang đúng vị trí trong tool mới. Sau đó chạy **TAI_GIONG_NHAN_BAN_NHANH.bat** và mở **MO_TOOL.bat**; kiểm tra giao diện ghi phiên bản **1.1.0**.

**KIEM_TRA.bat** kiểm tra thư viện và trạng thái mô hình khi cần hỗ trợ. Không xóa `.venv` hoặc `app/.data` để cập nhật tool; sao lưu dữ liệu trước.

## Tính năng

- Nhập/dán tối đa **200.000 ký tự** mỗi tác vụ; nhập tệp TXT/SRT UTF-8 tối đa 2 MB. Ký tự dấu, dấu cách và xuống dòng đều tính vào giới hạn.
- Giọng Việt Nano/Turbo; giọng đa ngôn ngữ Qwen là tùy chọn. Giọng Windows chỉ hiện khi SAPI trên máy truy cập được. Không phải tất cả ngôn ngữ trong danh sách đều có giọng AI.
- Lưu mẫu giọng cá nhân dài 3–30 giây, tối đa 20 MB, từ một người nói và được chủ giọng cho phép. Lưu mẫu không phải huấn luyện mô hình; mô hình nhân bản tạo lời đọc mới khi bạn bấm tạo voice.
- Tốc độ đọc 0,7–1,4×; nhịp tự nhiên, kể chuyện, tin tức, thư giãn, sôi nổi. `**từ cần nhấn**` và `[pause=1.5]` điều chỉnh nhịp và khoảng nghỉ. Các thiết lập này không bảo đảm diễn xuất cảm xúc như người thật.
- Tạo liên tục hoặc theo mốc SRT; hàng đợi, tiến độ, dừng/tiếp tục và nghe lại. Giới hạn bản thu 180 phút mỗi tác vụ; 200.000 ký tự có thể vượt thời lượng này, nên cần chia lời thành nhiều tác vụ để đọc hết. Tool phải báo khi chạm giới hạn, không coi phần lời còn lại là đã đọc.
- Xuất WAV/MP3 và TXT/SRT. Với TXT, SRT của bản thu chỉ có sau khi tạo giọng xong để dùng mốc đoạn đọc thực. Không tự căn chính xác từng từ.

Chưa có chức năng chia bản xuất thành các tệp đúng 2 phút hoặc ghép các tệp âm thanh do người dùng tải lên. Tool tự ghép các mảnh mô hình thành một bản thu trong mỗi tác vụ. Chưa có phong cách “review phim” riêng; có thể dùng nhịp kể chuyện hoặc sôi nổi tùy lời đọc.

Mục tiêu 2 phút tạo 1 giờ đã đạt trong phép đo trọn tác vụ ở mục hiệu năng, không phải cam kết cho mọi máy. Tốc độ phụ thuộc CPU, RAM, mô hình, ngôn ngữ và độ dài lời. Cần đo thực tế trên máy của bạn và nghe kiểm tra phát âm.

## Dữ liệu và kết nối

- Mẫu giọng, bản thu, lịch sử, các đoạn đã tạo và bộ nhớ đệm mô hình nằm trong **app/.data**. Sao lưu thư mục này để giữ dữ liệu.
- Gói ZIP không kèm API key, tài khoản, mẫu giọng cá nhân, Python, thư viện đã cài hoặc trọng số mô hình. Lần cài và tải mô hình đầu tiên cần Internet; các giọng AI đã tải đầy đủ có thể suy luận cục bộ.
- Máy cần truy cập PyPI (`pypi.org`, `files.pythonhosted.org`), GitHub để tải FFmpeg, Hugging Face (`huggingface.co`, các miền con `huggingface.co` và `hf.co`) để tải mô hình; Qwen thêm `download.pytorch.org` và `download-r2.pytorch.org`.
- Giao diện chỉ lắng nghe trên máy cục bộ. Đây là studio cá nhân, không có đăng nhập cho nhiều người dùng; không mở cổng ra Internet.
- Bộ cài không tắt xác minh TLS, checksum, antivirus hoặc Windows execution policy. Nếu gặp lỗi 403/mạng, cho phép đúng máy chủ cần tải rồi chạy lại bước bị lỗi. Không nhập khóa hoặc mật khẩu vào cuộc trò chuyện.

## Phạm vi đã kiểm tra

Đã kiểm tra bộ cài thư viện, khởi động API và giao diện, giới hạn ký tự, nhập mẫu, xử lý WAV/MP3 và xuất TXT/SRT trên Linux/Python 3.12 với FFmpeg thật. Các gói thư viện nền đã được resolver kiểm tra có bản phân phối cho Python 3.12/Windows x64.

Đã tải và kiểm tra mô hình nhân bản Nano bằng chính bộ cài. Tác vụ nhân bản tiếng Việt 80.053 ký tự tạo **64 phút 56,6 giây WAV trong 80,5 giây**, gồm nạp mô hình và mã hóa mẫu từ worker lạnh, trên Linux với hạn mức 4 lõi CPU / 32 GiB RAM. Xuất MP3 thêm 11,6 giây, tổng tạo WAV + MP3 là **92,1 giây**, dưới 2 phút. TXT/SRT khớp đủ 844 đoạn. Mỗi đoạn được tạo mới, không dùng lại âm thanh hay thêm khoảng lặng để tăng số đo. Mẫu giọng kiểm thử là âm thanh tổng hợp, không phải mẫu người thật. Xem **HIEU_NANG.md** và **BENCHMARK_RESULT.json** để biết cách đo và giới hạn; chưa kiểm chứng trên máy Windows của bạn.

Chưa chạy BAT hoặc giọng Windows SAPI trên máy Windows thực. Chưa xác minh suy luận Turbo hoặc Qwen trong gói này. Đây là **gói mã nguồn kèm bộ cài**, không phải EXE portable có sẵn mô hình.

## Linux/macOS (phụ)

Cần Python 3.12 và FFmpeg/ffprobe được cài sẵn. Chạy `bash install.sh`, `.venv/bin/python bootstrap.py --models vieneu_nano`, rồi `bash start.sh`. Gói được chuẩn bị ưu tiên Windows x64; chưa kiểm tra macOS hoặc CPU ARM.

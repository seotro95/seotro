## Bản 1.3.0: tự căn lời SRT

Mặc định tự tăng tốc riêng các câu dài để giữ mốc gốc, thay vì dừng ở giới hạn 1,5×. Trong Bản thu, nút **Tự căn và tiếp tục** áp dụng cho tác vụ SRT cũ, giữ các đoạn đã tạo. Các câu cần trên 2× được cảnh báo để nghe lại. Ô quá ngắn vẫn có thể khiến lời khó nghe; không tự viết lại hoặc bỏ chữ.

Để cập nhật và giữ giọng cá nhân/model: tắt tool, sao lưu, chép nội dung `app` mới vào `app` cũ; giữ nguyên `.data`, `.venv`, `tools`. Đọc `HUONG_DAN_CAN_MOC.txt`.

# Voice Studio Riêng · Windows 10/11 x64

Công cụ tạo giọng từ văn bản, tách riêng khỏi video và dịch phụ đề. Mở giao diện bằng trình duyệt trên chính máy của bạn; giữ cửa sổ lệnh chạy nền khi sử dụng.

## Cài và mở

1. Giải nén **toàn bộ ZIP** vào thư mục được phép ghi, ví dụ `D:\Voice-Studio-Rieng`. Không mở các tệp BAT trực tiếp trong ZIP.
2. Cài **Python 3.12 bản 64-bit** từ https://www.python.org/downloads/windows/ nếu chưa có. Khi cài chọn **Add python.exe to PATH**.
3. Chạy **CAI_DAT.bat**. Bộ cài tạo môi trường Python riêng trong `.venv` và cài thư viện. Nếu chưa có FFmpeg/ffprobe, bộ cài tải FFmpeg Windows từ BtbN qua HTTPS và kiểm tra SHA256 theo manifest của nhà phát hành. Không cần quyền quản trị cho thư mục của tool.
4. Chạy **TAI_GIONG_VIET.bat** để tải và kiểm tra giọng Việt Nano. Cần Internet, thời gian tải và dung lượng đĩa. Thao tác này chỉ báo thành công khi mô hình chạy được mẫu thử; lỗi tải không được coi là đã cài giọng.
5. Chạy **MO_TOOL.bat**. Giao diện mở tự động. Nhập lời, chọn giọng hiển thị sẵn sàng rồi bấm tạo voice. Dùng **Ctrl+C** trong cửa sổ lệnh để tắt.

Nếu cần giọng Việt/Anh tiêu chuẩn và nhân bản giọng Việt, chạy thêm **TAI_GIONG_TIEU_CHUAN.bat** để tải VieNeu Turbo. **TAI_GIONG_QUOC_TE.bat** cài PyTorch CPU/Qwen và tải cả mô hình giọng có sẵn lẫn nhân bản quốc tế; cần thêm vài GB và xử lý trên CPU có thể chậm. Đây là bước tùy chọn, không bắt buộc cho giọng Việt Nano hoặc giọng Windows SAPI đã cài.

**KIEM_TRA.bat** kiểm tra thư viện và trạng thái mô hình khi cần hỗ trợ. Không xóa `.venv` hoặc `app/.data` để cập nhật tool; sao lưu dữ liệu trước.

## Tính năng

- Nhập/dán tối đa **1.000.000 ký tự** mỗi tác vụ; nhập tệp TXT/SRT UTF-8 tối đa 8 MB. Ký tự dấu, dấu cách và xuống dòng đều tính vào giới hạn.
- Giọng Việt Nano/Turbo; giọng đa ngôn ngữ Qwen là tùy chọn. Giọng Windows chỉ hiện khi SAPI trên máy truy cập được. Không phải tất cả ngôn ngữ trong danh sách đều có giọng AI.
- Lưu mẫu giọng cá nhân dài 3–30 giây, tối đa 20 MB, từ một người nói và được chủ giọng cho phép. Lưu mẫu không phải huấn luyện mô hình; mô hình nhân bản tạo lời đọc mới khi bạn bấm tạo voice.
- Tốc độ đọc 0,7–1,4×; nhịp tự nhiên, kể chuyện, tin tức, thư giãn, sôi nổi. `**từ cần nhấn**` và `[pause=1.5]` điều chỉnh nhịp và khoảng nghỉ. Các thiết lập này không bảo đảm diễn xuất cảm xúc như người thật.
- Tạo liên tục hoặc theo mốc SRT; hàng đợi, tiến độ, dừng/tiếp tục và nghe lại. Giới hạn bản thu 1440 phút (24 giờ) mỗi tác vụ; 1.000.000 ký tự có thể vượt thời lượng này, nên cần chia lời thành nhiều tác vụ để đọc hết. Tool phải báo khi chạm giới hạn, không coi phần lời còn lại là đã đọc.
- Xuất WAV/MP3 và TXT/SRT. Với TXT, SRT của bản thu chỉ có sau khi tạo giọng xong để dùng mốc đoạn đọc thực. Không tự căn chính xác từng từ.

Chưa có chức năng chia bản xuất thành các tệp đúng 2 phút hoặc ghép các tệp âm thanh do người dùng tải lên. Tool tự ghép các mảnh mô hình thành một bản thu trong mỗi tác vụ. Chưa có phong cách “review phim” riêng; có thể dùng nhịp kể chuyện hoặc sôi nổi tùy lời đọc.

Không bảo đảm tốc độ 1 phút tạo hơn 1 giờ âm thanh. Tốc độ phụ thuộc CPU, mô hình, ngôn ngữ và độ dài lời. Cần đo thực tế trên máy của bạn và nghe kiểm tra phát âm.

## Dữ liệu và kết nối

- Mẫu giọng, bản thu, lịch sử, các đoạn đã tạo và bộ nhớ đệm mô hình nằm trong **app/.data**. Sao lưu thư mục này để giữ dữ liệu.
- Gói ZIP không kèm API key, tài khoản, mẫu giọng cá nhân, Python, thư viện đã cài hoặc trọng số mô hình. Lần cài và tải mô hình đầu tiên cần Internet; các giọng AI đã tải đầy đủ có thể suy luận cục bộ.
- Máy cần truy cập PyPI (`pypi.org`, `files.pythonhosted.org`), GitHub để tải FFmpeg, Hugging Face (`huggingface.co`, các miền con `huggingface.co` và `hf.co`) để tải mô hình; Qwen thêm `download.pytorch.org` và `download-r2.pytorch.org`.
- Giao diện chỉ lắng nghe trên máy cục bộ. Đây là studio cá nhân, không có đăng nhập cho nhiều người dùng; không mở cổng ra Internet.
- Bộ cài không tắt xác minh TLS, checksum, antivirus hoặc Windows execution policy. Nếu gặp lỗi 403/mạng, cho phép đúng máy chủ cần tải rồi chạy lại bước bị lỗi. Không nhập khóa hoặc mật khẩu vào cuộc trò chuyện.

## Phạm vi đã kiểm tra

Đã kiểm tra bộ cài thư viện, khởi động API và giao diện, giới hạn ký tự, nhập mẫu, xử lý WAV/MP3 và xuất TXT/SRT trên Linux/Python 3.12 với FFmpeg thật. Các gói thư viện nền đã được resolver kiểm tra có bản phân phối cho Python 3.12/Windows x64.

Đã tải mô hình Nano bằng chính bộ cài của gói và tạo voice tiếng Việt thật qua API: 148 ký tự thành 8,23 giây âm thanh, thời gian xử lý mẫu khoảng 1,11 giây trên CPU; xuất WAV/MP3/TXT/SRT đều thành công. Đây là phép đo mẫu ngắn, không bảo đảm tốc độ với kịch bản dài hoặc chất lượng phát âm trong mọi trường hợp.

Chưa chạy BAT hoặc giọng Windows SAPI trên máy Windows thực. Chưa xác minh suy luận Turbo hoặc Qwen trong gói này. Đây là **gói mã nguồn kèm bộ cài**, không phải EXE portable có sẵn mô hình.

## Linux/macOS (phụ)

Cần Python 3.12 và FFmpeg/ffprobe được cài sẵn. Chạy `bash install.sh`, `.venv/bin/python bootstrap.py --models vieneu_nano`, rồi `bash start.sh`. Gói được chuẩn bị ưu tiên Windows x64; chưa kiểm tra macOS hoặc CPU ARM.

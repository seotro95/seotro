# Bộ đọc Hmong nhanh thử nghiệm · Voice Studio Hmong 1.6.0

Lựa chọn này dùng **VITS để tạo lời Hmong**, sau đó dùng **OpenVoice V2 để chuyển chất giọng theo mẫu đã chọn**. Đây là bộ mặc định của tệp mở chính trong gói Windows 1.6.0; F5 vẫn có trong công cụ nâng cao. Chuyển chất giọng không bảo đảm sửa phát âm, thanh điệu, độ giống người nói hay cảm xúc như người thật. Giữ nguyên bộ phát âm Hmong bạn đã xác nhận. Mục tiêu một giờ lời đọc trong hai phút (30×) chưa đạt; chưa có phép đo GPU, và bản này không huấn luyện mô hình phát âm mới.

## Chọn bộ đọc

Trong gói Windows 1.6.0, đóng tool đang chạy rồi mở **`MO_VOICE_STUDIO_HMONG.bat`** ở ngoài cùng. Giao diện phải ghi **Hmong nhanh thử nghiệm**. Công cụ **`tools/MO_F5_HMONG.bat`** mở F5 để nghe so sánh. Đổi bộ mở rồi tạo tác vụ mới để nghe so sánh; không nối các đoạn của một bài đang dở bằng bộ khác.

Hai bộ đọc dùng cùng mẫu **hmong nam 2.MP3** và bản nữ rút gọn **hmong nữ 2(1).MP3**, cùng lời Hmong do bạn xác nhận. Hồ sơ giọng và lịch sử được giữ. Bộ mới tạo lời trước rồi chuyển chất giọng; mẫu ngắn không huấn luyện lại một mô hình phát âm Hmong riêng.

Lần chuẩn bị đầu cần Internet và khoảng **580 MB** tệp mô hình, ngoài dung lượng cho ứng dụng, bộ chạy và audio xuất. Chỉ bộ đang chọn cần tải mô hình của nó; dùng riêng bộ thử nghiệm không yêu cầu tải thêm F5 1,4 GB. Launcher kiểm tra checksum trước khi sử dụng. Khi chuẩn bị xong, suy luận chạy cục bộ, offline và không gửi bản thu lên dịch vụ suy luận ngoài. Đóng cửa sổ đang chạy để dừng tool.

Không có lựa chọn 4/8/16/32 bước trong bộ này. Các số đó thuộc F5; giao diện ẩn chúng khi chọn bộ thử nghiệm. Bộ mới dùng FP32; nếu từng đặt `HMOOB_PRECISION=int8` cho F5, hãy bỏ biến đó hoặc đặt `HMOOB_PRECISION=auto` hay `fp32` trước khi mở bộ thử nghiệm. Nhập/xuất TXT/SRT/WAV/MP3, hai giọng mặc định, giọng cá nhân, nhấn cụm, khoảng nghỉ và sắc thái vẫn dùng chung. Sắc thái chỉ điều chỉnh nhịp/cường độ, không phải cảm xúc được huấn luyện trong mô hình.

Bộ nhanh giữ các chữ và dấu thanh điệu RPA; dấu gạch nối được đưa thành ranh giới từ lúc tạo tiếng, trong khi kịch bản gốc vẫn giữ nguyên. Các ký tự khác được kiểm tra theo từ vựng mô hình; viết số bằng chữ Hmong và thay dấu chưa hỗ trợ khi tool báo lỗi. Tool giữ chữ cuối ghi thanh điệu và không tự bỏ ký tự để tạo audio.

Bộ mới thử gắn dấu WavMark lên đoạn có ít nhất 16.000 mẫu âm thanh. Đoạn ngắn hơn, khoảng 0,726 giây ở 22.050 Hz, bỏ qua bước này. Chưa kiểm chứng khả năng nhận diện dấu sau chỉnh nhịp, resample, ghép SRT hay xuất MP3. Không coi mọi tệp xuất là đã có dấu hoặc chắc chắn được máy dò nhận diện; audio do tool tạo vẫn là audio AI.

## Kịch bản dài và nhiều nhân vật

TXT Hmong của bản 1.6.0 nhận tối đa một triệu ký tự, trên 20.000 ký tự tự lập chương/phần để xuất ZIP; chế độ này không ghép video hoặc chia chương SRT. SRT hỗ trợ gán giọng Hmong theo nhân vật ở từng cue; tên nhân vật không trở thành lời đọc. Bộ nhanh giữ tối đa 16 mẫu tham chiếu gần dùng theo thứ tự LRU, loại mẫu ít dùng nhất khi đầy và dùng chung model đã nạp. Bộ đệm chỉ tránh tính lại tham chiếu khi đổi giọng; không xác nhận tốc độ cố định, phát âm hay độ giống giọng tốt hơn. Tạo bài dài vẫn cần đủ thời gian và dung lượng, và nên nghe thử trước khi tạo toàn bộ.

## Chạy từ mã nguồn

Cần toàn bộ kho mã nguồn, FFmpeg và môi trường Hmong đã cài theo [HMONG-README.md](../HMONG-README.md). Trên Linux:

```sh
cd voice-studio
HMOOB_BACKEND=native .venv-hmong/bin/python hmong_launcher.py
```

Trên Windows, từ thư mục `voice-studio` và môi trường Hmong đã cài:

```bat
set "HMOOB_BACKEND=native"
.venv-hmong\Scripts\python.exe hmong_launcher.py
```

Đặt `HMOOB_BACKEND=f5`, hoặc bỏ biến này, để về F5. `--setup-only` chuẩn bị đúng bộ đang chọn rồi thoát. `--check` chỉ kiểm tra tệp đã lưu, không tải thêm và không tạo audio; thiếu mô hình trước lần chuẩn bị đầu sẽ báo chưa sẵn sàng. Có thể chỉ định `VOICE_STUDIO_DATA_DIR` để dùng thư mục dữ liệu riêng, nhưng không dùng chung dữ liệu với bản Voice Studio tiếng Việt.

Bộ CPU có sẵn trong ZIP. Nếu dùng NVIDIA, đóng tool rồi chạy `tools/install_hmong_cuda.bat` trước khi mở lại `MO_VOICE_STUDIO_HMONG.bat`. Bộ GPU cài riêng và kiểm tra tính toán CUDA thật; phép kiểm tra này chưa chứng minh tốc độ hoặc chất lượng suy luận. Đặt `HMOOB_DEVICE=cpu` để chọn CPU rõ ràng. Tốc độ luôn phụ thuộc phần cứng và độ dài nội dung.

## Nghe đối chiếu và đo tốc độ

Bấm **Đo tốc độ và thử 6 từ Hmong** để tạo câu có `ua`, `thaj`, `qab`, `faib`, `rov`, `ris`. Nghe tệp MP3/WAV đã tải nếu trình phát trong trình duyệt không phát được. Thử cả nam và nữ; giữ nguyên chữ RPA và chữ cuối ghi thanh điệu khi đối chiếu. Việc lời mẫu đúng không xác nhận mọi câu do AI tạo đã đúng.

Báo cáo tốc độ cần tính toàn bộ thời gian tạo lời, chuyển chất giọng và xuất audio. Khoảng nghỉ do tool chèn và các khoảng trống trên timeline không được tính thành lời đọc để đạt mục tiêu. Mẫu ngắn không chứng minh tốc độ duy trì một giờ. Chỉ một lượt thực sự tạo ít nhất 3.600 giây đoạn lời đọc trong tối đa 120 giây mới có thể xác nhận mục tiêu 30×; hiện chưa đạt điều kiện này. Xem kết quả thực tế được ghi riêng trong [VALIDATION-HMONG.md](../VALIDATION-HMONG.md).

## Nguồn mô hình và giấy phép

Nguồn trọng số VITS Hmong là [leejnus/HmongTTS](https://huggingface.co/spaces/leejnus/HmongTTS); nguồn mã VITS là [jaywalnut310/vits](https://github.com/jaywalnut310/vits), nguồn OpenVoice V2 là [MyShell OpenVoice](https://github.com/myshell-ai/OpenVoice). Các tệp mô hình cần thiết, revision và SHA256 được ghi cụ thể trong `hmong_native_models.py` và được tải bằng `prepare_hmong_native.py`, gồm cả thành phần WavMark của bộ chuyển giọng. Nguồn và giấy phép mã được lưu trong `hmong_native_vendor/UPSTREAM.json` cùng các tệp giấy phép. Quá trình chuẩn bị không tắt TLS hoặc bỏ kiểm tra checksum để vượt lỗi tải.

**Trọng số không được đóng trong ZIP.** Kho Hmong VITS chưa nêu giấy phép rõ ràng cho trọng số; giấy phép của OpenVoice hoặc mã ứng dụng không tự cấp quyền cho mô hình Hmong đó. Cần kiểm tra điều kiện của từng nguồn trước khi phân phối lại hay sử dụng thương mại. Tải thành công và checksum đúng chỉ xác nhận đúng tệp, không xác nhận quyền sử dụng hoặc phát âm chuẩn.

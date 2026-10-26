# Bộ đọc Hmong nhanh thử nghiệm · Voice Studio Hmong 1.6.5

Lựa chọn này dùng **VITS để tạo lời Hmong**, sau đó dùng **OpenVoice V2 để chuyển chất giọng theo mẫu đã chọn**. Đây là bộ mặc định của tệp mở chính trong gói Windows 1.6.5; F5 vẫn có trong công cụ nâng cao. Chuyển chất giọng không bảo đảm sửa phát âm, thanh điệu, độ giống người nói hay cảm xúc như người thật. Giữ nguyên bộ phát âm Hmong bạn đã xác nhận. Mục tiêu một giờ lời đọc trong hai phút (30×) chưa đạt; chưa có phép đo GPU, và bản này không huấn luyện mô hình phát âm mới.

## Chọn bộ đọc

Trong gói Windows 1.6.5, đóng tool đang chạy rồi mở **`MO_VOICE_STUDIO_HMONG.bat`** ở ngoài cùng. Giao diện phải ghi **Hmong nhanh thử nghiệm**. Công cụ **`tools/MO_F5_HMONG.bat`** mở F5 để nghe so sánh. Đổi bộ mở rồi tạo tác vụ mới để nghe so sánh; không nối các đoạn của một bài đang dở bằng bộ khác.

Hai bộ đọc dùng cùng mẫu **hmong nam 2.MP3** và bản nữ rút gọn **hmong nữ 2(1).MP3**, cùng lời Hmong do bạn xác nhận. Hồ sơ giọng và lịch sử được giữ. Bộ mới tạo lời trước rồi chuyển chất giọng; mẫu ngắn không huấn luyện lại một mô hình phát âm Hmong riêng.

Lần chuẩn bị đầu cần Internet và khoảng **580 MB** tệp mô hình, ngoài dung lượng cho ứng dụng, bộ chạy và audio xuất. Chỉ bộ đang chọn cần tải mô hình của nó; dùng riêng bộ thử nghiệm không yêu cầu tải thêm F5 1,4 GB. Launcher kiểm tra checksum trước khi sử dụng. Khi chuẩn bị xong, suy luận chạy cục bộ, offline và không gửi bản thu lên dịch vụ suy luận ngoài. Đóng cửa sổ đang chạy để dừng tool.

Không có lựa chọn 4/8/16/32 bước trong bộ này. Các số đó thuộc F5; giao diện ẩn chúng khi chọn bộ thử nghiệm. Bộ mới dùng FP32; nếu từng đặt `HMOOB_PRECISION=int8` cho F5, hãy bỏ biến đó hoặc đặt `HMOOB_PRECISION=auto` hay `fp32` trước khi mở bộ thử nghiệm. Nhập/xuất TXT/SRT/WAV/MP3, hai giọng mặc định, giọng cá nhân, nhấn cụm, khoảng nghỉ và sắc thái vẫn dùng chung. Sắc thái chỉ điều chỉnh nhịp/cường độ, không phải cảm xúc được huấn luyện trong mô hình.

Bộ nhanh giữ các chữ và dấu thanh điệu RPA; dấu gạch nối được đưa thành ranh giới từ lúc tạo tiếng, trong khi kịch bản gốc vẫn giữ nguyên. Cặp mốc phụ đề và chỉ số cue được loại khỏi lời đọc trước khi kiểm tra ký tự; số trong câu vẫn được giữ và các số đếm được hỗ trợ được chuyển sang lời Hmong. Cách viết số hay ký tự khác chưa hỗ trợ được báo rõ để sửa. Tool giữ chữ cuối ghi thanh điệu và không tự bỏ nội dung để tạo audio.

Tác vụ mới thử gắn dấu WavMark lên đoạn có ít nhất một giây âm thanh (22.050 mẫu ở 22.050 Hz), đưa giây đầu về 16.000 Hz trước khi gắn dấu rồi chỉ cộng phần dấu vào tín hiệu gốc. Đoạn ngắn hơn một giây bỏ qua bước này. Tác vụ cũ tiếp tục giữ ngưỡng và cách xử lý cũ để không trộn các đoạn khi tiếp tục. Chưa kiểm chứng khả năng nhận diện dấu sau chỉnh nhịp, resample, ghép SRT hay xuất MP3. Không coi mọi tệp xuất là đã có dấu hoặc chắc chắn được máy dò nhận diện; audio do tool tạo vẫn là audio AI.

## Mẫu ngoài và lời có mốc phụ đề

Bộ nhanh nhận mẫu một người nói bằng **Hmong hoặc bất kỳ ngôn ngữ khác** để chuyển chất giọng sang lời Hmong. Tệp đầu vào dài 3–30 giây, tối đa 20 MB; chọn 3–8 giây nói rõ, không nhạc/tiếng chồng. Lời trong đoạn mẫu là tùy chọn, không phải nội dung được đọc, không cần dịch thành Hmong. Ngôn ngữ lời đọc đầu ra vẫn là Hmong Trắng RPA. F5 nâng cao tiếp tục yêu cầu mẫu cùng lời Hmong khớp đúng đoạn. Không có bảo đảm chuyển đúng toàn bộ giọng vùng, cách diễn xuất hay độ giống 100% từ một đoạn ngắn.

Sau khi lưu, chọn tên hồ sơ trong nơi tạo giọng và tạo câu mới để nghe; phát mẫu chỉ nghe bản thu gốc. Tác vụ giữ danh tính mẫu đã chọn; không sửa/xóa hồ sơ mà một bài dở cần dùng khi muốn tiếp tục. Chuyển giọng không huấn luyện lại phát âm Hmong.

Dòng `00:04:28,533 --> 00:04:29,333` được hiểu là khoảng thời gian 0,8 giây ở phút thứ tư, không đọc các chữ số đó. Ở TXT, dán SRT sẽ chỉ đọc nội dung liên tục; ở SRT, giữ mốc, căn nhịp trong giới hạn và báo rõ khi không vừa thay vì cắt lời. Số có nghĩa trong nội dung không bị xóa. Chi tiết nhập/xuất và các biến thể ở [hướng dẫn đầy đủ](HUONG-DAN-HMONG.md#4-nhập-và-xuất-txt-srt-wav-mp3).

## Kịch bản dài và nhiều nhân vật

TXT Hmong của bản 1.6.5 nhận tối đa một triệu ký tự, trên 20.000 ký tự tự lập chương/phần để xuất ZIP; chế độ này không ghép video hoặc chia chương SRT. SRT hỗ trợ gán giọng Hmong theo nhân vật ở từng cue; tên nhân vật không trở thành lời đọc. Bộ nhanh giữ tối đa 16 mẫu tham chiếu gần dùng theo thứ tự LRU, loại mẫu ít dùng nhất khi đầy và dùng chung model đã nạp. Bộ đệm chỉ tránh tính lại tham chiếu khi đổi giọng; không xác nhận tốc độ cố định, phát âm hay độ giống giọng tốt hơn. Tạo bài dài vẫn cần đủ thời gian và dung lượng, và nên nghe thử trước khi tạo toàn bộ.

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


## Giọng có sẵn và SRT chỉ đọc lời trong 1.6.5

Native có thêm `hmong-female-3` và `hmong-ngoc-huyen`, lấy từ hai MP3 người dùng gửi, với WAV tham chiếu PCM16 mono 24 kHz 7,44/7,78 giây. `additional-voices.json` ghi SHA nguồn, SHA đoạn mẫu và gain cố định. MP3 gốc giữ nguyên. Không có transcript được xác nhận cho hai mẫu này; tham chiếu chỉ điều kiện âm thanh, không tự tạo lời. Hai mẫu chỉ hiện với Native; bộ F5 giữ hai giọng có lời Hmong đã xác nhận trước đó.

`subtitle_timing=False` cho SRT độc lập giữ nguồn nguyên bản nhưng chỉ tạo lời liên tục, xuất SRT theo âm thanh thực. Mặc định API/worker cũ vẫn căn mốc; giao diện tạo giọng Hmong chủ động chọn đọc lời. Lồng tiếng video và phân vai yêu cầu giữ mốc. Lựa chọn mặc định được lưu riêng với snapshot tác vụ: đổi mặc định không đổi giọng của tác vụ đã xếp hàng.

Nhân bản Native gợi ý cửa sổ có năng lượng tiếng nói 3–8 giây trong bản thu 3–30 giây, không nhận dạng ngôn ngữ/lời hay chứng nhận độ giống. Decode được kiểm tra ở float trước khi giảm gain và chuyển PCM16 để tránh tự tạo clipping; tệp nguồn người dùng không bị thay. Các mẫu mặc định nhận diện bằng SHA dùng đúng WAV đã kiểm chứng khi nhập lại chính nguồn đó.

## Xử lý âm thanh trong 1.6.5

Tác vụ Native mới dùng `hmong_audio_profile=clear-v1`; tác vụ lưu từ trước không có trường này tiếp tục đường `legacy-v1`. Cache synth và danh tính checkpoint gắn với profile, tránh trộn âm thanh cũ và mới. Không đổi trọng số VITS/OpenVoice, tau, chữ RPA, cao độ hoặc bản thu gốc.

WavMark nhận đúng 16.000 mẫu ở 16 kHz. Chỉ phần sai khác do marker được resample về 22,05 kHz rồi cộng vào âm thanh gốc, có fade 20 ms ở hai đầu; không low-pass toàn bộ lời nói. Native giữ WAV trung gian FLOAT trước bước giới hạn đỉnh/xuất PCM16. Nhánh `atempo` tắt auto-level của limiter để không tăng thêm âm lượng ngoài thiết lập. Các sửa này xử lý lỗi tín hiệu; chưa chứng nhận mọi từ đúng hoặc giọng giống mẫu hoàn toàn.

Bốn MP3 trong `reports` là đầu ra thật của tool. Hai tệp mới `Ngoc-Huyen-preview.mp3` và `Hmong-female-3-preview.mp3` được đối chiếu SHA256 với tác vụ clear-profile và mẫu đã đóng băng. ASR Hmong cục bộ đã không vượt qua phép hiệu chuẩn trên lời mẫu do người dùng xác nhận nên không được dùng làm bằng chứng phát âm chuẩn.

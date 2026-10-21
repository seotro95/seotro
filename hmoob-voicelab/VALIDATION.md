# Kết quả kiểm tra Hmoob VoiceLab

Máy Linux, Python 3.12. Lượt kiểm tra ngày 21/10/2026 dùng F5-TTS 1.1.22, PyTorch/torchaudio 2.6.0+cpu, không có CUDA khả dụng.

## Đã xác minh

- 59 kiểm thử unittest đạt ngày 21/10/2026, không bỏ qua: giới hạn ký tự, Unicode/CRLF, gom câu, ghép chương, phục hồi lỗi, dừng/tiếp tục, khôi phục sau restart, khóa dữ liệu, HTTP, WAV/ZIP, mẫu tham chiếu mặc định và kiểm tra tính toàn vẹn mô hình/bộ tải. `node --check web/app.js`, `git diff --check` và kiểm tra tương thích 150 gói thư viện đều đạt. Một cảnh báo deprecation `audioop` từ pydub trên Python 3.12.
- Kiểm thử bổ sung xác minh việc tiếp tục sửa WAV hỏng/thiếu/rỗng, giữ nguyên byte và thời gian sửa đổi của checkpoint còn tốt, giữ lời/mẫu/thiết lập đã cố định và cho phép tiếp tục sau khi tạo lại bị lỗi.
- Kiểm thử tốc độ dùng bộ chia/tính thời lượng/cắt waveform thật của F5-TTS 1.1.22 với mô hình và vocoder kiểm thử. Hai câu ngắn dưới 10 byte UTF-8 tạo thời lượng tương ứng 0,5× / 1× / 2×, giữ đúng 16 bước. Đây là kiểm tra điều khiển nhịp, không chứng minh chất lượng giọng. Không sửa thư viện F5-TTS đã cài.
- Tác vụ **đủ 1.000.000 ký tự** đi qua HTTP, hàng đợi và bộ ghép đầu ra: 3.334 lần gọi engine kiểm thử, hoàn tất một triệu ký tự, tổng frame WAV đúng bằng tổng frame của các đoạn. Engine ở kiểm thử trả waveform nhân tạo; đây không phải bản đọc Hmong.
- Mỗi lần polling chỉ lấy trạng thái gọn, không gửi lại toàn bộ kịch bản. Kiểm tra nhận 1.000.001 ký tự trả lỗi trước khi khởi chạy mô hình.
- FFmpeg thật trích mẫu 3 giây từ bản MP3 có sẵn; lời tham chiếu và WAV được cố định vào từng tác vụ.
- Cài và import thật F5-TTS 1.1.22, PyTorch, torchaudio, Soundfile; thử WAV thành tensor 24 kHz và tái sử dụng tensor. Kiểm tra HTTP với mô hình thật đã chuẩn bị: `/api/status` trả 200, `engine.ready=true`, FFmpeg có sẵn. Lượt kiểm tra ban đầu diễn ra trước khi nhập lời hai giọng mặc định.
- Chromium ở lượt kiểm tra trước: giao diện máy tính/điện thoại, một triệu ký tự ASCII/Unicode, vượt giới hạn, tạo/dừng/tiếp tục và lịch sử bằng API kiểm thử; giao diện với máy chủ thật báo đúng thiếu mô hình và chưa có lời mẫu tại thời điểm đó. Không lỗi JavaScript hoặc tràn ngang trong các lượt thử.
- Thử bộ chia đoạn với một triệu ký tự liên tục, nhiều câu ngắn và Unicode: khoảng 0,05 giây trên máy này. Đây chỉ là **thời gian chia đoạn**, không phải tốc độ inference.

## Suy luận thật ngày 21/10/2026

- Lỗi mạng CONNECT 403 của lượt trước đã được giải quyết trong môi trường hiện tại. `setup_voice.py` tải đủ bốn tệp qua HTTPS và xác minh checksum; suy luận dùng toàn bộ tệp cục bộ với `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, trong tiến trình không có quyền mạng.
- F5-Hmong: repository `Pakorn2112/F5TTS-Hmong`, commit `c50fc0cc991bc0c4f22d86c7a6152730c667c0d5`; checkpoint SHA-256 `0b5e23fd6c9c1519f38195cbe0fdca3402beb75026b22ace483886529add3288`. Vocos: `charactr/vocos-mel-24khz`, commit `0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21`. Manifest đầy đủ lưu cục bộ tại `.data/models/verified-models.json`; không đưa trọng số vào Git.
- Mẫu công khai được ghép sẵn với lời trong [app.py upstream](https://github.com/YangNobody12/F5-TTS-Hmong/blob/ec21db33d2dea156840bd6ff03a2087e950b067e/app.py). [WAV nguồn](https://raw.githubusercontent.com/YangNobody12/F5-TTS-Hmong/ec21db33d2dea156840bd6ff03a2087e950b067e/src/f5_tts/infer/examples/thai_examples/ref_hmn.wav) dài 3,861 giây; SHA-256 `136741deb61d421e1f44046478e5757a322125e0bdbb112f05c42446fa731470`. Lời: `Kuv pom ib tug npauj npaim zoo nkauj heev li.`. Chuyển sang mono PCM16 24 kHz trước khi chạy. Không dùng hoặc gửi hai mẫu giọng của người dùng ra ngoài.
- Văn bản mới: `Nyob zoo. Kuv yog Hmoob. Hnub no peb kawm lus Hmoob ua ke.`. `SpeechEngine` thật chạy qua `JobManager`, hoàn tất 100%, xuất chương WAV **113.664 frame / 24.000 Hz = 4,736 giây**, PCM16 mono, dữ liệu hữu hạn và khác im lặng. SHA-256 WAV `b882a54a3ab5444fd940b8c8222cd135192f1023b2a865c5ab6973df63f41de5`.
- Nạp mô hình **8,143 giây**, sau đó suy luận và ghi checkpoint **69,657 giây**, chế độ fast 16 bước, nhịp 1×, CPU. Mô hình đã nạp trước khi bấm giờ tác vụ; đây là một câu ngắn trên máy cloud, không phải phép đo Windows hoặc cam kết tốc độ cho văn bản dài.

## Hai giọng mặc định được người dùng xác nhận

- Hai MP3 người dùng tải lên khớp nguyên byte với các mẫu có sẵn, không thay đổi âm thanh gốc. FFmpeg trích WAV mono PCM16 24 kHz đúng thời lượng chọn.
- Nữ **0–5,30 giây**: `tsis pom muaj neeg lawm ces, nws thiaj li los ze ze ntawm lawv lub tsev.`
- Nam **0–4,50 giây**: `hais tias ces Nraug Xyooj thiaj li tawm tau mus hauv kev mus lawm.`
- Mốc đầu tiên được chọn trong khoảng ngắt âm thanh; sau đó người dùng nghe và xác nhận **đúng cả hai đoạn**. Không coi phát hiện khoảng lặng là căn lời tự động. Chỉ chuẩn hóa dấu kết câu nữ thành dấu chấm, giữ nguyên các từ đã cung cấp.
- Lời/mốc đã lưu ở dữ liệu cục bộ và trong metadata mẫu mặc định. Thay đổi người dùng lưu riêng vẫn được ưu tiên; tác vụ tiếp tục dùng bản chụp lời/mẫu tại lúc tạo.
- Năm kiểm thử mới xác minh dữ liệu mới nhận đúng hai mẫu mặc định đã sẵn lời, thiết lập riêng được giữ qua lần mở sau và ưu tiên hơn metadata, từ chối mốc/lời mặc định không hợp lệ, giọng chưa cấu hình vẫn bị chặn, và FFmpeg trích đúng độ dài trong bản chụp âm thanh/lời không đổi khi sửa thiết lập về sau. API `/api/voices` xác nhận cả hai giọng mặc định có `reference_ready=true`.
- Hai tác vụ thật dùng `Voices.snapshot` và `JobManager` với hai mẫu đã xác nhận, chạy ngoại tuyến trên CPU, fast 16 bước, nhịp 1×. Cùng văn bản mới `Nyob zoo. Kuv yog Hmoob. Hnub no peb kawm lus Hmoob ua ke.`. Cả hai hoàn tất 100%, lưu ở Lịch sử cục bộ của tool, xuất WAV PCM16 mono 24 kHz và bản MP3 để nghe thử.

| Giọng | Frame WAV | Thời lượng | Thời gian suy luận và ghi checkpoint |
| --- | ---: | ---: | ---: |
| Nữ | 99.072 | 4,128 giây | 88,498 giây, có nạp mô hình |
| Nam | 91.648 | 3,819 giây | 73,493 giây, dùng lại mô hình đã nạp |

- SHA-256 WAV nữ: `73597999a94130ed6c05ad1f850009133bbc79bfca5942bbb5d77a678412bd80`; nam: `5213a37a7ea7d9223db558e4becb8f995b0d9db5c2b9f40820f80135a7100d14`. Các phép đo câu ngắn này không phải tốc độ bảo đảm cho máy khác hoặc văn bản dài. Người dùng đã xác nhận đoạn tham chiếu, chưa đánh giá hai bản đọc AI mới.

## Chưa xác minh / đang chờ

- Bản 1.1 thêm bộ khởi chạy tự chuẩn bị: phát hiện runtime/FFmpeg đi kèm, chuẩn bị riêng phần còn thiếu, kiểm tra thư viện native và model, bảo toàn dữ liệu cũ. Mười kiểm thử bootstrap đạt, gồm khởi chạy không cài/tải lại, lần đầu chỉ thiếu model, môi trường Python không tương thích, dữ liệu được giữ, và biến Python kế thừa không làm sai runtime. Hai kiểm thử mới đảm bảo bộ tải chỉ dùng đúng commit mô hình đã kiểm thử. Bộ kiểm thử ứng dụng tổng cộng 59 bài đạt trên Linux.
- Ba kiểm thử đóng gói đạt trên Linux: nguồn allowlist không mang theo dữ liệu/môi trường, kiểm tra đường dẫn FFmpeg và từ chối asset liên kết. Quy trình Windows mới phải qua kiểm thử native, suy luận thật nam/nữ ngoại tuyến sau khi chuyển thư mục, tải WAV/ZIP và mở lại lịch sử, kiểm tra lần đầu chỉ cần tải model, rồi quét Defender cả thư mục lẫn ZIP trước khi cung cấp artifact. Báo cáo thực thi được đính kèm riêng trong Actions; không suy ra kết quả Windows từ các kiểm thử Linux.

- Chưa có người nói Hmong đánh giá phát âm/phương ngữ Hmong Trắng hoặc độ giống giọng. WAV hợp lệ không chứng minh nội dung được đọc đúng. Chưa thử suy luận thật với một triệu ký tự hoặc nhiều giờ liên tục.
- Chưa thử Windows BAT, CUDA/MPS hoặc một task mới sau khi publish môi trường.

Bản nháp cấu hình môi trường và snapshot được publish là hai trạng thái khác nhau. Kết quả trên không chứng minh publish hoặc khôi phục trong task mới đã thành công.

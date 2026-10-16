# Voice Studio 2.8 — Xuất video đến 4K, TXT/SRT và sửa phụ đề trực tiếp

Giao diện tiếng Việt cho chuyển văn bản thành lời nói, hồ sơ nhân bản giọng từ mẫu, thư viện giọng, hàng đợi, nghe lại và tải WAV/MP3. Tạo giọng cục bộ không cần API key. AI viết kịch bản mặc định dùng Ollama trên máy, không cần tài khoản hoặc API key. OpenAI/Gemini là tùy chọn nâng cao và vẫn yêu cầu khóa riêng.

## Chức năng

- Tiếng Việt/Anh: **VieNeu-TTS v3 Turbo**, chạy ONNX trên CPU.
- Anh, Nhật, Hàn, Trung, Pháp, Đức, Tây Ban Nha, Ý, Bồ Đào Nha, Nga: **Qwen3-TTS 0.6B CustomVoice**; nhân bản dùng **0.6B Base**.
- Hai lựa chọn English US/UK dùng chung mô hình ngôn ngữ English. Âm sắc/giọng vùng phụ thuộc giọng gốc hoặc mẫu thu, không được bảo đảm chỉ bằng lựa chọn ngôn ngữ. Với UK, nên thêm mẫu được phép sử dụng của người nói giọng Anh.
- Nhập mẫu âm thanh 3–30 giây, tối đa 20 MB. VieNeu thực tế dùng tối đa khoảng 8 giây tham chiếu. Đoạn sạch, một người nói, không nhạc cho kết quả tốt hơn.
- Lưu mẫu là đăng ký hồ sơ tham chiếu, không huấn luyện lại mô hình. Nhân bản thực sự được thực hiện khi tạo lời đọc mới. Chỉ dùng mẫu của chính bạn hoặc đã được chủ giọng cho phép.
- Điều chỉnh tốc độ 0.7–1.4×, xuất WAV hoặc MP3 192 kbps. Lịch sử lưu cục bộ; xóa mẫu và bản thu riêng.
- Tối đa 4 tác vụ chờ/chạy; chạy tuần tự các tác vụ; mỗi tác vụ Nano có thể chọn tối đa hai luồng tạo đoạn. Nhận tối đa **200.000 ký tự**, chia câu/đoạn tối đa 240 ký tự, nạp mô hình một lần và giữ trong RAM để tái sử dụng giữa các tác vụ cùng giọng/ngôn ngữ/chế độ. Đổi cấu hình sẽ thay mô hình cũ; Dừng hoặc tắt ứng dụng sẽ giải phóng tiến trình. PCM được ghi theo khối trên đĩa, không giữ bản thu nhiều giờ trong RAM.
- Bản thu tối đa **180 phút (3 giờ)**, tính cả khoảng nghỉ và tốc độ đã chỉnh. Nếu đạt giới hạn trước khi hết lời, giao diện báo rõ còn nội dung chưa đọc. Không kéo giãn/chèn im lặng cho đủ 3 giờ.
- Dừng/tiếp tục trong Lịch sử: lưu từng đoạn, tiếp tục dùng lại các đoạn đã hoàn tất. Khởi động lại máy đánh dấu tác vụ gián đoạn; có thể tiếp tục. Giới hạn xử lý một lượt là 7 ngày, tách biệt với thời lượng âm thanh 3 giờ.
- Nhập kịch bản `.txt`, đánh dấu **từ cần nhấn** và `[pause=1.5]`; nhịp đọc Tự nhiên/Kể chuyện/Tin tức/Thư giãn/Sôi nổi điều chỉnh tốc độ và khoảng nghỉ. Nhấn từ dùng tốc độ chậm hơn và tăng âm lượng nhẹ có limiter. Đây là điều khiển nhịp/âm lượng; mô hình hiện tại không hỗ trợ đầy đủ mô tả cảm xúc tự do.


## Cập nhật từ bản trước (Windows)

1. Tắt Voice Studio bằng Ctrl+C trong cửa sổ đang chạy.
2. Tải ZIP mới từ GitHub, chép các tệp trong thư mục `voice-studio` mới đè vào thư mục cũ. **Giữ nguyên `.data` và `.venv`** để không mất mô hình, mẫu giọng và bản thu. Không xóa thư mục cũ rồi giải nén lại nếu chưa sao lưu dữ liệu.
3. Bản 2 dùng các thư viện đã có ở bản trước; chạy `start.bat`. Nếu thư viện thiếu, chạy lại `install.bat` và chụp lỗi cuối khi thất bại.
4. Muốn bật chế độ nhanh tiếng Việt, chạy thêm `download_fast_model.bat`. Chỉ khả dụng trên CPU được xác nhận có AVX-VNNI/AVX-512 VNNI. Nếu máy không hỗ trợ, dùng Tiêu chuẩn.

## Viết kịch bản không cần API key (mặc định)

1. Tải và cài **Ollama** từ https://ollama.com/download/windows. Mở Ollama sau khi cài.
2. Trong thư mục Voice Studio, chạy **`setup_local_writer.bat`**. Tệp này tải `qwen3:4b` về máy (vài GB), không đăng nhập và không cần API key. Cần Internet ở bước tải. Máy ít RAM có thể chạy `setup_local_writer.bat qwen3:1.7b` rồi chọn đúng tên model đó trong giao diện.
3. Chạy `start.bat`, mở **AI viết kịch bản**. Giữ lựa chọn mặc định **AI cục bộ · Ollama · Không cần key**.
4. Bấm **Kiểm tra AI**, chọn tên mô hình đã tải, nhập yêu cầu và bấm **Viết kịch bản**. Chọn **Đưa sang tạo giọng** hoặc **Thêm vào cuối kịch bản** sau khi sửa nội dung nếu cần.

Linux/macOS: cài Ollama theo hướng dẫn chính thức, chạy dịch vụ trên máy rồi chạy `ollama pull qwen3:4b`. API local cố định ở `127.0.0.1:11434`; Voice Studio không cho đổi sang máy chủ bên ngoài. Không dùng `:cloud` trong chế độ cục bộ. Mô hình local được gỡ khỏi RAM sau mỗi phản hồi để dành bộ nhớ cho tạo giọng. Mô hình 4B cần RAM trống và có thể mất vài phút trên CPU; bản 1.7B nhẹ hơn nhưng chất lượng thường thấp hơn. Không hứa chất lượng ngang ChatGPT/Gemini.

Đây là **Qwen qua Ollama**, không phải truy cập ChatGPT/Gemini miễn phí. Sau khi tải đầy đủ mô hình, phần viết có thể chạy không có Internet. Ứng dụng vẫn cần dịch vụ Ollama chạy nền. Nếu chưa cài/mở Ollama hoặc thiếu model, giao diện báo cách xử lý; không yêu cầu bạn nhập khóa cho chế độ này. Tạo giọng vẫn hoạt động nếu không dùng phần viết.

- Viết lời, viết lại/thêm nhịp đọc, lập dàn ý; chọn ngôn ngữ và thời lượng mục tiêu 1–180 phút. **Đưa sang tạo giọng** thay nội dung trình đọc; **Thêm vào cuối** nối tiếp nội dung đã có.
- Kịch bản dài cần viết tiếp từng chương bằng **Viết tiếp**; một phản hồi có giới hạn token, không được coi một đoạn ngắn là kịch bản đủ 3 giờ.

### Dịch vụ đám mây (không bắt buộc)

OpenAI và Gemini vẫn có trong danh sách cho người muốn dùng tài khoản API riêng. Khi chọn chúng, giao diện mới hiện ô API key. Khóa chỉ giữ trong RAM máy chủ đến khi tắt ứng dụng; không ghi ra Git, dữ liệu hay localStorage. Có thể dùng biến môi trường `OPENAI_API_KEY`, `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY`. Các lựa chọn này vẫn gửi chủ đề/nội dung tới nhà cung cấp khi bấm Viết, cần Internet và có thể tính phí; gói web không tự cấp hạn mức API. Chọn Ollama nếu muốn hoàn toàn không cần khóa. Model cloud mặc định `gpt-4.1-mini` / `gemini-2.5-flash` có thể đổi theo danh mục tài khoản.

## TXT / SRT, chọn giọng và tiến độ (bản 2.5)

- **Nhập TXT/SRT** trong cả mục Tạo giọng và Lồng tiếng video; tối đa 200.000 ký tự / tệp 2 MB, UTF-8 (có thể có BOM). Có chọn định dạng để dán trực tiếp lời TXT hoặc nội dung SRT. SRT phải có mốc `HH:MM:SS,mmm --> HH:MM:SS,mmm`, câu tăng dần, không chồng nhau, kết thúc trong 3 giờ; tối đa 10.000 câu. Thẻ HTML cơ bản được bỏ khỏi lời đọc.
- **Xuất TXT/SRT** ở editor và Lịch sử. TXT có thể xuất ngay; TXT sang SRT cần tạo giọng xong để lấy mốc thời gian thực từng đoạn đã đọc. Đây là mốc đoạn, không phải căn chính xác từng từ. SRT nhập sẵn có thể xuất lại trước khi tạo. Sau khi lồng tiếng xong, xuất SRT của tác vụ sẽ cộng thời điểm bắt đầu video. Nếu sửa nội dung TXT, phải tạo lại voice để xuất SRT mới khớp lời.
- SRT được đọc theo từng ô thời gian: chèn im lặng trước câu và ở cuối ô còn dư, không tự thêm nghỉ giữa các mảnh câu. Nếu âm thanh dài hơn ô, FFmpeg điều chỉnh nhịp từ bản gốc và đo lại, giới hạn **1,5×** so với lời đã tạo. Nếu vẫn không vừa, báo số câu cần chỉnh để người dùng nới mốc hoặc rút ngắn lời; không cắt mất lời hay đẩy lệch câu sau. Mốc SRT phải nằm trong giới hạn bản thu/video cộng thời điểm bắt đầu. SRT không tự nhận dạng hoặc dịch lời video và không khớp khẩu hình.
- **Chọn giọng ngay trong mục Lồng tiếng**: ngôn ngữ, nguồn AI/Windows, giọng cụ thể, số bước Nano và một/hai tiến trình. Tốc độ/nhịp đọc dùng thiết lập mục Tạo giọng. Có nút **Chỉ tạo voice WAV từ lời TXT/SRT**, dùng được ngay cả khi chưa tải video.
- **Giọng hệ thống Windows**: chọn nguồn Giọng có sẵn Windows. Chỉ dùng giọng SAPI đã cài và ứng dụng có thể truy cập, không tải mô hình AI hoặc dùng API key. Thêm giọng qua Settings > Time & language > Speech, rồi khởi động lại tool. Một số giọng OneCore/Narrator có thể không hiện trong SAPI; danh sách trống không có nghĩa máy không có bất kỳ giọng đọc nào. Phụ thuộc Windows PowerShell và .NET System.Speech có sẵn trên Windows desktop; không đổi execution policy. Trên Linux/macOS danh sách này trống; dùng giọng AI. Chất lượng/đa ngôn ngữ tùy giọng hệ thống đã cài, không cam kết ngang mô hình AI. Cần FFmpeg cho MP3/video và căn nhịp SRT.
- **Dừng** ngay trong mục Lồng tiếng áp dụng cả tạo voice, lồng tiếng và xuất video; giữ phần đã tạo để tiếp tục trong Lịch sử. Có **thanh và số %** ở cả mục Tạo giọng và Lồng tiếng: theo số đoạn đã xử lý, rồi theo timestamp thực do FFmpeg báo khi xuất. 100% chỉ khi tác vụ hoàn tất. Tải video có % truyền tệp riêng, sau 100% truyền tệp còn bước kiểm tra video. Các khoảng % là tiến độ theo giai đoạn, không phải ước lượng thời gian còn lại.

## Lồng tiếng video

1. Mở **Lồng tiếng video**, tải video MP4/MOV/MKV/WebM tối đa 2 GB / 3 giờ. Codec xuất nhanh được hỗ trợ: H.264, HEVC, AV1, MPEG-4, VP9; các codec khác cần chuyển sang H.264 trước. Video đã tải được giữ trên máy, có thể chọn lại sau khi mở ứng dụng.
2. Dán lời lồng tiếng tối đa **200.000 ký tự**, nhập TXT hoặc lấy nội dung từ mục Tạo giọng. Kiểm tra chính tả, tên riêng và cách viết số để mô hình phát âm đúng hơn.
3. Chọn giọng và ngôn ngữ trực tiếp ở mục **Lồng tiếng video**; nhịp đọc/tốc độ điều chỉnh ở mục **Tạo giọng**. Nano **8 bước** là lựa chọn cân bằng tốc độ/độ rõ; 16 bước ưu tiên chất lượng, 4 bước là bản nháp. Tăng tốc bằng hai tiến trình trên máy đủ CPU/RAM. Hỗ trợ cả giọng cá nhân và giọng quốc tế theo mô hình đã tải; không cam kết cùng tốc độ giữa các giọng.
4. Chọn thời điểm bắt đầu đọc (giây), tùy chọn giữ âm thanh gốc ở 15%, rồi bấm **Tạo giọng và lồng tiếng video**. Mặc định thay âm thanh gốc bằng giọng mới. Giữ âm thanh gốc không tách bỏ tiếng người nói cũ.
5. Xem trước và tải **MP4**, hoặc tải lại ở **Lịch sử**. Hình ảnh được sao chép nguyên codec, không mã hóa lại, để giảm thời gian và giữ chất lượng. Giọng mới được mã hóa AAC. Dừng sẽ dừng cả tạo giọng/ghép video; tiếp tục dùng lại đoạn đã tạo. Muốn xóa video gốc, xóa các tác vụ đang tham chiếu trong Lịch sử rồi bấm Xóa video gốc đã tải.

Đây là lồng tiếng theo kịch bản người dùng cung cấp: TXT đọc liên tục, SRT bám mốc từng câu từ thời điểm đã chọn. Chưa tự nhận dạng lời gốc, dịch hoặc khớp khẩu hình. Nếu lời dài hơn khoảng video còn lại, ứng dụng báo rõ và không xuất video bị cắt lời; cần rút ngắn kịch bản hoặc chỉnh tốc độ và tạo tác vụ mới. Nhịp đọc giữ theo thiết lập, không tự ép giọng đọc nhanh đến méo tiếng. Hãy nghe kiểm tra trước khi dùng; không bảo đảm mô hình phát âm đúng mọi từ. Tệp gốc và sản phẩm lưu cục bộ, cần đủ dung lượng đĩa. FFmpeg và FFprobe phải có trong PATH (cài cùng gói FFmpeg).

## Tối ưu mục tiêu 1 giờ voice trong 2 phút (bản 2.3)

- Chạy `download_turbo_model.bat` nếu chưa tải Nano. Trong giao diện bấm **Cấu hình ưu tiên tốc độ 30×**, rồi **Đo tốc độ máy bằng mẫu đọc**. Nút cấu hình chọn Minh Quân Nano tiếng Việt, 4 bước, WAV, nhịp tự nhiên 1×, không thêm nghỉ giữa câu; chọn hai luồng tạo đoạn trên máy từ 4 CPU logic. Không đổi nội dung trình soạn thảo khi đo mẫu.
- Mỗi luồng dùng một mô hình riêng, giữ trong RAM cho các lượt sau. Có thể đổi về một luồng nếu thiếu RAM hoặc máy chậm hơn khi chạy song song. Hai ONNX threads cho mỗi luồng là mặc định; nhiều threads hơn không mặc nhiên nhanh hơn. Mô hình chỉ tạo trước tối đa hai đoạn, ghép theo đúng thứ tự và giữ checkpoint để tiếp tục.
- **4 bước là chế độ bản nháp thử nghiệm**, có thể giảm độ rõ và tự nhiên. Chọn 8 hoặc 16 bước khi cần chất lượng cao hơn. Cấu hình này không áp dụng cho nhân bản hoặc giọng Qwen các ngôn ngữ khác; giọng Nano khác với Turbo.
- Bấm **Xem cấu hình máy** để xem CPU, RAM, NVIDIA và trạng thái PyTorch CUDA, không cần tự tìm trong Windows. Nano chạy CPU; thông tin NVIDIA không có nghĩa Nano tự chuyển sang GPU.
- Sau mỗi bản thu mới, ứng dụng hiện thời gian xử lý, thời lượng âm thanh, hệ số tốc độ và ước tính tạo 1 giờ. Phép đo tính cả nạp mô hình/xuất tệp, không tính chờ hàng đợi; lượt tiếp tục dùng cache không được dùng để ước tính tốc độ. Đo lần đầu và lần sau vì nạp mô hình làm kết quả khác nhau.
- Mục tiêu 30× phụ thuộc CPU, RAM, mô hình, văn bản, tải nền và định dạng. Không cam kết máy Windows của bạn đạt cùng kết quả máy thử. Xem kết quả và giới hạn trong `VALIDATION.md`. Nút Dừng vẫn tắt cả cây tiến trình, giữ các đoạn đã tạo.

## Tăng tốc bản 2.2 và nút Dừng

- **Tự động** là mặc định: dùng INT8 nếu giọng Turbo tiếng Việt có model và CPU VNNI phù hợp; nếu thiếu thì dùng FP32, giữ đúng giọng đã chọn. Qwen tự dùng CUDA khi bản PyTorch hỗ trợ; cài PyTorch CPU sẽ không tự có CUDA chỉ vì máy có NVIDIA.
- **Siêu nhanh Nano**: chạy `download_turbo_model.bat` một lần, sau đó bấm **Chọn giọng tiếng Việt siêu nhanh** hoặc chọn **Minh Quân · Siêu nhanh / Ái Hân · Siêu nhanh**. Nano chạy ONNX CPU 8 bước, chỉ giới thiệu cho tiếng Việt; chất lượng/âm sắc thấp hơn hoặc khác Turbo. Nano ở bản này dùng giọng có sẵn, không tự thay mô hình cho giọng nhân bản.
- **Giữ mô hình nóng**: cùng giọng và chế độ sẽ dùng lại tiến trình/mô hình, tránh nạp lại mỗi lần. Vì vậy lượt đầu/đổi giọng vẫn có thể chậm hơn. Đóng ứng dụng hoặc Dừng sẽ giải phóng bộ nhớ mô hình.
- Nhịp tự nhiên 1× dùng xử lý âm thanh trực tiếp thay cho mở FFmpeg ở từng câu. Nhấn/nghỉ vẫn giữ nguyên; đổi tốc độ/nhịp có thể cần FFmpeg. Chọn WAV để bỏ qua bước nén MP3 cuối.
- **Dừng tạo giọng** có ngay màn hình chính cạnh bản thu; không cần mở Lịch sử. Nút dừng tác vụ đang chọn, kết thúc cây tiến trình xử lý, giữ đoạn đã hoàn tất. Có thể Tiếp tục trong Lịch sử. Tác vụ khác trong hàng đợi vẫn được xử lý.
- Trong **AI viết · ChatGPT / Gemini**, có nút **Kết nối ChatGPT**, **Kết nối Gemini** và **AI cục bộ không cần key**. Cloud cần key hợp lệ/quyền API như trước; Ollama vẫn không cần key. Không tích hợp đăng nhập tài khoản web thay API.

Đo một mẫu khoảng 6 giây tiếng Việt trên CPU cloud 5 vCPU: bản trước khoảng 4,74–4,92 giây/lượt; bản mới Turbo FP32 lượt đầu 4,69 giây, lượt nóng 1,76 giây; Turbo INT8 2,85/1,34 giây; Nano giọng khác 1,05/0,74 giây. Số đo là mẫu ngắn, không phải cam kết cho Windows, phần cứng khác hoặc bản thu 3 giờ; Nano không phải so sánh ngang chất lượng. Chưa đo CUDA.

## Tạo nhanh và dự án 3 giờ

- **Tiêu chuẩn**: VieNeu FP32; Qwen 0.6B tự dùng CUDA khi PyTorch/CUDA phù hợp. Nạp một lần, dùng lại mã hóa mẫu trong cùng tác vụ; không nạp lại mô hình cho mỗi câu.
- **Nhanh**: VieNeu INT8 trên CPU VNNI (cần tải thêm mô hình); Qwen dùng giải mã xác định thay vì sampling. Tốc độ/chất lượng có thể khác theo phần cứng, văn bản và ngôn ngữ; không bảo đảm tăng tốc cố định.
- Không tăng tốc bằng cách chỉ nâng tốc độ phát giọng. Thanh Tốc độ thay đổi nhịp đọc, còn Chế độ xử lý thay đổi cách suy luận.
- Một WAV 3 giờ mono 24 kHz/16-bit khoảng 518 MB; các đoạn lưu để tiếp tục tốn thêm dung lượng. Dành **ít nhất khoảng 3 GB trống cho mỗi dự án dài**, ngoài dung lượng thư viện/mô hình.
- CPU yếu có thể mất nhiều giờ hoặc nhiều ngày để tạo bản thu 3 giờ. Nếu cần xuất nhiều bản dài nhanh, dùng NVIDIA GPU có PyTorch/CUDA phù hợp. Không để Windows ngủ giữa chừng; nếu bị gián đoạn, mở lại và dùng Tiếp tục trong Lịch sử.

## Yêu cầu

Python 3.12 được dùng trong môi trường phát triển; FFmpeg/ffprobe trong PATH. Khuyến nghị 16 GB RAM trở lên và khoảng 8–12 GB đĩa trống cho thư viện/mô hình. Máy cloud hiện tại có khoảng 33 GB RAM, 5 CPU và không có NVIDIA GPU. CPU có thể mất nhiều phút; tốc độ và độ tự nhiên cần đánh giá trên bản thu thực tế.

Lần tải đầu cần truy cập PyPI, kho PyTorch CPU và Hugging Face (`huggingface.co`, `*.huggingface.co`, `*.hf.co`). Sau khi chuẩn bị mô hình, tiến trình tạo giọng bật `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1`; văn bản/mẫu không gửi tới API giọng nói. Riêng mục AI viết gửi yêu cầu văn bản đến OpenAI/Gemini khi bạn sử dụng nó. Tệp được lưu trên **máy chạy ứng dụng**: nếu chạy cloud, đó là máy cloud, không phải máy tính cá nhân của bạn.

## Linux / macOS

Tại thư mục `voice-studio`, có thể chạy `bash install.sh` để cài thư viện trên Linux/macOS (Python 3.12 và FFmpeg phải có sẵn), hoặc dùng các lệnh sau:

```bash
python3.12 -m venv .venv
# Linux CPU:
.venv/bin/python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
# macOS: dùng pip install torch torchaudio từ PyPI thay cho dòng trên.
.venv/bin/python -m pip install -r requirements-qwen.txt
.venv/bin/python -m pip check

# Có thể chọn một mô hình trước; all tải cả ba.
.venv/bin/python prepare_models.py vieneu
.venv/bin/python prepare_models.py qwen
.venv/bin/python prepare_models.py qwen_clone
bash start.sh
```

Ứng dụng lắng nghe trên cổng **8770** của máy cục bộ. Không mở công khai ra Internet; bản này là studio cá nhân, chưa có đăng nhập/phân quyền nhiều người dùng.

## Windows

1. Cài Python 3.12 và FFmpeg, bảo đảm `py -3.12` và `ffmpeg` chạy được.
2. Chạy `install.bat` để cài bản CPU.
3. Chạy `download_models.bat` để tải mô hình.
4. Chạy `start.bat`.

Các tệp BAT được cung cấp để chạy trên máy Windows; không thể xác minh BAT bằng máy Linux hiện tại. Với NVIDIA GPU, cài PyTorch đúng phiên bản CUDA theo hướng dẫn chính thức của PyTorch thay bản CPU. Qwen tự chọn CUDA khi khả dụng; VieNeu trong bản này được cấu hình ONNX/CPU.

## Trong môi trường cloud hiện tại

Môi trường Python riêng nằm ở `/workspace/runtime/voice-studio-venv`:

```bash
cd /workspace/seotro/voice-studio
VOICE_STUDIO_PYTHON=/workspace/runtime/voice-studio-venv/bin/python bash start.sh
```

Dữ liệu mặc định nằm trong `.data/` (được Git bỏ qua): `models/cache`, `voices`, `audio`, `jobs`. Đặt `VOICE_STUDIO_DATA_DIR` thành đường dẫn khác **trước cả khi tải mô hình lẫn khi chạy server** nếu muốn di chuyển dữ liệu. `VOICE_STUDIO_THREADS=4` điều chỉnh số luồng cho tiến trình tạo giọng. Không xóa cache nếu muốn chạy offline. Các tệp `*.ready` chỉ được tạo sau khi script chuẩn bị mô hình hoàn tất; không tự tạo chúng để bỏ qua tải mô hình.

Nếu tốc độ tải Hugging Face chậm, có thể cài `hf_transfer==0.1.9` rồi chạy lệnh tải với biến `HF_HUB_ENABLE_HF_TRANSFER=1` (đã thử trên Linux trong môi trường này). Đây chỉ là tối ưu tải trọng số, không cần cho suy luận.

## Sử dụng

1. Chọn ngôn ngữ và giọng có sẵn, nhập văn bản đúng ngôn ngữ (ứng dụng không tự dịch) và bấm **Tạo giọng nói**.
2. Trong **Nhân bản giọng nói**, đặt tên, chọn ngôn ngữ mẫu, tải bản thu và xác nhận quyền sử dụng. Với Qwen, nhập chính xác lời nói trong mẫu để cải thiện độ bám giọng; nếu bỏ trống, dùng speaker embedding với chất lượng có thể thấp hơn.
3. Trong **Thư viện giọng**, bấm **Sử dụng giọng**. Hồ sơ cá nhân hiện được giới hạn ở ngôn ngữ đã đăng ký.
4. Theo dõi **Lịch sử bản thu**, nghe và tải xuống sau khi hoàn tất. Nếu khởi động lại server khi đang tạo, tác vụ được đánh dấu gián đoạn thay vì chờ mãi.

Không có mô hình nào bảo đảm sao chép chính xác 100% một giọng thật. Thiết kế giọng hoàn toàn mới bằng mô tả văn bản, fine-tune, chỉnh sửa timeline và chạy nhiều người dùng chưa được triển khai.

## Kiểm thử

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests
```

Kiểm thử ứng dụng dùng FFmpeg thật cho nhập/kiểm tra mẫu; phần tạo giọng trong unit test dùng mock và không chứng minh chất lượng mô hình. Xem `VALIDATION.md` cho kết quả thực thi trong môi trường này. Nhật ký lỗi suy luận nằm trong `.data/jobs/<id>.log`; không đưa dữ liệu giọng cá nhân lên Git.

## Mô hình và giấy phép

- VieNeu: https://github.com/pnnbao97/VieNeu-TTS
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
- Các trọng số được tải từ kho chính thức tương ứng. Giấy phép mã nguồn và từng mô hình là riêng biệt; xem model card và LICENSE của phiên bản tải về trước khi phân phối hoặc sử dụng thương mại. Không đóng gói lại trọng số trong Git.

### Tự tạo phụ đề, dịch và xử lý logo (2.6)

Trong mục Lồng tiếng video, chọn video, ngôn ngữ gốc (hoặc tự nhận dạng), ngôn ngữ lời đọc và giọng. **Tự nhận dạng → tạo / dịch SRT** dùng Whisper base đa ngôn ngữ, chạy CPU int8 trên máy. Bản Portable kèm model; bản mã nguồn chạy `download_subtitle_model.bat` một lần khi có Internet. Phụ đề được đưa vào ô SRT để sửa và xuất TXT/SRT. Nút tự lồng tiếng chạy nối tiếp nhận dạng, dịch nếu bật, rồi giọng đã chọn. SRT giữ nguyên mốc; câu dịch dài quá ô sẽ yêu cầu chỉnh thay vì cắt lời.

Dịch dùng model Ollama cục bộ (mặc định `qwen3:4b`); cần cài Ollama và chạy `setup_local_writer.bat` trước. Không cần API key. Chưa có Ollama vẫn tạo được phụ đề nguyên ngữ. Nhận dạng/dịch có thể sai; kiểm tra tên riêng, tiếng ồn và các mốc câu trước khi dùng. Thời gian nhận dạng phụ thuộc CPU và độ dài video.

**Hiện khung hình** rồi kéo chọn vùng logo cố định. Có thể xuất video chỉ xử lý logo hoặc bật áp dụng khi lồng tiếng. Nội suy không phục hồi chi tiết bị che, không theo dõi logo chuyển động. Xử lý logo mã hóa lại H.264/CRF20 nên chậm hơn ghép giọng nguyên hình. Nút **Dừng** hủy cả nhận dạng, dịch hoặc xử lý logo; thanh phần trăm dựa trên mốc âm thanh/hình ảnh đang xử lý. Dữ liệu tác vụ nằm trong `.data/video_tasks`; phụ đề gốc được giữ nếu dịch thất bại.

### Sửa trực tiếp trên video (2.7)

Chọn hoặc tải video trong **Lồng tiếng video**. Khung xem và danh sách câu nằm ngay trong tool; nhấn **Tự tạo phụ đề từ lời nói trong video**, sửa lời và mốc từng câu, thêm/xóa câu nếu cần. **Lưu phụ đề đã sửa** giữ dự án trong `.data/editor`. **Xuất video có phụ đề đã sửa** gắn chữ trực tiếp vào hình và giữ âm thanh gốc; không cần voice hoặc nhập TXT/SRT. Có thể chọn dịch các câu đang sửa hoặc lồng tiếng bằng giọng đã chọn. TXT/SRT chỉ là tùy chọn nâng cao.

Dừng video ở mốc cần xem, nhấn **Khoanh vùng logo tại thời điểm đang xem**, kéo chọn vùng rồi bật áp dụng khi xuất. Có thể xuất phụ đề và xử lý vùng logo trong một lần. Video phát trong trình duyệt nếu codec hỗ trợ; trường hợp khác dùng ô giây và nút xem khung hình. Đây là phụ đề mới từ âm thanh hoặc các câu tự nhập; chữ cũ dính trong hình chưa được OCR để sửa tự động. Có thể khoanh vùng chữ cũ để xử lý và gắn chữ mới, nhưng chi tiết bị che không khôi phục được.

### Chế độ xuất 2.8

Trong trình sửa video, chọn độ phân giải **Gốc / 720p / 1080p / UHD 4K**. Xuất MP4 không cần có phụ đề; nút xuất video có phụ đề dùng các câu vừa sửa. Có nút xuất TXT và SRT ngay trong trình sửa, tự lưu câu đã sửa trước khi tải; không cần mở phần nhập tệp nâng cao. Chế độ độ phân giải cũng áp dụng khi xử lý logo hoặc lồng tiếng.

Xuất giữ tỷ lệ hình, không cắt hoặc kéo méo. UHD 4K tối đa 3840×2160 ngang, 2160×3840 dọc; video tỷ lệ khác nằm trong khung giới hạn tương ứng. Chế độ Gốc không nâng kích thước, nhưng hạ video trên 4K về giới hạn 4K. Các chế độ kích thước cố định có thể nâng video nhỏ lên; đây không phải phục hồi chi tiết bằng AI. Giữ FPS nguồn. Xử lý logo trước khi đổi kích thước; gắn phụ đề sau khi đổi kích thước để chữ rõ ở độ phân giải đầu ra. 4K cần nhiều CPU/RAM và thời gian hơn.

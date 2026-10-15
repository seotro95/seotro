# Voice Studio 2 — bản đọc dài, nhấn/nghỉ và AI viết kịch bản

Giao diện tiếng Việt cho chuyển văn bản thành lời nói, hồ sơ nhân bản giọng từ mẫu, thư viện giọng, hàng đợi, nghe lại và tải WAV/MP3. Tạo giọng cục bộ không cần API key. Tính năng AI viết kịch bản là tùy chọn, dùng OpenAI/Gemini API qua Internet.

## Chức năng

- Tiếng Việt/Anh: **VieNeu-TTS v3 Turbo**, chạy ONNX trên CPU.
- Anh, Nhật, Hàn, Trung, Pháp, Đức, Tây Ban Nha, Ý, Bồ Đào Nha, Nga: **Qwen3-TTS 0.6B CustomVoice**; nhân bản dùng **0.6B Base**.
- Hai lựa chọn English US/UK dùng chung mô hình ngôn ngữ English. Âm sắc/giọng vùng phụ thuộc giọng gốc hoặc mẫu thu, không được bảo đảm chỉ bằng lựa chọn ngôn ngữ. Với UK, nên thêm mẫu được phép sử dụng của người nói giọng Anh.
- Nhập mẫu âm thanh 3–30 giây, tối đa 20 MB. VieNeu thực tế dùng tối đa khoảng 8 giây tham chiếu. Đoạn sạch, một người nói, không nhạc cho kết quả tốt hơn.
- Lưu mẫu là đăng ký hồ sơ tham chiếu, không huấn luyện lại mô hình. Nhân bản thực sự được thực hiện khi tạo lời đọc mới. Chỉ dùng mẫu của chính bạn hoặc đã được chủ giọng cho phép.
- Điều chỉnh tốc độ 0.7–1.4×, xuất WAV hoặc MP3 192 kbps. Lịch sử lưu cục bộ; xóa mẫu và bản thu riêng.
- Tối đa 4 tác vụ chờ/chạy; chạy tuần tự để giảm RAM. Nhận tối đa **200.000 ký tự**, chia câu/đoạn tối đa 240 ký tự, nạp mô hình một lần cho mỗi tác vụ. PCM được ghi theo khối trên đĩa, không giữ bản thu nhiều giờ trong RAM.
- Bản thu tối đa **180 phút (3 giờ)**, tính cả khoảng nghỉ và tốc độ đã chỉnh. Nếu đạt giới hạn trước khi hết lời, giao diện báo rõ còn nội dung chưa đọc. Không kéo giãn/chèn im lặng cho đủ 3 giờ.
- Dừng/tiếp tục trong Lịch sử: lưu từng đoạn, tiếp tục dùng lại các đoạn đã hoàn tất. Khởi động lại máy đánh dấu tác vụ gián đoạn; có thể tiếp tục. Giới hạn xử lý một lượt là 7 ngày, tách biệt với thời lượng âm thanh 3 giờ.
- Nhập kịch bản `.txt`, đánh dấu **từ cần nhấn** và `[pause=1.5]`; nhịp đọc Tự nhiên/Kể chuyện/Tin tức/Thư giãn/Sôi nổi điều chỉnh tốc độ và khoảng nghỉ. Nhấn từ dùng tốc độ chậm hơn và tăng âm lượng nhẹ có limiter. Đây là điều khiển nhịp/âm lượng; mô hình hiện tại không hỗ trợ đầy đủ mô tả cảm xúc tự do.


## Cập nhật từ bản trước (Windows)

1. Tắt Voice Studio bằng Ctrl+C trong cửa sổ đang chạy.
2. Tải ZIP mới từ GitHub, chép các tệp trong thư mục `voice-studio` mới đè vào thư mục cũ. **Giữ nguyên `.data` và `.venv`** để không mất mô hình, mẫu giọng và bản thu. Không xóa thư mục cũ rồi giải nén lại nếu chưa sao lưu dữ liệu.
3. Bản 2 dùng các thư viện đã có ở bản trước; chạy `start.bat`. Nếu thư viện thiếu, chạy lại `install.bat` và chụp lỗi cuối khi thất bại.
4. Muốn bật chế độ nhanh tiếng Việt, chạy thêm `download_fast_model.bat`. Chỉ khả dụng trên CPU được xác nhận có AVX-VNNI/AVX-512 VNNI. Nếu máy không hỗ trợ, dùng Tiêu chuẩn.

## Viết lời/kịch bản bằng ChatGPT hoặc Gemini

Mở **AI viết kịch bản**, chọn OpenAI hoặc Gemini, nhập API key và bấm **Kiểm tra & kết nối**. Key chỉ được giữ trong RAM phía máy chủ, không ghi vào `.data`, Git hoặc localStorage. Tắt/khởi động lại ứng dụng thì cần kết nối lại. Có thể cấu hình `OPENAI_API_KEY`, `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` trong môi trường thay cho nhập qua giao diện; việc ngắt một key từ môi trường yêu cầu xóa biến đó và khởi động lại.

- Model mặc định: `gpt-4.1-mini` / `gemini-2.5-flash`; có ô đổi tên model nếu tài khoản hoặc dịch vụ thay đổi danh mục.
- Viết lời, viết lại/thêm nhịp đọc, lập dàn ý; chọn ngôn ngữ và mục tiêu 1–180 phút. **Đưa sang tạo giọng** thay thế nội dung trình đọc; **Thêm vào cuối** nối tiếp nội dung đã có.
- Một phản hồi API có giới hạn token. Với kịch bản dài, dùng dàn ý/chương và **Viết tiếp**, rồi thêm từng phần; không coi một phản hồi ngắn là đủ kịch bản 3 giờ. Thời lượng mục tiêu khi viết chỉ là ước tính.
- Khi bấm Viết, chủ đề và nội dung trong ô yêu cầu được gửi đến nhà cung cấp đã chọn. Không gửi mẫu giọng. Tính năng này cần Internet, quyền dùng model và hạn mức API; gói ChatGPT Plus/Gemini trên web không tự cấp hạn mức API.
- Mô hình tạo giọng vẫn chạy cục bộ với cờ offline; API viết kịch bản là tính năng kết nối mạng riêng. Các miền API: `api.openai.com`, `generativelanguage.googleapis.com`.

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

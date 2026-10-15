# Voice Studio — AI giọng nói chạy cục bộ

Giao diện tiếng Việt cho chuyển văn bản thành lời nói, hồ sơ nhân bản giọng từ mẫu, thư viện giọng, hàng đợi, nghe lại và tải WAV/MP3. Không cần API key hoặc thuê dịch vụ tạo giọng.

## Chức năng

- Tiếng Việt/Anh: **VieNeu-TTS v3 Turbo**, chạy ONNX trên CPU.
- Anh, Nhật, Hàn, Trung, Pháp, Đức, Tây Ban Nha, Ý, Bồ Đào Nha, Nga: **Qwen3-TTS 0.6B CustomVoice**; nhân bản dùng **0.6B Base**.
- Hai lựa chọn English US/UK dùng chung mô hình ngôn ngữ English. Âm sắc/giọng vùng phụ thuộc giọng gốc hoặc mẫu thu, không được bảo đảm chỉ bằng lựa chọn ngôn ngữ. Với UK, nên thêm mẫu được phép sử dụng của người nói giọng Anh.
- Nhập mẫu âm thanh 3–30 giây, tối đa 20 MB. VieNeu thực tế dùng tối đa khoảng 8 giây tham chiếu. Đoạn sạch, một người nói, không nhạc cho kết quả tốt hơn.
- Lưu mẫu là đăng ký hồ sơ tham chiếu, không huấn luyện lại mô hình. Nhân bản thực sự được thực hiện khi tạo lời đọc mới. Chỉ dùng mẫu của chính bạn hoặc đã được chủ giọng cho phép.
- Điều chỉnh tốc độ 0.7–1.4×, xuất WAV hoặc MP3 192 kbps. Lịch sử lưu cục bộ; xóa mẫu và bản thu riêng.
- Tối đa 4 tác vụ chờ/chạy; chạy tuần tự để giảm RAM. Mỗi lần suy luận dùng tiến trình riêng, giải phóng mô hình khi hoàn tất. Giới hạn 2.000 ký tự/lượt, 30 phút/lượt.

## Yêu cầu

Python 3.12 được dùng trong môi trường phát triển; FFmpeg/ffprobe trong PATH. Khuyến nghị 16 GB RAM trở lên và khoảng 8–12 GB đĩa trống cho thư viện/mô hình. Máy cloud hiện tại có khoảng 33 GB RAM, 5 CPU và không có NVIDIA GPU. CPU có thể mất nhiều phút; tốc độ và độ tự nhiên cần đánh giá trên bản thu thực tế.

Lần tải đầu cần truy cập PyPI, kho PyTorch CPU và Hugging Face (`huggingface.co`, `*.huggingface.co`, `*.hf.co`). Sau khi chuẩn bị mô hình, tiến trình tạo giọng bật `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1`; văn bản/mẫu không gửi tới API giọng nói. Tệp được lưu trên **máy chạy ứng dụng**: nếu chạy cloud, đó là máy cloud, không phải máy tính cá nhân của bạn.

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

Không có mô hình nào bảo đảm sao chép chính xác 100% một giọng thật. Tính năng thiết kế giọng hoàn toàn mới bằng mô tả văn bản, fine-tune, chỉnh sửa timeline và chạy nhiều người dùng chưa được triển khai.

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

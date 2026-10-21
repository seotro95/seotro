# Hmoob VoiceLab 1.1

Gói ZIP 1.0 cũ vẫn được thu hồi do cảnh báo Defender trên máy người dùng; xem [SECURITY-REVIEW.md](SECURITY-REVIEW.md). Bản 1.1 bổ sung bộ khởi chạy tự chuẩn bị, hai giọng có sẵn lời tham chiếu và quy trình kiểm thử/quét riêng cho gói Windows mới.

Tool mới, viết độc lập cho quy trình đọc Hmong Trắng cục bộ, không cần API key. Nhận tối đa **1.000.000 ký tự Unicode** qua trình soạn thảo hoặc TXT UTF-8 tối đa 4 MB.

**Trạng thái hiện tại (21/10/2026):** 59 kiểm thử đạt. Mô hình F5-Hmong/Vocos đã tải và xác minh checksum trên máy cloud; tác vụ thật chạy ngoại tuyến qua hàng đợi đã tạo WAV mono 24 kHz bằng mẫu Hmong công khai và hai mẫu nam/nữ của người dùng. Hai giọng mặc định đã có lời và mốc đoạn đầu do người dùng nghe xác nhận; bản đọc thử mới dài **4,128 giây (nữ)** và **3,819 giây (nam)**. **Chưa đánh giá phát âm Hmong Trắng hoặc độ giống giọng**, chưa thử đọc tài liệu dài bằng mô hình thật. Xem `VALIDATION.md` cho nguồn mẫu, phép đo và giới hạn.

## Mở tool

**Windows Portable:** giải nén toàn bộ gói rồi mở **`MO_HMOOB_VOICELAB.bat`** ở thư mục ngoài cùng. Gói có sẵn Python 64-bit, thư viện AI, FFmpeg và ffprobe. Lần đầu cần Internet để tool tự tải và xác minh mô hình F5-Hmong/Vocos khoảng **1,4 GB**; không cần API key hoặc cài thêm công cụ. Các lần sau mở cùng tệp và dùng ngoại tuyến. Hai giọng đã có sẵn đoạn mẫu/lời, chỉ cần chọn giọng, nhập văn bản rồi tạo. Đọc `BAT-DAU.txt` trong gói.

Khuyến nghị Windows 10/11 x64, RAM 16 GB và ít nhất khoảng 8 GB đĩa trống cho ứng dụng/mô hình, cộng dung lượng bản thu dài. Giữ cửa sổ lệnh trong lúc dùng; Ctrl+C để dừng. Chỉ cho phép máy chủ trên 127.0.0.1. Sao lưu `hmoob-voicelab/.data` khi chuyển hoặc cập nhật bản Portable.

Bộ khởi chạy hiện thông báo ngay trước khi nạp Python/thư viện AI, rồi báo từng bước kiểm tra và tải mô hình. Lần đầu nạp thư viện trên máy có thể lâu hơn; bước này có giới hạn 120 giây và báo rõ nếu hết thời gian. Nếu trình duyệt chưa mở, xem bước đang chạy trong cửa sổ hoặc nhật ký `hmoob-voicelab/.data/.logs/launch.log`. Tệp `CHAN_DOAN_HMOOB.bat` kiểm tra điều kiện chạy và ghi kết quả vào nhật ký; chỉ mở địa chỉ giao diện khi cửa sổ đã in URL của máy chủ.

**Bản mã nguồn:** Windows cần Python 3.10–3.12 64-bit và FFmpeg/ffprobe, chạy `start.bat`. Linux/macOS chạy `bash start.sh`. Bộ khởi chạy tự tạo môi trường riêng và tải phần còn thiếu ở lần đầu, giữ nguyên dữ liệu và mô hình đã có. `install_voice.bat` hoặc `start.bat --setup` chỉ chuẩn bị rồi thoát; `start.bat --check` kiểm tra mà không tải/cài. Với Linux/macOS dùng các tham số tương tự sau `bash start.sh`.

Muốn tạo lời mới cần thêm:

1. Cài **FFmpeg và ffprobe** theo hướng dẫn ffmpeg.org, thêm thư mục chứa chúng vào PATH.
2. Bản mã nguồn dùng `start.bat` hoặc `bash start.sh`; bộ khởi chạy tự chuẩn bị `.venv` khi cần, cài PyTorch CPU/F5-TTS và tải mô hình có kiểm tra checksum. Bản Portable đã có runtime/thư viện và chỉ tải mô hình lần đầu. Không tự xóa môi trường hoặc dữ liệu cũ nếu không tương thích.
3. Chọn giọng Nam/Nữ. Hai mẫu đã có sẵn lời tham chiếu khớp đoạn đầu: **Nữ 0–5,30 giây**, **Nam 0–4,50 giây**, được người dùng nghe xác nhận. Có thể nghe đoạn chọn trong **Đoạn mẫu & lời tham chiếu**. Nếu đổi mốc, nhập đúng lời khớp đoạn mới dài **3–8 giây** rồi bấm **Lưu đoạn & lời mẫu**.
4. Kiểm tra lại bộ tạo giọng, tạo một câu ngắn và nghe đánh giá trước khi gửi tài liệu dài.

Linux/macOS, cài PyTorch/torchaudio phù hợp CPU hoặc GPU theo https://pytorch.org/get-started/locally/ trong một venv Python 3.10–3.12, sau đó:

```sh
python -m pip install -r requirements-voice.txt
python setup_voice.py
python launch.py
```

Máy cloud hiện tại dùng `/workspace/venvs/hmong-f5/bin/python`, với F5-TTS 1.1.22 và PyTorch/torchaudio 2.6.0 CPU. Trong thư mục tool, chạy `setup_voice.py` bằng Python này để chuẩn bị mô hình, rồi mở bằng `/workspace/venvs/hmong-f5/bin/python launch.py --no-browser`.

## Tạo văn bản dài và tối ưu tốc độ

- Các câu ngắn được gom vào đoạn tối đa 300 ký tự; bản gốc được giữ nguyên, kể cả Unicode và xuống dòng. Mô hình xử lý tiếp các phần nhỏ có giới hạn ngữ cảnh.
- Một mô hình và tensor tham chiếu được giữ trong RAM để dùng lại. Tool xử lý một tác vụ tại một thời điểm, tối đa 4 tác vụ đang chạy/chờ; tránh tạo nhiều bản sao mô hình làm đầy RAM/VRAM.
- **Nhanh: 16 bước** là mặc định. **Chất lượng: 32 bước** xử lý lâu hơn. **Bản nháp: 8 bước** mang tính thử nghiệm, có thể giảm độ rõ/phát âm. Không có cam kết một triệu ký tự sẽ xong trong vài phút.
- `HMOOB_DEVICE=auto` tự chọn CUDA, MPS hoặc CPU mà PyTorch thực sự hỗ trợ. Bộ cài Windows mặc định dùng PyTorch CPU. Muốn dùng NVIDIA, cài bản PyTorch CUDA phù hợp theo pytorch.org vào chính `.venv` trước khi chạy; không cài lại gói CPU đè lên bản CUDA.
- **Nhịp đọc 0,5–2×** điều chỉnh lời đọc, khác với thời gian xử lý máy. Hệ số xử lý đo từ âm thanh thực đã tạo chia cho thời gian suy luận và ghi checkpoint, có tính lần nạp mô hình; ước tính còn lại chỉ là tham khảo. Tổng thời gian tác vụ còn gồm ghép tệp.
- Đầu ra thành các chương WAV liên tiếp, mỗi chương tối đa **30 phút**, tiếp tục đến hết lời. Không có giới hạn dừng âm thầm ở 3 giờ. Không ép toàn bộ tài liệu vào một WAV khổng lồ hoặc giữ toàn bộ âm thanh trong RAM. Tải từng chương hoặc ZIP chứa toàn bộ chương, kịch bản và manifest.
- WAV mono PCM16 24 kHz chiếm khoảng **173 MB mỗi giờ**. Khi chưa hoàn tất cần thêm dung lượng cho checkpoint và chương đang ghép; tạo ZIP cần thêm khoảng bằng toàn bộ kết quả. Đĩa gần đầy sẽ báo lỗi và giữ tiến độ để tiếp tục sau khi giải phóng chỗ.
- **Dừng** có hiệu lực sau đoạn suy luận hiện tại; tool không ngắt hỏng mô hình giữa chừng. Khi tiếp tục, dùng lại đoạn WAV đã ghi xong và bản chụp cố định của lời/mẫu/thiết lập tác vụ. Sau khi đóng máy chủ, tác vụ chưa xong xuất hiện ở trạng thái có thể tiếp tục.
- Khi **Tiếp tục**, đoạn WAV bị hỏng, thiếu dữ liệu hoặc rỗng được tạo lại; các đoạn còn nguyên và lời/mẫu đã lưu vẫn được dùng lại. Nếu lần tạo lại thất bại, có thể tiếp tục lần nữa.

Mô hình cộng đồng F5-Hmong là thử nghiệm, không bảo đảm mọi từ và văn bản dài được đọc chính xác. Nghe lại trước khi sử dụng kết quả. Tạo bản dài chỉ sau khi câu thử phù hợp mục đích của bạn.

## Mô hình, hai mẫu giọng và dữ liệu

Nguồn mô hình: https://github.com/YangNobody12/F5-TTS-Hmong và https://huggingface.co/Pakorn2112/F5TTS-Hmong ; Vocos: https://huggingface.co/charactr/vocos-mel-24khz . Kiểm tra giấy phép của từng bộ trọng số trước khi dùng cho mục đích của bạn.

`setup_voice.py` lấy metadata từ HTTPS chính thức tại các commit đã kiểm thử được cố định trong `MODEL_REVISIONS`, từ chối phản hồi khác phiên bản, kiểm tra SHA-256 cho tệp LFS hoặc Git blob cho tệp nhỏ, rồi ghi `verified-models.json`. Bản Portable không phân phối lại checkpoint Hmong chưa có giấy phép rõ ràng; tải trực tiếp từ nguồn mô hình cho máy người dùng khi chuẩn bị lần đầu. Có thể xác minh lại offline:

```sh
python setup_voice.py --verify-only
```

Không tự tải mô hình hoặc tự nhận dạng lời mẫu khi bấm Tạo giọng. Nếu thiếu tệp hoặc checksum sai, tool báo thiếu điều kiện thay vì dùng âm thanh giả. Không tắt TLS/checksum để vượt lỗi mạng. Trên cloud cần cho phép `huggingface.co`, các miền con Hugging Face và CDN `*.xethub.hf.co` trong Environment settings, lưu thay đổi rồi chạy lại bộ cài. Việc lưu bản nháp chưa áp dụng hoặc publish cấu hình.

Hai tệp `assets/default-female.mp3` và `assets/default-male.mp3` giữ nguyên byte và khớp SHA-256 với hai MP3 người dùng tải lên. `assets/voices.json` chứa thời lượng, checksum, lời và mốc đoạn đầu do người dùng xác nhận ngày 21/10/2026. Giọng nữ được chọn khi mở tool. Dữ liệu mới dùng các đoạn mặc định đã xác nhận; lời/mốc do người dùng lưu riêng trong `.data/references/` luôn được ưu tiên khi cập nhật tool. Không tự nhận dạng hoặc đoán lời mẫu.

Mặc định dữ liệu ở `.data/`: lời tham chiếu, văn bản tác vụ, kế hoạch chia đoạn, mẫu WAV cố định, checkpoint và chương đầu ra. Giữ thư mục này khi cập nhật tool. `HMOOB_DATA_DIR` đổi thư mục dữ liệu, `HMOOB_MODEL_DIR` đổi thư mục mô hình (mặc định `.data/models`). Chỉ cho phép một phiên máy chủ dùng cùng thư mục dữ liệu.

## Kiểm thử

Trong thư mục tool:

```sh
python -m unittest discover -s tests -v
node --check web/app.js
```

Xem `VALIDATION.md` để phân biệt kiểm thử ứng dụng bằng engine giả lập với những phần đã kiểm tra bằng thư viện/tệp thật. Chưa chạy launcher BAT trên Windows thật.

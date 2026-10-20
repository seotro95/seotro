# Hmoob VoiceLab 1.0

**Cảnh báo phát hành:** gói ZIP 1.0 đã bị Windows Defender trên máy người dùng chặn với tên `Trojan:Script/Ulthar.A!ml`. Tạm ngừng cung cấp gói này; chưa có kết luận cảnh báo nhầm hoặc an toàn. Không khôi phục/cho phép tệp bị chặn hoặc tắt bảo vệ. Xem [SECURITY-REVIEW.md](SECURITY-REVIEW.md).

Tool mới, viết độc lập cho quy trình đọc Hmong Trắng cục bộ, không cần API key. Nhận tối đa **1.000.000 ký tự Unicode** qua trình soạn thảo hoặc TXT UTF-8 tối đa 4 MB.

**Trạng thái hiện tại:** giao diện, hàng đợi, chia đoạn, lưu/tiếp tục và xuất WAV/ZIP đã được kiểm thử. F5-TTS/PyTorch đã cài và import được trên máy cloud. **Chưa có bản đọc Hmong thực tế được kiểm chứng**, vì proxy của máy cloud từ chối tải mô hình Hugging Face (CONNECT 403). Chưa đo được tốc độ tạo giọng, chất lượng Hmong Trắng hoặc độ giống mẫu. Không coi tốc độ chia văn bản là tốc độ tạo voice.

## Mở tool

Windows: cài **Python 3.12 64-bit** và Python Launcher từ python.org, giải nén toàn bộ gói rồi chạy `start.bat`. Giao diện mở được bằng thư viện có sẵn của Python, không cần cài thư viện AI trước. Linux/macOS: `bash start.sh`. Mở địa chỉ mà cửa sổ lệnh in ra bằng trình duyệt trên cùng máy. Giữ cửa sổ chạy; Ctrl+C để dừng. Chỉ cho phép máy chủ trên 127.0.0.1.

Muốn tạo lời mới cần thêm:

1. Cài **FFmpeg và ffprobe** theo hướng dẫn ffmpeg.org, thêm thư mục chứa chúng vào PATH.
2. Windows: chạy `install_voice.bat`. Bộ cài chọn Python 3.10–3.12 64-bit, tạo `.venv`, cài PyTorch CPU/F5-TTS và tải mô hình có kiểm tra checksum. Không tự xóa môi trường hoặc dữ liệu cũ nếu không tương thích.
3. Nghe mẫu Nam/Nữ; chọn một đoạn rõ lời dài **3–8 giây**. Nhập đúng lời Hmong khớp đoạn đó và bấm **Lưu đoạn & lời mẫu**.
4. Kiểm tra lại bộ tạo giọng, tạo một câu ngắn và nghe đánh giá trước khi gửi tài liệu dài.

Linux/macOS, cài PyTorch/torchaudio phù hợp CPU hoặc GPU theo https://pytorch.org/get-started/locally/ trong một venv Python 3.10–3.12, sau đó:

```sh
python -m pip install -r requirements-voice.txt
python setup_voice.py
python launch.py
```

Máy cloud đã cài thư viện dùng `/workspace/.venvs/hmoob-voice/bin/python`. Chạy `setup_voice.py` bằng Python này sau khi truy cập Hugging Face được cho phép, rồi chạy `launch.py --no-browser` trong thư mục tool.

## Tạo văn bản dài và tối ưu tốc độ

- Các câu ngắn được gom vào đoạn tối đa 300 ký tự; bản gốc được giữ nguyên, kể cả Unicode và xuống dòng. Mô hình xử lý tiếp các phần nhỏ có giới hạn ngữ cảnh.
- Một mô hình và tensor tham chiếu được giữ trong RAM để dùng lại. Tool xử lý một tác vụ tại một thời điểm, tối đa 4 tác vụ đang chạy/chờ; tránh tạo nhiều bản sao mô hình làm đầy RAM/VRAM.
- **Nhanh: 16 bước** là mặc định. **Chất lượng: 32 bước** xử lý lâu hơn. **Bản nháp: 8 bước** mang tính thử nghiệm, có thể giảm độ rõ/phát âm. Không có cam kết một triệu ký tự sẽ xong trong vài phút.
- `HMOOB_DEVICE=auto` tự chọn CUDA, MPS hoặc CPU mà PyTorch thực sự hỗ trợ. Bộ cài Windows mặc định dùng PyTorch CPU. Muốn dùng NVIDIA, cài bản PyTorch CUDA phù hợp theo pytorch.org vào chính `.venv` trước khi chạy; không cài lại gói CPU đè lên bản CUDA.
- **Nhịp đọc 0,5–2×** điều chỉnh lời đọc, khác với thời gian xử lý máy. Hệ số xử lý đo từ âm thanh thực đã tạo chia cho thời gian suy luận và ghi checkpoint, có tính lần nạp mô hình; ước tính còn lại chỉ là tham khảo. Tổng thời gian tác vụ còn gồm ghép tệp.
- Đầu ra thành các chương WAV liên tiếp, mỗi chương tối đa **30 phút**, tiếp tục đến hết lời. Không có giới hạn dừng âm thầm ở 3 giờ. Không ép toàn bộ tài liệu vào một WAV khổng lồ hoặc giữ toàn bộ âm thanh trong RAM. Tải từng chương hoặc ZIP chứa toàn bộ chương, kịch bản và manifest.
- WAV mono PCM16 24 kHz chiếm khoảng **173 MB mỗi giờ**. Khi chưa hoàn tất cần thêm dung lượng cho checkpoint và chương đang ghép; tạo ZIP cần thêm khoảng bằng toàn bộ kết quả. Đĩa gần đầy sẽ báo lỗi và giữ tiến độ để tiếp tục sau khi giải phóng chỗ.
- **Dừng** có hiệu lực sau đoạn suy luận hiện tại; tool không ngắt hỏng mô hình giữa chừng. Khi tiếp tục, dùng lại đoạn WAV đã ghi xong và bản chụp cố định của lời/mẫu/thiết lập tác vụ. Sau khi đóng máy chủ, tác vụ chưa xong xuất hiện ở trạng thái có thể tiếp tục.

Mô hình cộng đồng F5-Hmong là thử nghiệm, không bảo đảm mọi từ và văn bản dài được đọc chính xác. Nghe lại trước khi sử dụng kết quả. Tạo bản dài chỉ sau khi câu thử phù hợp mục đích của bạn.

## Mô hình, hai mẫu giọng và dữ liệu

Nguồn mô hình: https://github.com/YangNobody12/F5-TTS-Hmong và https://huggingface.co/Pakorn2112/F5TTS-Hmong ; Vocos: https://huggingface.co/charactr/vocos-mel-24khz . Kiểm tra giấy phép của từng bộ trọng số trước khi dùng cho mục đích của bạn.

`setup_voice.py` lấy metadata từ HTTPS chính thức, cố định commit tải về, kiểm tra SHA-256 cho tệp LFS hoặc Git blob cho tệp nhỏ, rồi ghi `verified-models.json`. Có thể xác minh lại offline:

```sh
python setup_voice.py --verify-only
```

Không tự tải mô hình hoặc tự nhận dạng lời mẫu khi bấm Tạo giọng. Nếu thiếu tệp hoặc checksum sai, tool báo thiếu điều kiện thay vì dùng âm thanh giả. Không tắt TLS/checksum để vượt lỗi mạng. Trên cloud cần cho phép `huggingface.co`, các miền con Hugging Face và CDN `*.xethub.hf.co` trong Environment settings, lưu thay đổi rồi chạy lại bộ cài. Việc lưu bản nháp chưa áp dụng hoặc publish cấu hình.

Hai tệp `assets/default-female.mp3` và `assets/default-male.mp3` được sao chép nguyên byte từ hai bản ghi có sẵn trong repository. SHA-256 và thời lượng nằm trong `assets/voices.json`. **Tệp TXT vừa gửi trong hội thoại không phải mẫu âm thanh mới**. Giọng nữ được chọn khi mở tool; lời tham chiếu ban đầu để trống, không tự đoán. Mẫu nghe gốc chưa chứng minh nhân bản lời mới hoạt động.

Mặc định dữ liệu ở `.data/`: lời tham chiếu, văn bản tác vụ, kế hoạch chia đoạn, mẫu WAV cố định, checkpoint và chương đầu ra. Giữ thư mục này khi cập nhật tool. `HMOOB_DATA_DIR` đổi thư mục dữ liệu, `HMOOB_MODEL_DIR` đổi thư mục mô hình (mặc định `.data/models`). Chỉ cho phép một phiên máy chủ dùng cùng thư mục dữ liệu.

## Kiểm thử

Trong thư mục tool:

```sh
python -m unittest discover -s tests -v
node --check web/app.js
```

Xem `VALIDATION.md` để phân biệt kiểm thử ứng dụng bằng engine giả lập với những phần đã kiểm tra bằng thư viện/tệp thật. Chưa chạy launcher BAT trên Windows thật.

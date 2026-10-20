# Hmong Studio 0.7.0 — tự dùng NVIDIA và đo cấu hình nhanh

Bản này gom toàn bộ ứng dụng, hai mẫu nam/nữ và các bản sửa lỗi vào một ZIP. **Chỉ chạy `CHAY-STUDIO.bat`**: tự phát hiện NVIDIA, thử cài CUDA riêng, kiểm tra GPU bằng phép tính thật rồi mở Studio trong trình duyệt. Nếu chưa cài được GPU, chương trình báo rõ và dùng lại CPU đã kiểm tra; không lặp tải bộ GPU thất bại ở mỗi lần mở. Những lần sau dùng lại bộ máy hợp lệ, không cài đè thư viện.

**Dành cho GTX 1060 6 GB:** phần tra chữ Qwen dùng chung với đầu ra ngôn ngữ không sử dụng được chuyển về RAM, giảm nhu cầu giữ khoảng **0,507 GiB trọng số trên VRAM** khi mô hình phù hợp. Bộ transformer, chọn token giọng, sinh phổ và vocoder vẫn chạy trên GPU. Không lượng tử hóa thêm hoặc sửa trọng số tải về; giá trị embedding và phép tính Qwen được kiểm tra bằng mô hình nhỏ. Chưa đo chuyển bộ nhớ/tốc độ trên GPU thật trong phiên này.

**Chọn cấu hình nhanh bằng số đo tại máy:** mở Studio một lần để cài GPU, đóng cửa sổ Studio bằng Ctrl+C, rồi chạy **`DO-TOC-DO.bat`**. Công cụ tạo bốn mẫu ngắn (làm ấm và đo riêng cho FP32/FP16), Review + Lọc ồn Nhẹ, lưu WAV để nghe và chọn chế độ có thời gian tạo trên mỗi giây lời đọc thấp nhất. Nó không tính 0,15 giây khoảng lặng tool thêm cuối câu vào lời đã tạo. Kết quả lưu riêng cho GPU/thư viện/mô hình hiện có; mở lại `CHAY-STUDIO.bat` để áp dụng. Nếu phép đo lỗi bất thường hoặc bị dừng, cấu hình trước vẫn giữ nguyên. Nếu một chế độ hết VRAM, chỉ chế độ đã tạo WAV hợp lệ được xét. Một mẫu ngắn nhanh không chứng minh đã tạo một giờ trong hai phút.

**Chưa đạt hoặc xác nhận mục tiêu 2 phút tạo 1 giờ voice trên GTX 1060.** Card này không có Tensor Cores/TF32; FP16 không mặc nhiên nhanh hơn FP32. Bản này giúp app tự vào đường CUDA và chọn theo phép đo thật, không gắn nhãn đã đạt 30 lần thời gian thực. Đây là app cục bộ mở trong trình duyệt, không phải EXE độc lập chứa sẵn Python/mô hình.

Giữ lựa chọn **Chuẩn / Nhanh CPU** và **Lọc ồn Tắt / Nhẹ / Mạnh** từ 0.6.0. Mặc định Chuẩn + Nhẹ. Mẫu được giảm ù/ồn nền và cân mức trước khi lấy âm sắc; bản đọc cuối được giảm ồn và giới hạn đỉnh âm thanh một lần sau khi ghép. Giữ **1.000.000 ký tự/lượt**, Review, TXT/SRT, tiến độ %, worker/mẫu dùng lại và WAV ghi trực tiếp ra đĩa.

Trên máy chạy CPU, chọn **Nhanh CPU + Lọc ồn Nhẹ** để thử tốc độ. Chế độ nhanh dùng bản sao INT8 của riêng bộ sinh phổ; bộ chọn token giọng và mô hình gốc không thay đổi. Sau mỗi lượt, bộ máy trả lại bản Chuẩn; bản nhanh được giữ trong bộ nhớ để dùng tiếp. Chế độ nhanh có thể đổi âm sắc, cần nghe kiểm tra; chọn Chuẩn nếu kết quả không phù hợp. Trên NVIDIA, dùng **Chuẩn + Nhẹ** và cấu hình FP32/FP16 đã đo; Nhanh CPU không tăng thêm tốc độ GPU.

Đo thực tế bản 0.6.0, mẫu nữ Review và Lọc ồn Nhẹ trên CPU kiểm thử: Chuẩn **34,254 giây**, Nhanh CPU **26,052 giây**, cùng WAV **2,110 giây**. Mô hình đã được nạp riêng; lượt nhanh dùng lại mẫu nữ và có tạo bản INT8 lần đầu. Không ngoại suy thành tốc độ cho mọi máy hoặc một giờ lời đọc. Các WAV trong `examples` cho phép nghe so sánh; xem `TOC-DO.md` để biết đầy đủ điều kiện đo.

**Bản 0.5.1 bỏ thêm phép tính từ vựng ngôn ngữ không dùng trong bộ giải mã giọng.** Phép đo cặp cùng seed tạo WAV giống hệt từng byte: trước sửa 31,426 giây, sau sửa 30,760 giây, cùng WAV 2,110 giây. Phần sinh phổ âm vẫn chiếm khoảng 26 giây. Đây là tối ưu có số đo, **chưa đạt mục tiêu 1 giờ voice trong 2 phút**. Xem `TOC-DO.md` để biết phạm vi đo và phần cứng cần xác định. Chạy `KIEM-TRA-GPU.bat` để xem tên GPU/VRAM; ảnh thẻ System trong dxdiag chỉ cho biết CPU/RAM.

Phép đo CPU đám mây 4 luồng ở bản 0.5.0, Review cùng câu “Nyob zoo, kuv hais lus Hmoob.”: lượt đầu 66,817 giây cho WAV 2,510 giây; lượt dùng lại cache 46,929 giây cho WAV 2,150 giây. Lượt sau bắt đầu suy luận sau 0,012 giây, loại được khoảng 24 giây nạp mô hình/mẫu. Các số đo này không phải trên máy Xeon Windows của bạn và chưa đo GPU. RAM 128 GB giúp xử lý kịch bản dài, không tự bảo đảm tốc độ 30 lần thời gian thực.

CosyVoice Hmong tạo lời đọc mới theo mẫu nam/nữ, chạy trên máy và không cần dịch vụ trả phí hoặc API key. **Mô hình chưa nằm sẵn trong ZIP**: cần Internet lần đầu để tải thư viện và khoảng **5,4 GB** mô hình; tệp đã tải đúng được dùng tiếp. Mẫu âm thanh dùng để lấy âm sắc; không phải huấn luyện lại mô hình.

Gói này giữ bản sửa WinError 2 với tệp `__init__.py.part` sau khi đã tải trọng số. Tệp nguồn rỗng được tạo và kiểm tra checksum trước khi dùng. Nếu đang dùng bản 0.4.x/0.5.x/0.6.x, **đóng Studio và bộ cài, giải nén đè mã mới vào đúng thư mục đang dùng, giữ nguyên `.data`**, rồi chạy `CHAY-STUDIO.bat`. Không thay tệp phụ thuộc hoặc tải lại mô hình đã hợp lệ; chuyển từ bộ CPU sang CUDA cần tải thư viện GPU riêng.

Bộ cài vẫn tạo môi trường riêng để tránh WinError 32 khi pip cài đè tệp SymPy/Torch đang bị giữ. Nếu vẫn bị tiến trình giữ tệp, khởi động lại Windows trước khi thử lại; không cần chạy quản trị hoặc cài Visual C++ Build Tools.

## Cài trên Windows

1. Cài **Python 3.12.10 Windows 64-bit** từ https://www.python.org/downloads/release/python-31210/ , bật Python Launcher. Không cần gỡ Python 3.15 đang có.
2. Lần đầu: giải nén ZIP vào thư mục có quyền ghi. Đang dùng `E:\voi hmong\Hmong-Studio-Trang`: đóng Studio/bộ cài, giải nén ZIP vào **`E:\voi hmong\`** và chọn thay thế tệp để cập nhật đúng thư mục `Hmong-Studio-Trang` hiện có. Giữ `.data`; tránh lồng thêm một thư mục `Hmong-Studio-Trang` bên trong thư mục cũ. Không di chuyển `.venv` hoặc các thư mục `.venv-clone-*` sang nơi khác.
3. Bấm đúp **`CHAY-STUDIO.bat`**. Chờ quá trình cài/kiểm tra hoàn tất; Studio sẽ tự mở trong trình duyệt sau khi máy chủ sẵn sàng. Nếu bị ngắt, chạy lại chính file này để tiếp tục; không đổi checksum hoặc tắt TLS. Nếu trình duyệt không tự mở, dùng địa chỉ hiện trong cửa sổ lệnh.
4. Giữ cửa sổ lệnh mở khi dùng Studio. Nhấn Ctrl+C để đóng. Những lần sau chỉ bấm đúp **`CHAY-STUDIO.bat`**; có thể tạo voice cục bộ khi không có Internet sau khi cài xong. Nếu trình duyệt còn giao diện cũ, nhấn Ctrl+F5.

`install_clone_ai.bat` và `start.bat` vẫn có cho việc cài/mở riêng; dùng `CHAY-STUDIO.bat` thì không cần chạy hai file đó. `install_local_ai.bat` gọi bộ cài nhân bản; `install_mms_asr.bat` chỉ dành cho MMS/ASR riêng. Bộ cài tạo môi trường có tên `.venv-clone-<mã>` và chỉ chọn nó sau khi mọi kiểm tra đạt. `.venv` cũ không bị cài đè. Nếu cài lỗi, môi trường đang dùng và mô hình/giọng đã lưu được giữ nguyên; lần thử lại tạo môi trường mới. Hai bộ cài không được chạy cùng lúc.

Bộ cài mới chọn CPython 3.10–3.12 x64, ưu tiên 3.12; giữ bản sao môi trường không tương thích thay vì xóa. Dữ liệu `.data` được giữ riêng. Nếu muốn chuyển mẫu cá nhân từ bản cũ, sao chép `.data/clones` khi cả hai bản đã tắt.

Khuyến nghị **RAM 16 GB trở lên**, chừa ít nhất khoảng 15 GB đĩa trống cho mô hình/thư viện và dung lượng cho sản phẩm. Lượt đầu phải nạp mô hình; CPU có thể chậm. Nếu xuất hiện lỗi DLL của Torch/ONNXRuntime, kiểm tra Microsoft Visual C++2015–2022 x64 Redistributable chính thức; không cần bộ biên dịch Build Tools cho quy trình cài này. Windows launcher chưa được chạy trên Windows thật trong phiên kiểm thử này.

**Nếu có GPU NVIDIA:** `CHAY-STUDIO.bat` tự thử PyTorch/Torchaudio 2.6 CUDA 12.4 trong môi trường riêng, kiểm tra GPU rồi mới kích hoạt. `CAI-NVIDIA.bat` vẫn có để chủ động thử lại nếu lần tự động thất bại. Máy GTX 1060 6 GB với driver 560.94 đã được xác định qua ảnh người dùng; chưa được chạy kiểm thử từ xa. Driver tương thích không tự bảo đảm mô hình vừa VRAM hoặc đạt tốc độ yêu cầu. Sau khi đo bằng `DO-TOC-DO.bat`, lần mở tiếp dùng lựa chọn FP32/FP16 đã đo. Có thể đặt `HMONG_COSY_PRECISION=auto|float32|float16` để chủ động ghi đè; mặc định `auto`. Thay mô hình/GPU/bản Torch sẽ bỏ qua lựa chọn cũ.

## Tạo voice

- Chọn **Hmong Trắng**, rồi **Giọng nữ** hoặc **Giọng nam**. Hai mẫu chính xác người dùng cung cấp đã đi kèm; không cần thu lại bằng micro.
- Nhập lời Hmong RPA, tối đa **1.000.000 ký tự/lượt** khi dùng mẫu giọng với CosyVoice cục bộ. Có thể nhập TXT/SRT hoặc dự án JSON tối đa 8 MB; đoạn lời mới không cần trùng với lời trong mẫu. Tệp SRT tính cả mốc thời gian vào giới hạn ký tự.
- Review được chọn sẵn; có thể đổi sang Tự nhiên, Kể chuyện, Quảng cáo, Tin tức, Thư giãn, Ấm áp, Vui vẻ hoặc Buồn. Thanh tốc độ điều chỉnh nhịp đọc, không phải tốc độ tính toán.
- Chọn **Chế độ tạo** và **Lọc ồn**. Nhẹ giảm ồn nền đều, Mạnh giảm nhiều hơn nhưng có thể mất chi tiết giọng. Tắt giữ âm thanh gốc của bộ máy, không lọc hoặc cân mức mẫu. Bộ lọc không tách riêng được nhạc nền/người nói khác và không bảo đảm phát âm Hmong chuẩn. Tệp mẫu MP3/WAV gốc vẫn giữ nguyên.
- Bấm **Tạo voice**. Nút và thanh tiến độ hiện % theo các đoạn đã xử lý, kèm số đoạn, thời gian đã chạy và thời lượng âm thanh. Đây là tiến độ công việc, không phải dự đoán thời gian còn lại; đoạn dài có thể giữ cùng % trong lúc mô hình suy luận. Chỉ đạt 100% sau khi WAV đã hoàn tất và được kiểm tra.
- **Dừng** kết thúc tiến trình suy luận và dọn tệp tạm của lượt đó; lượt sau cần nạp lại mô hình. Hoàn tất bình thường thì giữ mô hình/mẫu trong bộ nhớ cho lượt kế tiếp. Bản thu trước được giữ khi tác vụ thất bại/hủy.
- Khi hoàn tất, nghe và bấm **Tải toàn bộ WAV**. Bản trên 25 MB dùng phát/tải trực tiếp để tiết kiệm RAM; công cụ cắt chỉ dùng cho bản ngắn. WAV tối đa 24 giờ/lượt (khoảng 4,15 GB mono 24 kHz PCM16), cần chừa dung lượng tương ứng và giữ Studio mở. Tải trước khi tắt máy chủ; chỉ giữ tối đa 10 kết quả tạm. Kịch bản tạo ra hơn 24 giờ cần chia nhỏ.

## Review theo mốc thời gian SRT

Chọn **Tự nhận dạng** hoặc **SRT**, nhập tệp `.srt` hay dán như sau. Nút **Mẫu review SRT** cũng nạp ví dụ; tệp đi kèm là `examples/review-hmong.srt`.

```srt
1
00:00:00,200 --> 00:00:02,700
Nyob zoo.

2
00:00:03,000 --> 00:00:09,000
Hnub no peb saib qhov no ua ke.
```

Tool chỉ đọc lời, không đọc số thứ tự hoặc mốc giờ. WAV bắt đầu từ 0; giữ khoảng lặng trước, giữa và sau lời trong từng mốc. Lời vượt khoảng thời gian được tăng tốc giữ cao độ tối đa 2 lần; nếu vẫn quá dài thì báo rõ đoạn cần nới thời gian hoặc rút ngắn lời, không cắt mất câu. Mốc chồng lấn, sai thứ tự, thiếu lời hoặc quá 24 giờ sẽ bị từ chối trước khi tạo. SRT cần bộ máy CosyVoice cục bộ và mẫu nam/nữ hoặc mẫu riêng. Lọc ồn bù 25 ms độ trễ của bộ lọc và kiểm tra đúng số mẫu, giữ mốc giờ và phần âm ở cuối câu; tiến độ chuyển sang “Đang lọc ồn” trước khi hoàn tất.

CosyVoice dùng tối đa 10 giây đầu mẫu, không yêu cầu bản chép mẫu trong chế độ instruct2. Có thể tải thêm mẫu riêng dài 3–60 giây / 20 MB, nhập tên và xác nhận quyền sử dụng. Ô bản chép là tùy chọn; chỉ dịch vụ ngoài theo hợp đồng cũ có thể yêu cầu nó.

Các cách đọc được gửi thành chỉ dẫn suy luận thực tế, không giả lập nhân bản bằng đổi cao độ. Mức độ biểu cảm, độ giống mẫu và cách phát âm cần nghe kiểm tra; chưa được đánh giá bởi người bản ngữ và không cam kết phát âm chuẩn mọi từ. Micro chỉ dùng khi muốn thu mẫu mới. Lỗi quyền micro không chặn chọn mẫu nam/nữ hoặc tạo voice.

## Đã xác minh

Linux, CPU 4 threads, không GPU:

- Toàn bộ118 tệp mô hình/mã nguồn được đối chiếu SHA256 hoặc Git blob SHA1 theo snapshot được ghim; trọng số chỉ nạp bằng `weights_only=True`.
- Giọng nữ tạo thật câu **“Nyob zoo, kuv hais lus Hmoob.”**: WAV PCM16 mono 24 kHz, 2,71 giây; lượt lạnh khoảng64,7 giây, RAM đỉnh khoảng7,84 GiB.
- Giọng nam, cách đọc Review, cùng câu trên: tạo thật qua giao diện/API, WAV 2,51 giây; lượt này khoảng93,6 giây. Đây là số đo máy kiểm thử, không bảo đảm tốc độ trên máy khác.
- Nút Dừng đã kết thúc worker thật, sau đó tạo lại thành công. Chọn mẫu/generate không yêu cầu micro. Desktop/mobile 390 px không tràn ngang hoặc lỗi JavaScript.
- 257 kiểm thử Python đạt, 1 kiểm tra CUDA thật bỏ qua do không có GPU. Bao gồm tự chọn CUDA/CPU, phép đo và cấu hình gắn phần cứng, Qwen offload/rollback, CPU INT8, FFmpeg thật, SRT, worker, giới hạn 1 triệu ký tự, WAV 24 giờ và tải Range. Kết quả 1 giờ WAV trong kiểm thử streaming là dữ liệu thử, không phải đã tạo 1 giờ lời Hmong thật; cũng chưa tạo đủ 1 triệu ký tự bằng mô hình thật.
- 9 nhóm kiểm tra Chromium chạy lại đạt: lựa chọn chế độ/lọc ồn, dự án/API, tiến độ lọc ồn, hiển thị chế độ xử lý, Dừng, 1 triệu ký tự, tải WAV lớn và mobile. 8 kiểm tra micro đã đạt ở 0.6.0; phần micro không thay đổi ở 0.7.0.
- Mô hình Hmong đầy đủ với wrapper tra chữ mới được chạy cưỡng bức trên CPU để kiểm tra phép tính: WAV nữ Review + Nhẹ 2,110 giây giống từng byte với WAV Chuẩn 0.6.0, SHA256 `49f40eacdae0bfcc86c372672cfccc6716fad571a3fe76eaf51954fa8f256a17`. Đây là kiểm tra giữ kết quả, không phải phép đo tăng tốc CUDA.
- Tín hiệu thử cho thấy lọc Nhẹ giảm ù 50 Hz khoảng 3,9 dB và nhiễu cao tần khoảng 2,2 dB, giữ biên độ các thành phần 500/1.500 Hz gần mức gốc. Đây là kiểm tra tín hiệu tổng hợp; cảm nhận giọng trong hơn và phát âm Hmong vẫn cần bạn nghe đánh giá. Đã kiểm tra giữ âm thanh ở 5 ms cuối và vị trí bắt đầu SRT tới độ chính xác 1 ms.
- Đã thử thiếu toàn bộ 12 tệp rỗng trên snapshot thật: xác minh đủ 118 tệp mà không gọi mạng hay sửa trọng số lớn. Bản 0.4.1 đã qua kiểm tra môi trường do bộ cài tạo và 8 kiểm tra micro trong Chromium. Đã giải mã WAV và xác minh tín hiệu khác 0; kết quả này không thay thế việc nghe chất lượng/phát âm.

## Nguồn và kỹ thuật

Mô hình: https://huggingface.co/Xuajpaj2026/hmong-tts-weights , revision `5663e0df2589c2ca2403cd327a52702c3ff96e8f`. Tác giả có cấu hình chỉ dẫn White Hmong RPA. Source/license CosyVoice và Matcha được giữ trong snapshot; không chạy wrapper sửa checkpoint của tác giả. App chỉ nạp cấu hình suy luận đã kiểm tra; không cài thành phần huấn luyện CUDA/pyworld.

Mặc định snapshot nằm trong `.data/models/hmong-cosy`; có thể đặt `HMONG_COSY_DIR` trỏ tới snapshot đã xác minh. Chạy Linux: cài Torch/Torchaudio 2.6 CPU khớp nhau, `pip install -r requirements-cosy.txt`, `python prepare_clone_model.py`, rồi `python -m uvicorn app:app --host 127.0.0.1 --port 8090 --no-access-log`. FFmpeg/ffprobe cần có trong PATH. Không công khai trực tiếp dịch vụ lên Internet; app chưa có đăng nhập.

Bộ tải có thể tiếp tục tệp `.part` và chỉ ghi marker ready sau khi toàn bộ checksum đạt. Mã suy luận đặt chế độ offline trước khi nạp thư viện Hub. Nếu chủ động cấu hình `HMONG_CLONE_URL`/`HMONG_TTS_URL`, mẫu/lời có thể gửi tới dịch vụ đó khi dùng luồng từ xa; khi CosyVoice cục bộ sẵn sàng thì mẫu nam/nữ và mẫu riêng ưu tiên xử lý cục bộ.

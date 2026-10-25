# Hmong Nhanh 0.5.0

Bản gọn dùng **MO_HMONG_NHANH.bat** để đọc văn bản Hmong bằng hai mẫu Nam/Nữ riêng. Bản 0.5 nhận tối đa **1.000.000 ký tự Unicode**, lưu tiến độ để tiếp tục sau khi dừng hoặc mở lại, và xuất các phần WAV dài tối đa khoảng 30 phút.

[Tải gói Hmong-Nhanh-da-sua.zip](https://github.com/seotro95/seotro/raw/refs/heads/codex/hmong-nhanh-0.5.0/Hmong-Nhanh-da-sua.zip).

## Sử dụng

1. Giải nén toàn bộ gói vào thư mục mới. Cài Python 3.12 64-bit kèm Python Launcher nếu máy chưa có, rồi mở **MO_HMONG_NHANH.bat**.
2. Lần đầu cần Internet để tải thư viện và mô hình F5-Hmong/Vocos, khoảng 1,4 GB trọng số chưa tính thư viện. Bộ CUDA cần thêm vài GB. Giữ cửa sổ lệnh mở; các lần sau dùng lại dữ liệu đã tải.
3. Chọn **Nam** hoặc **Nữ**, mở **Chuẩn bị mẫu**, chọn đoạn rõ lời 3–8 giây và lưu lời chép đúng của đoạn đó. Làm một lần cho mỗi giọng. Hai mẫu gốc độc lập; chưa có lời chép đã được xác nhận nên công cụ không tự đoán nội dung mẫu.
4. Nhập văn bản hoặc tệp TXT UTF-8 tối đa 8 MB và 1.000.000 ký tự. Chọn cách kể, chế độ tạo giọng, nhịp đọc; nên **Đo tốc độ máy** và nghe thử trước khi chạy bản dài.
5. Bấm **Tạo giọng nói**. Nghe hoặc tải từng phần WAV đã hoàn tất. Bấm **Dừng**, rồi **Tiếp tục từ đoạn đã lưu** khi cần; đoạn đang tạo dở sẽ được làm lại. Một bản đọc được xử lý tại một thời điểm.

## Kiểu đọc và tăng tốc

| Lựa chọn | Tác dụng |
| --- | --- |
| Tự nhiên, Kể chuyện, Review phim, Tin tức, Quảng cáo, Thư giãn | Điều chỉnh nhịp đọc và khoảng nghỉ giữa các đoạn xử lý; không tự viết kịch bản hoặc tạo cảm xúc bằng mô hình mới. |
| Bản nháp / Nhanh / Cân bằng / Chất lượng | 4 / 8 / 16 / 32 bước tính toán; mặc định Nhanh 8 bước. Ít bước có thể giảm độ rõ hoặc độ giống giọng. |
| Nhịp đọc | Thay đổi nhanh/chậm của lời nói. |
| Đo tốc độ máy | Tạo một câu ngắn và hiển thị tốc độ đo được cùng ước tính thời gian tạo một giờ âm thanh. |

Công cụ giữ mô hình và mẫu đã xử lý trong bộ nhớ giữa các lượt. Văn bản dài được chia thành các đoạn nhỏ; ghép WAV theo từng phần trên đĩa và phát trực tiếp từng phần, tránh giữ toàn bộ bản đọc trong bộ nhớ.

Bộ cài tự chọn CUDA khi GPU NVIDIA và driver tương thích, kể cả nâng từ bộ CPU đã có. Không có GPU dùng được thì chạy CPU. Để giữ CPU, chạy `MO_HMONG_NHANH.bat --cpu` trong CMD tại thư mục công cụ; `--gpu` yêu cầu kiểm tra GPU. Giao diện báo thiết bị thực tế; thấy card NVIDIA chưa đồng nghĩa CUDA đã sẵn sàng.

## Số đo thực tế và giới hạn

**Chưa xác nhận đạt mục tiêu 1 giờ voice trong 2 phút (30× thời gian thực).** Các mẫu sau chạy trên cùng máy CPU, dùng một câu ngắn và mẫu tham chiếu công khai có lời chép đi kèm:

| Lượt đo | Thời gian xử lý | Âm thanh tạo được |
| --- | ---: | ---: |
| Bản trước, 32 bước | 162,590 giây | 3,232 giây |
| Bản 0.5, 8 bước, lượt đầu | 59,528 giây | 3,467 giây |
| Bản 0.5, 8 bước, mô hình đã nạp | 55,949 giây | 3,467 giây |

Thời gian lượt đầu giảm khoảng 2,7 lần trong các mẫu này; lượt đã nạp đạt khoảng **0,062× thời gian thực**, còn rất xa 30×. Các lần sinh ngẫu nhiên độc lập không phải so sánh chất lượng có kiểm soát. Môi trường đo: Python 3.12.14, F5-TTS 1.1.22, PyTorch/torchaudio 2.6.0+cpu.

Đây là phép đo một câu ngắn: chưa đo đủ một giờ âm thanh, chưa tạo âm thanh thật cho toàn bộ 1.000.000 ký tự và chưa đo GPU. Ước tính thời gian một giờ trong giao diện là ngoại suy từ phần đã xử lý; khoảng lặng do kiểu đọc thêm vào không được tính là tăng tốc tạo lời nói. Hãy đo trên máy sử dụng trước khi lên lịch xuất bản dài.

F5-Hmong thật đã xuất WAV 24 kHz có âm thanh trong chế độ offline. Chưa kiểm chứng phát âm Hmong Trắng hoặc độ giống hai giọng người dùng vì thiếu lời chép chính xác của các đoạn tham chiếu. Chưa chạy tệp BAT trên Windows thật.

94 kiểm thử tự động đã đạt. Một lượt tích hợp thật đi qua API → tác vụ lưu trên đĩa → xử lý văn bản → F5-Hmong → tải phần WAV đã hoàn tất: Kể chuyện, Nhanh 8 bước, CPU; 83,147 giây xử lý cho 3,691 giây âm thanh. Lượt này dùng mẫu công khai và chạy cùng lúc với các công việc khác trên máy, nên chỉ dùng làm bằng chứng hoạt động, không phải so sánh tốc độ có kiểm soát.

## Dữ liệu và cập nhật

Khi mở bằng BAT, thư mục `.data` cạnh BAT giữ mô hình, mẫu đã lưu, văn bản, tiến độ và âm thanh. Tắt tool trước khi chép `.data` từ bản gọn cũ sang cạnh BAT của bản mới; giữ bản sao cũ đến khi kiểm tra xong. Nếu đã đặt `HMONG_STUDIO_DATA_DIR`, tiếp tục dùng đường dẫn đó. Thư mục `app` là phần cần thiết để chạy tool.

Một giờ WAV mono 24 kHz, 16-bit chiếm khoảng 173 MB. Giữ cả đoạn nhỏ để tiếp tục và các phần đã ghép cần khoảng **346 MB mỗi giờ thành phẩm**, chưa tính tệp tạm, mô hình, thư viện và bộ nhớ đệm. Bản đọc dài cần dung lượng tương ứng.

Gói chỉ giữ một lối mở chính và các tệp cần cho đọc giọng. Những màn hình video, nhận dạng, thu âm, biên tập và dịch vụ từ xa của các bản khác không nằm trong gói này. Giải nén không tự xóa thư mục công cụ cũ trên máy.

Mô hình tải từ HTTPS và được đối chiếu checksum; trọng số không nằm trong ZIP. Nguồn: [F5TTS-Hmong](https://huggingface.co/Pakorn2112/F5TTS-Hmong) và [Vocos](https://huggingface.co/charactr/vocos-mel-24khz). Hướng dẫn đi kèm gói: [HUONG_DAN.txt](hmong-nhanh/HUONG_DAN.txt).

Chromium đã kiểm tra giao diện với API mô phỏng, gồm nhập 1.000.000 ký tự Unicode, Nam/Nữ, dừng/tiếp tục và phát/tải từng phần.

Gói ZIP: 777,843 bytes; SHA-256 `b14bb8d3ce17a76d07f446ccfe255e8f4eebd5bbf71bc3f62e0014bcc6d884a6`. Không chứa dữ liệu chạy, trọng số, môi trường Python hoặc lời tham chiếu riêng đã lưu.

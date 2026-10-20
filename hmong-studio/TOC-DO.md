# Tốc độ tạo voice và mục tiêu 2 phút cho 1 giờ

Mục tiêu tương đương tạo âm thanh nhanh ít nhất 30 lần thời gian thực: 3.600 giây lời đọc mới trong 120 giây. Bản này **chưa đạt** mục tiêu đó. Không tính phát lại mẫu, thêm khoảng lặng, cắt lời hay tăng tốc giọng thành kết quả tăng tốc tính toán.

## ULTRA FAST 0.8.0

Giữ model và số bước/precision của Chuẩn, thêm cache PCM có checksum, preload, pause/resume và số đo tách lời mới/tái dùng. Cold tắt cache read kể cả đoạn lặp. Không có bằng chứng đạt 30× trên GTX 1060 6 GB. Xem `PERFORMANCE_REPORT.md` và `benchmark-results` cho kết quả thật; `BENCHMARK-ULTRA.bat` đo 1/5/15/30/60 phút và giữ rõ incomplete/unrun. Một worker/batch 1 theo giới hạn backend, không tạo nhiều model trên 6 GB VRAM.

## Bản 0.7.0 và GTX 1060 6 GB

Người dùng đã xác định NVIDIA GeForce GTX 1060 6 GB, driver 560.94. `CHAY-STUDIO.bat` giờ tự thử bộ máy CUDA 12.4 riêng, chỉ kích hoạt khi phép tính CUDA thật thành công. Nếu cài GPU thất bại, báo rõ rồi dùng CPU; không lặp lại bộ tải thất bại cho cùng GPU/driver và bộ phụ thuộc. `CAI-NVIDIA.bat` cho phép thử lại chủ động. Mô hình/giọng và môi trường cũ không bị ghi đè.

GPU tối đa 8 GiB dùng RAM cho bảng tra chữ Qwen và đầu ngôn ngữ dùng chung không được gọi. Với cấu hình ghim, bảng có 151.936 × 896 phần tử FP32, khoảng 0,507 GiB; đây là lượng trọng số không còn phải giữ trên VRAM, không phải số đo tổng VRAM hoặc tốc độ thực tế. Phép tra trả đúng embedding về GPU; các phần tạo giọng vẫn trên GPU. CPU mặc định không đổi. Kiểm thử mô hình Qwen nhỏ so khớp từng bit embedding, hidden states và KV cache, giữ tên/giá trị/tham chiếu trọng số.

GTX 1060 không có Tensor Cores/TF32; không mặc định coi AMP nhanh hơn FP32. Đóng Studio rồi chạy `DO-TOC-DO.bat`: nạp mô hình một lần, làm ấm từng chế độ, đo tạo mẫu nữ Review + Nhẹ cho FP32 và FP16. Chỉ xét WAV hợp lệ và thời gian đồng bộ CUDA; trừ 0,15 giây khoảng lặng được tool thêm cuối mẫu khỏi mẫu số thời lượng lời. Chọn chế độ có RTF thấp nhất, lưu gắn với GPU/thư viện/revision. WAV và `report.json` nằm trong `.data/runtime/speed-test`. Mẫu ngắn không xác nhận tạo đủ một giờ. Nếu lỗi bất thường/bị dừng thì không thay lựa chọn trước; nếu một chế độ hết VRAM thì có thể chọn chế độ còn lại đã tạo WAV hợp lệ.

Chưa có GPU thật/Windows trong môi trường kiểm thử để chạy phép đo đó. Không có số đo mới xác nhận 2 phút/giờ. Giảm VRAM và tự chọn CUDA giúp dùng tài nguyên hiện có; không thay mô hình lớn thành mô hình tốc độ 30×.

Từ bản 0.6.0 có lựa chọn **Nhanh CPU**: dùng INT8 cho riêng bộ sinh phổ, giữ bộ chọn token giọng và bản Chuẩn gốc. Bản nhanh được giữ trong RAM cho lượt kế tiếp, và bản Chuẩn được trả lại sau mỗi lượt. Đây là lựa chọn có thể đổi âm sắc, vì vậy mặc định vẫn là Chuẩn; trên GPU vẫn dùng AMP đã có. Lọc ồn Nhẹ là mặc định, có thể chuyển Mạnh/Tắt. Bộ lọc xử lý mẫu trước khi lấy đặc trưng và WAV cuối sau khi ghép, bù độ trễ và kiểm tra số mẫu để giữ SRT/đuôi câu. Không cài thêm dịch vụ trả phí hoặc sửa trọng số tải về.

Đo chạy thật bản 0.6.0 trên CPU đám mây 4 luồng, mô hình đã nạp, Review và Lọc ồn Nhẹ:

| Lượt | Giọng / chế độ | Thời gian tạo và lọc | WAV |
| --- | --- | ---: | ---: |
| 1 | Nữ / Chuẩn | 34,254 giây | 2,110 giây |
| 2 | Nữ / Nhanh CPU | 26,052 giây | 2,110 giây |
| 3 | Nam / Nhanh CPU / SRT | 24,858 giây | 2,700 giây |

Hai lượt nữ cùng lời và seed; lượt nhanh dùng mẫu nữ đã chuẩn bị và bao gồm lần tạo bản INT8 đầu tiên. Thời gian nạp mô hình riêng là 30,312 giây; RAM đỉnh quan sát khoảng 8,33 GiB. Đây là số đo mẫu ngắn trên máy kiểm thử, không phải tốc độ bảo đảm trên Xeon/Windows hoặc phép đo tạo đủ một giờ. Ba WAV thật nằm trong `examples` để bạn nghe chọn cấu hình. Tệp mẫu gốc giữ nguyên; sau mỗi lượt đã kiểm tra bộ sinh phổ Chuẩn được trả lại. Lượt SRT khớp đúng 2,700 giây và có khoảng lặng trước lời.

Các lựa chọn lọc ồn không thay độ dài âm thanh: Nhẹ giảm ù/nhiễu đều ở mức vừa, Mạnh có thể mất chi tiết nhỏ, Tắt giữ nguyên đầu ra mô hình. Không dùng bộ lọc như công cụ tách nhạc/người nói khác. Kiểm tra tín hiệu tổng hợp và thời điểm SRT đã đạt; chất lượng/phát âm Hmong và độ giống mẫu vẫn cần nghe đánh giá.

Bản 0.5.1 bỏ phép chiếu sang 151.936 từ ngôn ngữ mà CosyVoice tính rồi bỏ đi, chỉ dùng trạng thái ẩn cho bộ giải mã giọng. Trọng số và thuật toán chọn token giọng được giữ nguyên; ảnh chụp mô hình được ghim cũng không bị sửa.

Đo cặp trên cùng CPU đám mây 4 luồng, cùng seed, mẫu nữ, Review và lời “Nyob zoo, kuv hais lus Hmoob.”:

| Cấu hình | LLM | Sinh phổ âm | Vocoder | Tổng | WAV |
| --- | ---: | ---: | ---: | ---: | ---: |
| Trước sửa | 5,508 giây | 25,469 giây | 0,428 giây | 31,426 giây | 2,110 giây |
| Sau sửa | 4,632 giây | 25,754 giây | 0,361 giây | 30,760 giây | 2,110 giây |

Hai WAV có SHA256 giống hệt nhau. Đây là phép đo mẫu ngắn, không phải kiểm chứng tạo một giờ âm thanh và không phải số đo trên máy Xeon Windows của bạn. Chênh lệch tổng nhỏ vì phần sinh phổ âm vẫn chiếm phần lớn công việc. Không suy ra mức tăng tốc cố định cho mọi máy/kịch bản.

Mô hình hiện dùng 22 lớp DiT, 10 bước sinh phổ, cùng bộ giải mã token tuần tự. Xeon E5-2680 v4 và RAM 128 GB không đủ để bảo đảm 30 lần thời gian thực với cấu hình này. Bản Chuẩn giữ thiết lập hiện có; chỉ lựa chọn Nhanh CPU mới bật INT8. Không giảm số bước, cắt lời hoặc thêm khoảng lặng để tính thành tốc độ tạo lời mới.

Để kiểm tra lại GPU, chạy **`KIEM-TRA-GPU.bat`** và xem tên card cùng VRAM. Trong `dxdiag`, thông tin này nằm ở thẻ **Display/Hiển thị**. `CAI-NVIDIA.bat` có cấu hình CUDA riêng; chưa có GPU thực tế để đo trong phiên này, vì vậy chưa thể cam kết tốc độ.

Ngay cả số đo GPU công khai cũng phải đọc đúng phạm vi: [CosyVoice3 TensorRT-LLM chính thức](https://github.com/FunAudioLLM/CosyVoice/blob/main/runtime/triton_trtllm/README.Cosyvoice3.md) báo RTF 0,0501 ở batch 16 trên NVIDIA L20, tương đương khoảng 3 phút tạo mỗi giờ âm thanh. Mô hình cơ sở và môi trường Linux đó khác bản Hmong này; không dùng số đó làm cam kết cho Windows hoặc mọi card NVIDIA.

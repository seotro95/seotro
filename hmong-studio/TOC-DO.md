# Tốc độ tạo voice và mục tiêu 2 phút cho 1 giờ

Mục tiêu tương đương tạo âm thanh nhanh ít nhất 30 lần thời gian thực: 3.600 giây lời đọc mới trong 120 giây. Bản này **chưa đạt** mục tiêu đó. Không tính phát lại mẫu, thêm khoảng lặng, cắt lời hay tăng tốc giọng thành kết quả tăng tốc tính toán.

Bản 0.5.1 bỏ phép chiếu sang 151.936 từ ngôn ngữ mà CosyVoice tính rồi bỏ đi, chỉ dùng trạng thái ẩn cho bộ giải mã giọng. Trọng số và thuật toán chọn token giọng được giữ nguyên; ảnh chụp mô hình được ghim cũng không bị sửa.

Đo cặp trên cùng CPU đám mây 4 luồng, cùng seed, mẫu nữ, Review và lời “Nyob zoo, kuv hais lus Hmoob.”:

| Cấu hình | LLM | Sinh phổ âm | Vocoder | Tổng | WAV |
| --- | ---: | ---: | ---: | ---: | ---: |
| Trước sửa | 5,508 giây | 25,469 giây | 0,428 giây | 31,426 giây | 2,110 giây |
| Sau sửa | 4,632 giây | 25,754 giây | 0,361 giây | 30,760 giây | 2,110 giây |

Hai WAV có SHA256 giống hệt nhau. Đây là phép đo mẫu ngắn, không phải kiểm chứng tạo một giờ âm thanh và không phải số đo trên máy Xeon Windows của bạn. Chênh lệch tổng nhỏ vì phần sinh phổ âm vẫn chiếm phần lớn công việc. Không suy ra mức tăng tốc cố định cho mọi máy/kịch bản.

Mô hình hiện dùng 22 lớp DiT, 10 bước sinh phổ, cùng bộ giải mã token tuần tự. Xeon E5-2680 v4 và RAM 128 GB không đủ để bảo đảm 30 lần thời gian thực với cấu hình này. Giảm số bước, rút ngắn mẫu hoặc lượng tử hóa có thể đổi chất lượng; bản phát hành không tự thay các thiết lập đó để báo tốc độ đẹp hơn.

Để xác định hướng GPU, chạy **`KIEM-TRA-GPU.bat`** và xem tên card cùng VRAM. Trong `dxdiag`, thông tin này nằm ở thẻ **Display/Hiển thị**, không nằm trong ảnh thẻ System bạn đã gửi. Nếu có NVIDIA tương thích, `CAI-NVIDIA.bat` có cấu hình CUDA riêng; chưa có GPU thực tế để đo trong phiên này, vì vậy chưa thể cam kết tốc độ.

Ngay cả số đo GPU công khai cũng phải đọc đúng phạm vi: [CosyVoice3 TensorRT-LLM chính thức](https://github.com/FunAudioLLM/CosyVoice/blob/main/runtime/triton_trtllm/README.Cosyvoice3.md) báo RTF 0,0501 ở batch 16 trên NVIDIA L20, tương đương khoảng 3 phút tạo mỗi giờ âm thanh. Mô hình cơ sở và môi trường Linux đó khác bản Hmong này; không dùng số đó làm cam kết cho Windows hoặc mọi card NVIDIA.

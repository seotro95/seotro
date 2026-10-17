# Đo hiệu năng nhân bản tiếng Việt · 1.1.0

## Kết quả trọn tác vụ

Trên máy thử Linux AMD EPYC 9V45, hạn mức **4 lõi CPU, 32 GiB RAM**, không dùng NVIDIA:

| Kiểm tra | Kết quả |
| --- | --- |
| Văn bản | 80.053 ký tự, 844 đoạn, lời kể tổng hợp có thay đổi nội dung |
| Giọng | Nhân bản từ mẫu âm thanh tổng hợp do chính tool tạo; không phải mẫu người thật |
| Mô hình | VieNeu Nano FP32 gốc, 4 bước, CFG mặc định, 4 tiến trình × 1 luồng |
| Đầu ra WAV | **3.896,6 giây = 64 phút 56,6 giây** |
| Thời gian xử lý trên server | **80,458 giây** |
| Thời gian từ gửi tác vụ tới nhận hoàn tất | **80,498 giây** |
| Tốc độ trọn luồng | **48,4× thời gian thực** |
| Xuất thêm MP3 qua API | 11,614 giây; codec MP3 và thời lượng được FFprobe xác minh |
| Tổng tạo WAV và xuất MP3 | **92,112 giây**, dưới 2 phút |
| Kết quả mục tiêu 1 giờ / 2 phút | Đạt trong phép đo này, với đầu ra dài hơn 1 giờ |

Mô hình và bộ mã hóa mẫu giọng được nạp từ trạng thái worker lạnh trong phép đo; các trọng số đã tải sẵn. Không tính thời gian cài thư viện, tải mô hình hoặc chờ một tác vụ khác trong hàng đợi. Mỗi đoạn được suy luận mới, không dùng lại checkpoint hay lặp tệp WAV. Không đổi tốc độ phát, không chèn khoảng lặng để tăng thời lượng. Các đoạn được ghép đúng thứ tự; TXT/SRT xuất ra khớp kế hoạch đoạn đọc, đủ 844 đoạn, không chạm giới hạn thời lượng. Dữ liệu kiểm tra chi tiết nằm trong `BENCHMARK_RESULT.json`.

## Cách tăng tốc

- Mã hóa mẫu giọng một lần mỗi tiến trình, sau đó dùng lại embedding khi đọc các đoạn mới. Mã hóa mẫu lặp lại từng đoạn có thể tốn khoảng 0,8 giây mỗi lần trong phép đo riêng.
- Nạp và giữ mô hình trong RAM, xử lý nhiều đoạn đồng thời rồi ghép có thứ tự. Hàng đợi có giới hạn để tránh tích quá nhiều tác vụ.
- Tự chọn số tiến trình và luồng theo CPU/RAM. Không nhân số luồng ONNX với số tiến trình vượt ngân sách CPU.
- Chế độ ưu tiên tốc độ dùng 4 bước, giọng Nano nhân bản, WAV, tốc độ đọc 1× và không thêm khoảng nghỉ giữa các đoạn.

## Giới hạn của kết quả

Đây là phép đo trên **máy thử nêu trên**, chưa đo trực tiếp máy Windows của bạn. CPU yếu hơn, ít RAM hơn, 8/16 bước, nhịp kể chuyện, nhấn từ, mẫu giọng khác hoặc căn mốc SRT có thể làm thời gian khác đi. Giọng Nano 4 bước có thể giảm độ tự nhiên và độ giống giọng so với cấu hình chất lượng cao hơn; cần nghe thử. Đầu vào mẫu tổng hợp kiểm tra được đường xử lý nhân bản, không chứng minh mức độ giống một người nói thật.

Kết quả tốc độ không chứng minh phát âm đúng từng từ. Kiểm tra tự động xác minh tệp âm thanh hợp lệ, thứ tự đoạn và nội dung TXT/SRT; chưa đánh giá bằng tai hoặc ASR. Chọn **Đo tốc độ thực** để đo mẫu trên máy của bạn. Báo cáo cho mẫu ngắn là ước tính; chỉ đánh dấu kiểm chứng một giờ khi đã thực sự tạo ít nhất 3.600 giây lời đọc mới trong tối đa 120 giây. Tác vụ tiếp tục từ checkpoint và SRT có căn nhịp không dùng để xác nhận mục tiêu này.

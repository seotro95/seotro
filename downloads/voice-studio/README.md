# Voice Studio Riêng 1.1 · Nhân bản tiếng Việt trên CPU

**[Tải bản cập nhật 1.1 cho Windows 10/11 x64](./Voice-Studio-Rieng-1.1.0-Windows-10-11.zip?raw=true)**

Giải nén toàn bộ ZIP. Gói cần Python 3.12 64-bit và Internet để cài thư viện/tải mô hình lần đầu. Mã nguồn có thể xem trong [voice-studio-standalone](../../voice-studio-standalone).

## Dùng giọng nhân bản nhanh

1. Nếu cài mới, chạy `CAI_DAT.bat`.
2. Chạy `TAI_GIONG_NHAN_BAN_NHANH.bat` một lần để chuẩn bị mô hình nhân bản Nano.
3. Chạy `MO_TOOL.bat`, chọn mẫu giọng tiếng Việt của bạn rồi bấm **Ưu tiên tốc độ**. Tool giữ nguyên mẫu, dùng Nano 4 bước và CPU tự động.
4. Bấm **Đo tốc độ thực** để đo trên máy hoặc **Tạo giọng nói** để xử lý văn bản.

Giới hạn 200.000 ký tự mỗi tác vụ, nhập TXT/SRT và xuất WAV/MP3/TXT/SRT. Giọng tiêu chuẩn, quốc tế và Windows vẫn có lựa chọn riêng. Nano 4 bước có thể giảm độ tự nhiên/độ giống giọng; nghe thử rồi chọn 8/16 bước hoặc nhân bản tiêu chuẩn khi cần.

## Kết quả kiểm chứng

Máy thử Linux AMD EPYC có hạn mức **4 lõi CPU / 32 GiB RAM**, không dùng NVIDIA, đã tạo **64 phút 56,6 giây âm thanh nhân bản trong 80,5 giây**, gồm nạp mô hình và mã hóa mẫu từ worker lạnh. Tạo WAV rồi xuất thêm MP3 tổng **92,1 giây**. Đủ 844 đoạn từ 80.053 ký tự, không dùng lại WAV, không chèn khoảng lặng để tăng số đo. Mẫu giọng kiểm tra là âm thanh tổng hợp do tool tạo; chưa đánh giá mức độ giống người thật hay phát âm từng từ.

Đây là kết quả trên máy thử, **chưa kiểm chứng trực tiếp máy Windows của bạn**. Xem [HIEU_NANG.md](../../voice-studio-standalone/HIEU_NANG.md) và [BENCHMARK_RESULT.json](../../voice-studio-standalone/BENCHMARK_RESULT.json) để biết cách đo.

## Cập nhật an toàn

Tắt tool, sao lưu `app/.data`, rồi chép tệp mới vào thư mục cũ; giữ nguyên `.venv` và `app/.data`. Chạy bộ tải nhân bản nhanh và mở lại tool, kiểm tra phiên bản 1.1.0. Hướng dẫn đầy đủ trong [DOC_TRUOC.md](../../voice-studio-standalone/DOC_TRUOC.md).

Gói không chứa môi trường Python đã cài, trọng số mô hình, dữ liệu giọng cá nhân hoặc API key. Tên ZIP không có số phiên bản được cập nhật thành cùng bản 1.1 để liên kết tải cũ tiếp tục dùng được.

SHA256: `4b6917e46c16beee0fe8ef6eb470a01cbe6b303f8dc5ee4b274f6e855af2a158`

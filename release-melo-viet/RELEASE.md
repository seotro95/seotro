Sửa bộ cài riêng **MeloTTS + VieNeu Turbo Việt** khi WSL đăng ký tên `Ubuntu` nhưng hệ điều hành bên trong là Ubuntu 22.04.5. **Không cần cài lại Ubuntu hoặc xóa bản Linux đang có.**

1. Tải ZIP bên dưới, giải nén toàn bộ vào thư mục cố định, ví dụ `D:\Melo-Viet-1.0.1`.
2. Nhấp đôi `CAI_DAT.bat`. Bộ cài tự chọn `Ubuntu-22.04` hoặc `Ubuntu` đã cài và kiểm tra hệ điều hành là Ubuntu 22.04. Tên được lưu vào `wsl-distro.txt` để lần mở sau dùng đúng bản đó.
3. Nhập mật khẩu Linux khi sudo hỏi, chờ cài xong. Chạy `MO_TOOL.bat`, mở `http://localhost:8817`.

Nếu `wsl -d Ubuntu -- cat /etc/os-release` hiện `VERSION_ID="22.04"`, bạn đã có đúng hệ điều hành. `Stopped` trong danh sách WSL là bình thường. **Không chạy lại `wsl --install -d Ubuntu-22.04`** trong trường hợp này. Nếu tên WSL khác, ghi tên đó vào `wsl-distro.txt`. Không đổi bản WSL mặc định, không tự cài thêm hoặc nâng cấp Ubuntu.

ZIP nhỏ là **bộ cài**, chưa chứa mô hình hoặc thư viện. Cần Internet khi cài và tải mô hình lần đầu; nên có ít nhất 15 GB trống. Mô hình, môi trường và WAV đã có trong `~/.local/share/melo-viet-local` được giữ lại; chạy lại bộ cài không xóa dữ liệu. Không cần khóa Azure.

Các tiếng: VI dùng VieNeu Turbo FP32; EN, FR, JP, KR, ES, ZH dùng MeloTTS. Không gồm tiếng Nga/Thái hoặc nhân bản 19 mẫu riêng. Bộ đọc, khóa phụ thuộc và quy trình cài thư viện giống 1.0.0; bản 1.0.1 sửa nhận diện WSL, thông báo lỗi và hướng dẫn.

Kiểm tra: 30 kiểm thử ứng dụng/API/PCM và 11 tình huống launcher trên Windows PowerShell 5.1 với WSL giả lập. Chưa chạy thao tác cài WSL trên máy Windows của bạn. Cài đặt Ubuntu 22.04 và tổng hợp thật 14 WAV / bảy ngôn ngữ đã được kiểm tra ở bản 1.0.0 (Actions run 41337929203); `MODEL-QA-1.0.0.json` là báo cáo cũ được giữ nguyên, không phải số đo mới.

Các số đo CPU Linux ở bản 1.0.0: MeloTTS khoảng 0,64–0,67× theo độ dài WAV ở lượt thứ hai; VieNeu Việt khoảng 2,15×. **Chưa đạt 30×**, chưa có đánh giá nghe bởi người bản ngữ cho mọi giọng và không bảo đảm tốc độ trên Windows/Xeon của bạn. Bản vá launcher không thay đổi tốc độ tổng hợp.

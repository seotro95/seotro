# Muse AI Studio 1.4.10 · Bản Windows đầy đủ

[Bản Windows x64 đầy đủ](Muse-AI-Studio-Windows-x64.zip) · [Mã nguồn đầy đủ](Muse-Video-Workstation.zip) · [Hướng dẫn](muse-video-studio/README.md)

1. Giải nén **toàn bộ** bản Windows vào một thư mục mới.
2. Mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Không cần Node.js, npm, Chrome hoặc bản cũ.
3. Đăng nhập Muse ngay trong tool, bấm **← Về Studio** rồi **Kiểm tra phiên**.
4. Nhập prompt hoặc TXT/SRT, chọn ảnh/video, bấm **TẠO 10 ẢNH / VIDEO**.

Không chép `.data`, `.env`, `node_modules` hoặc tệp chương trình từ bản cũ. Gói mới có runtime và các thư viện cần thiết; tạo hồ sơ đăng nhập mới khi chạy. Thanh trên và tiêu đề cửa sổ hiện **1.4.10**.

Bản 1.4.10 thêm **số thứ tự tải tự tăng**, dùng chung cho tải riêng, lịch sử và các tệp trong ZIP. Bộ đầu 1–10, bộ sau 11–20; tiếp tục qua 1.000 và lớn hơn, giữ khi mở lại cùng hồ sơ. Tên ZIP cũng ghi dải số; mã riêng của bản cài tránh trùng với tệp từ hồ sơ khác. Không cần nhập số hoặc xác nhận thêm.

**Tải tất cả** vẫn là một lần bấm tải **một tệp ZIP** chứa các kết quả đang chọn trong các ô. Đủ 10 sẽ có đủ 10 tệp; chưa đủ thì tải phần đã hoàn tất với đúng số cảnh. Ảnh trong ZIP là PNG thật, video giữ nguyên định dạng. Không cần bấm tải từng ô.

Giữ **Tạo/Dừng riêng từng ô**, cho phép thêm cảnh khi ô khác đang chạy. Phần **Kết quả đã lưu** giữ các ảnh/video trước trên máy, gồm thời gian và prompt; bấm chọn để xem, tải hoặc xóa từng bản. Đóng/mở lại cùng hồ sơ vẫn giữ kết quả.

Có lựa chọn **1/2/3/5/10 luồng**. Tool kiểm tra các địa chỉ hội thoại riêng trước khi bật song song, không gửi prompt tạo nội dung trong bước kiểm tra. Nếu Muse chỉ có một hội thoại chung thì giữ 1 luồng và báo rõ; không khẳng định tài khoản Muse cho 10 render đồng thời. Các bản PNG tải xuống là PNG thực sự; ảnh trùng cảnh khác không được tính là kết quả mới.

Một tài khoản, 10 cảnh với số luồng được kiểm tra; hạn mức thực tế, mô hình, độ nét và khả năng tạo media do Muse quyết định. Kết nối giao diện không chính thức. Kiểm thử dùng dịch vụ giả lập; chưa xác minh tự động trên tài khoản Muse thật. Xem [kết quả kiểm thử](muse-video-studio/VALIDATION.md).

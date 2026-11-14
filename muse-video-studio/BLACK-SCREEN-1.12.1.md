# Muse AI Studio 1.12.1 — Khôi phục giao diện Studio

Bản dành cho trường hợp thanh công cụ vẫn hiện, trang đăng nhập Muse mở được nhưng vùng Studio bị đen trong 1.12.0.

- Gắn và bố trí lại vùng Studio sau khi thanh công cụ đã tải. Nút **← Về Studio** đưa đúng vùng Studio lên trước và cập nhật lại kích thước.
- Kết nối giao diện Studio với máy chủ trên chính máy được đặt trực tiếp; proxy của từng tài khoản Muse tiếp tục dùng riêng.
- Hiện trạng thái đang tải, lỗi tải trang, lỗi cầu nối, lỗi giao diện hoặc tiến trình bị dừng. Nếu giao diện không báo sẵn sàng trong 20 giây, hiện nút **Tải lại Studio** và **Sao chép chẩn đoán Studio**.
- Tải lại riêng giao diện. Không cho tải lại khi đang có tác vụ tạo nội dung. Giữ hồ sơ đăng nhập, prompt và thư viện đã ghi trên máy.
- Có thêm **MO_STUDIO_KHONG_GPU.bat** để thử tương thích hiển thị. Đóng ứng dụng trước khi dùng tệp này. Chế độ này có thể làm xem video tốn CPU hơn.

## Cách mở

1. Đóng hoàn toàn Muse 1.12.0.
2. Giải nén toàn bộ ZIP 1.12.1 vào một thư mục mới.
3. Mở **Muse AI Studio.exe**. Giữ nguyên `%LOCALAPPDATA%\Muse AI Studio` để dùng lại dữ liệu và tài khoản.
4. Nếu Studio báo lỗi, bấm **Tải lại Studio**. Nếu lỗi còn lặp lại, bấm **Sao chép chẩn đoán Studio** và gửi nội dung báo cáo để xác định bước bị lỗi. Báo cáo chỉ có phiên bản, mã trạng thái và trạng thái tăng tốc hiển thị.
5. Nếu vẫn gặp vấn đề hiển thị, đóng ứng dụng rồi mở **MO_STUDIO_KHONG_GPU.bat**.

Ảnh lỗi của người dùng chưa đủ để khẳng định nguyên nhân trên máy Windows của họ. Mã nguồn và tệp giao diện đóng gói của 1.12.0 tải được trong môi trường thử nghiệm. Bản này sửa vòng đời hiển thị và bổ sung khôi phục/chẩn đoán; cần mở trên máy gặp lỗi để xác nhận kết quả cuối cùng. Kiểm thử dùng dịch vụ Muse giả lập, không tạo nội dung hoặc xác minh hạn mức trên Muse thật.

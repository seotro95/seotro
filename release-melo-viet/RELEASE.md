Bản nâng cấp dành cho **Melo + Việt Studio 1.2.0 đang dùng tốt**: thêm lựa chọn giọng thật, MP3, phần trăm tiến độ và nhấn nhá; giữ mô hình, bản thu và báo cáo cũ.

- **5 nam + 5 nữ cho 31 ngôn ngữ** bằng bộ Supertonic 3 trên máy (CPU INT8, tùy chọn Đa giọng). Các preset thật được dùng chung giữa các ngôn ngữ. Giọng Piper FP32, Melo và VieNeu cũ vẫn có thể chọn như trước.
- Thêm **22 mô hình Piper**, tổng **49 mô hình / 51 preset thực**, cùng 25 preset VieNeu Việt khi SDK đã cài. Lọc Nam/Nữ/Chưa phân loại, lưu giọng yêu thích và nhớ lựa chọn. Supertonic chưa hỗ trợ Trung, Na Uy, Ba Tư, Catalan; các tiếng này giữ bộ đọc cũ. Nút thêm giọng trực tuyến mở đúng locale khi dịch vụ có cung cấp.
- **Tải MP3 192 kbps**, xuất toàn bản kể cả khi WAV chia nhiều phần; có tiến độ, dừng và tải lại. WAV gốc được giữ.
- **Hiện % tạo voice**, chia văn bản dài, hàng đợi nhiều bản và lịch sử. 100% sau khi ghép xong; đang tải/nạp lần đầu có thể ở 0%.
- Kiểu **Thân thiện**, nhấn nhá theo dấu câu và **cụm từ** đánh dấu để đọc chậm nhẹ/rõ hơn. Điều chỉnh nhịp và âm lượng có giới hạn, không phải mô hình cảm xúc riêng; cần Nghe thử để chọn chất giọng phù hợp.
- **Hmong RPA thử nghiệm**: một giọng từ mô hình TTS Hmong cộng đồng, có mẫu thật kèm dưới. **Chưa xác minh phương ngữ Hmong Trắng hoặc giới tính bằng người nghe bản ngữ.** Trọng số Hmong tải trực tiếp từ nguồn gốc lần đầu dùng, không nằm trong ZIP. Không thay bằng giọng Việt/Anh.

**Tải cho máy đang dùng 1.2.0:** `Melo-Viet-Studio-1.3.0-Them-Giong-Windows.zip` chứa chương trình mới + 22 mô hình Piper bổ sung + Supertonic 3; giữ 27 mô hình cũ đã có. Không chứa lại mọi trọng số 1.2.0. `Cap-Nhat-Windows.zip` nhỏ chỉ có chương trình và tải đúng mô hình được chọn khi cần. Cả hai gói cập nhật thư viện cần Internet. Các model cards/giấy phép nguồn được giữ; bộ Hmong nguồn chưa công bố rõ giấy phép nên không phân phối lại trọng số.

**Cập nhật:** đóng cửa sổ tool → giải nén toàn bộ ZIP mới → chạy **CAP_NHAT.bat** → **MO_TOOL.bat** trong thư mục mới → Ctrl+F5, kiểm tra **v1.3.0**. **Không cài lại Ubuntu, không xóa models/outputs.** Chọn **Trên máy → Đa giọng** để xem 5 nam/5 nữ, chọn Hmong RPA ở mục Ngôn ngữ để thử Hmong. Bấm **Nghe thử** trước khi làm bản dài.

Không cam kết mọi quốc gia đều có đủ giọng nam/nữ ngoại tuyến hoặc mọi giọng đều hợp tai. Không có phép đo tốc độ 30× đã xác minh trên máy Xeon/Windows của bạn. Các số đo CI là tổng hợp CPU mới trên Linux, không dùng tăng tốc phát hay đổi báo cáo cũ.

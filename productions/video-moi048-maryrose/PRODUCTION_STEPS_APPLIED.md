# Quy trình áp dụng — MỚI-048 Mary Rose

1. Tạo tập riêng, giữ danh mục cũ và các tập MỚI-011, 022, 027, 030; không tự chạy chủ đề kế tiếp.
2. Đọc nguồn chủ yếu từ Mary Rose Trust; ghi phần đã đọc, điều chưa chắc và các số liệu không dùng trong NGUON_KIEM_CHUNG.md.
3. Viết lời Anh mới theo công thức người dùng; hòm minh họa và thao tác bản sao không bị gọi là tổ hợp khảo cổ thật.
4. Căn 131 mốc Anh, 138 cảnh sử dụng + 2 dự phòng, 14 TXT × 10; mở 10 cảnh trong 30 giây. Mỗi prompt clip 10 giây, camera riêng, không trẻ em/âm/lời; ngoài trời là chính, không lab.
5. Tạo bản chuyển thể ngắn gọn nhưng giữ các quan hệ và giới hạn bằng chứng theo 13 chương dùng chung. Việt viết lại với Nam Minh; các ngôn ngữ khác chuyển ngữ từ nguồn ngữ cảnh đã làm rõ, rà các đoạn kỹ thuật và quét lỗi lẫn tiếng Anh. Không tự nhận có biên tập/kiểm nghe bản ngữ độc lập.
6. Dùng backend online đã khóa của Melo-Viet-Studio 1.3.1 qua edge-tts, không UI Windows hay model Melo đa ngôn ngữ cục bộ. Giữ 16 ID nam từ hồ sơ trước, native phrase rate nhẹ, pitch không đổi; kiểm word metadata, không cắt mất từ để ép thời lượng.
7. Tái dùng raw speech thành công khi có lỗi tạm thời. Nếu chương dồn lời quá ngưỡng, rút câu lặp và sửa lời chuyển thể, không nới ngưỡng tốc độ hoặc đổi giọng. Kiểm FFmpeg đủ 62.496.000 mẫu mono 48 kHz = 21:42 từng MP3.
8. Phát hành tài liệu/prompt và từng MP3 theo tên quốc gia, ZIP 16 giọng, TXT link, QA/checksum; tải lại công khai và kiểm ZIP, giải mã audio, ID và hash script.
9. Lưu bản đọc được, profile và trạng thái trên GitHub; kiểm các blob cũ được giữ, chỉ cập nhật hai tệp trạng thái/profile chung. Lưu cách tiếp tục, không tự đánh dấu footage/thumbnail/MP4 đã tạo.

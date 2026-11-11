# AutoDoc Studio1.0

Ứng dụng Windows tự dựng phim tài liệu từ một voice và thư mục video. Giao diện tiếng Việt, chạy cục bộ, không cần API trả phí. Chọn voice, thư mục video, nơi lưu rồi bấm **TỰ DỰNG VIDEO**.

Tool dùng Whisper để nhận dạng lời và CLIP ONNX để so khớp lời với ba mẫu hình của từng đoạn video. Chọn10cảnh trong30giây đầu khi đủ nguồn, xếp các cảnh sau theo nội dung/ranh câu và giảm lặp. Voice giữ nguyên thời gian/cao độ, chỉ chuẩn hóa độ lớn; toàn bộ tiếng clip gốc bị loại. Thiếu nguồn thì tái dùng video chuyển động liên quan; không tạo ảnh đứng/bảng chữ để bù. Có cắt cảnh, hòa hình ngắn, crop nhẹ khi dùng lại và fade cuối.

## Chạy bản Windows portable

1. Giải nén ZIP vào thư mục có quyền ghi. Giữ nguyên thư mục `_internal` cạnh `AutoDocStudio.exe`.
2. Mở AutoDocStudio.exe hoặc MO_TOOL.bat. Không cần cài Python cho bản portable.
3. Chọn voiceAnh,thư mục video và thư mục xuất. Chọn720p để dựng nhanh hơn hoặc1080p. Bấm TỰ DỰNG VIDEO.
4. Lần đầu cần Internet tải FFmpeg khoảng80–100MBnén,model Whisper khoảng145MB và CLIP khoảng156MB. Những lần sau dùng model đã lưu trong `%LOCALAPPDATA%\AutoDocStudio\models`. Không cần tải model mỗi tập.
5. Kết quả ở thư mục `AutoDoc_<mã dự án>`: VIDEO_HOAN_CHINH.mp4,LOI_DOC.srt,TIMELINE.csv,EDIT_PLAN.json và KIEM_TRA_VIDEO.json. Phụ đề mặc định không chèn vào hình; có thể chọn kèm đường phụ đề tùy chọn.

Windows10/11 64-bit, khuyến nghị8GBRAM và CPU4luồng trở lên. Không bắt buộc GPU. Tốc độ phụ thuộc CPU,số đoạn nguồn,độ phân giải và độ dài voice; tool không cam kết dựng tức thì. Chọn ổ xuất đủ dung lượng cho cache và video. Model cần mạng ở lần đầu; phiên hoàn toàn ngoại tuyến chỉ chạy được khi model đã tải đủ.

Nguồn được giữ nguyên. Dừng giữ các đoạn đã làm để lần sau tiếp tục khi cùng đầu vào/cài đặt. Không sửa/xóa file gốc. Cache và đường dẫn nguồn chỉ nằm trên máy,không tự upload lên server hoặc GitHub. Khi chia sẻ project JSON,kiểm tra đường dẫn cục bộ trước.

## Phạm vi và giới hạn

Đây là tự động xếp hình theo tương đồng,không phải người biên tập hiểu chắc mọi kết luận khảo cổ. Lời mơ hồ,đại từ hoặc clip không có cảnh liên quan sẽ giảm độ khớp. Cần xem kết quả trước khi đăng,nhất là khoa học/niên đại/giả thuyết. Lọc trẻ em/bảng chữ bằng CLIP là ước lượng và có thể sót hoặc loại nhầm;không phải bộ xác nhận độ tuổi/OCR. Hãy cung cấp bộ nguồn đã kiểm tra không có trẻ em khi yêu cầu đó là bắt buộc.

Nếu ít hơn10nguồn hợp lệ,tool có thể dùng những đoạn khác nhau từ cùng video và ghi trong báo cáo;không tuyên bố có10nguồn khác nhau khi không đủ. Nếu mọi nguồn bị lọc hoặc hỏng,tool báo lỗi rõ thay vì tự thêm ảnh/bảng chữ. Clip ngắn có thể lặp chuyển động; các mốc đó được ghi trong timeline.

Whisper nhận dạng tốt nhất với voiceAnh rõ. Ngôn ngữ tự động vẫn nhận lời nhưng CLIP này chủ yếu so khớp tiếngAnh;videoAnh là cấu hình được khuyến nghị. Không cần đưa kịch bản,SRT,prompt hoặc APIkey. Có thể lưu SRT và timeline để người dùng kiểm tra nhưng chúng không phải đầu vào bắt buộc.

## Chạy mã nguồn

Python3.12 + FFmpeg/ffprobe + `pip install -r requirements.txt`. Windows có thể dùng CAI_DAT.bat rồi MO_TOOL.bat. Nếu không có FFmpeg trong PATH,đặt ffmpeg.exe và ffprobe.exe vào `bin`.

`python main.py --doctor`

`python main.py --voice "D:\voice.mp3" --videos "D:\clips" --output "D:\ket_qua" --resolution 720`

Chạy không tham số để mở giao diện. `python -m unittest discover -s tests` chạy kiểm tra quy hoạch/cancel. Có thể dùng `--clip-model-path` và `--whisper-model-path` để trỏ model đã lưu,không cần tải lại.

Mã nguồn tách khỏi nội dung người dùng;không kèm video/voice cá nhân hoặc clip nguồn trong bản phần mềm. Xem THIRD_PARTY.md về model và FFmpeg.

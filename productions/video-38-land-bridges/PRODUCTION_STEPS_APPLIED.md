# Chủ đề 38 — Hồ sơ tiếp tục sản xuất

Chủ đề đã lưu: **Các cây cầu đất xuất hiện và biến mất qua những chu kỳ băng hà**.
Tên kịch bản Anh: **When the Sea Was Land: Earth's Vanishing Bridges**.
Thời lượng yêu cầu: **22:32 = 1.352 giây**.

## Tài liệu và mã nguồn

- Kho: https://github.com/seotro95/seotro
- Nhánh sản xuất: `codex/land-bridges38-production-20261111`, thư mục `episode38/`.
- Hồ sơ chung của chuỗi: nhánh `codex/beringia-video-01`, thư mục `productions/series/`.
- Bản phát hành: https://github.com/seotro95/seotro/releases/tag/land-bridges-video-38-22m32s
- Lượt tạo voice chính: https://github.com/seotro95/seotro/actions/runs/43050614061
- Không tự chuyển sang một chủ đề khác. Chỉ đánh dấu hoàn tất khi các tệp tải công khai đã qua kiểm tra.

## Nội dung và cách kể

Đã xem lại các bảng khung hình và hồ sơ phân tích của video tham khảo. Dùng cấu trúc câu hỏi → bằng chứng → cơ chế → giới hạn hiểu biết → trở lại câu hỏi đầu. Kịch bản mới có 3.581 từ Anh, không chép lời dẫn hoặc lấy cảnh từ video tham khảo.

Mở đầu bằng đường đi bị nước che phủ. Phần thân đi từ nước bị giữ trong băng đến thềm lục địa, Beringia, Doggerland, Sunda, Sahul, mực biển địa phương và cách nghiên cứu cảnh quan chìm. Phân biệt đất liền được nối với một tuyến di chuyển thực sự sử dụng được. Không mô tả một đường đi bộ hoàn toàn từ châu Á đến Australia; các eo sâu ở Wallacea vẫn tồn tại.

Nguồn và phạm vi chắc chắn của thông tin nằm trong `NGUON_KIEM_CHUNG.md`. Không giả các mô hình minh họa thành bản đồ hoặc hồ sơ nghiên cứu thật.

## Kịch bản và prompt

- 136 mốc lời: 135 mốc 10 giây và mốc cuối 2 giây.
- 120 bối cảnh mới: 12 TXT, mỗi TXT có 10 prompt.
- 16 mốc dùng lại đã đánh dấu `REUSE` trong timeline.
- Tên clip theo **ID prompt**, từ `001.mp4` đến `120.mp4`; ID prompt khác ID mốc lời.
- Mỗi prompt tạo một cảnh chuyển động 10 giây, khung 16:9, một hành động và một chuyển động máy phù hợp.
- Không có trẻ em hoặc thiếu niên, kể cả nền, phản chiếu, ảnh, màn hình và hình mô hình.
- Không có lời nói, nhạc, hiệu ứng âm thanh hoặc audio stream. Mỗi prompt kết thúc bằng `không có âm thanh`.
- Cảnh cuối chỉ dùng 2 giây của clip 001; không nối cả clip 10 giây vào cuối phim.

## Dịch và giữ giọng

Hồ sơ nhận diện giọng: `science-prehistory-17-v1`. Dùng đúng 16 giọng nam đã khóa và nữ H'mông `hmong-female-3`; không đổi giọng để xử lý lỗi kết nối.

- Tool đa ngôn ngữ: Melo-Viet-Studio 1.3.1, backend được ghim tại commit `4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043`.
- Tool H'mông: Voice-Studio-Hmong 1.6.6 tại commit `061430d958b8d5fc14d04209c6f0cd20492382c2`.
- SHA-256 tham chiếu nữ H'mông: `ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17`.
- Bản nguồn dịch đã làm rõ các thuật ngữ dễ nhầm. Các bản dịch được chỉnh thuật ngữ; toàn bộ 14 chương H'mông được viết lại. Không chạy lại dịch tự động rồi ghi đè các bản đã sửa.
- Tên MP3 theo quốc gia; Anh là bản chính, Bồ Đào Nha dùng giọng Portugal.
- Nhấn nhá bằng nhịp câu hỏi, câu suy ngẫm, khoảng nghỉ và nhấn từ nhẹ; không đổi pitch hoặc nhận diện giọng.
- Bản Anh giữ 136 mốc. Các bản dịch giữ 14 ranh giới chương: 13 chương 100 giây và chương cuối 52 giây. Cùng thời lượng không có nghĩa từng từ trùng thời điểm.
- Đầu ra mono 48 kHz, MP3 96 kb/s, đích loudness -19 LUFS, true peak -2 dBTP.
- Mỗi MP3 phải giải mã thành **64.896.000 mẫu**, đúng 1.352 giây. Kiểm tra cả hash, nội dung metadata từ đọc và mã giọng.
- Kiểm kỹ thuật không thay thế việc nghe và biên tập bản ngữ. Phương ngữ H'mông Trắng chưa được người bản ngữ xác nhận độc lập.

## Sửa lỗi đã áp dụng

GitHub Ubuntu mới thiếu FFmpeg. Workflow dùng `imageio-ffmpeg==0.6.0` và `ensure_ffmpeg.py` để cung cấp FFmpeg portable đã chạy thử; không phụ thuộc lệnh cài hệ thống bị treo.

Dịch vụ Edge có thể trả `NoAudioReceived` theo đợt. Mỗi yêu cầu thử tối đa 5 lần, có khoảng đợi tăng dần và giới hạn tổng thời gian. Dừng khi gặp HTTP 401, 403 hoặc 429. Giữ các đoạn WAV hoàn tất và metadata để sửa hoặc chạy lại riêng phần lỗi. Không đổi giọng, tắt TLS hoặc tìm đường vòng dịch vụ.

H'mông chạy độc lập bằng mô hình native và tham chiếu có hash cố định. Chỉ công bố gói đủ 17 giọng sau khi tất cả vượt kiểm tra.

## Khi người dùng cung cấp footage

Tập này hiện chưa có footage được cung cấp và chưa có MP4 hoàn chỉnh. Khi có clip:

1. Đọc timeline và đối chiếu nội dung thực tế của từng clip với lời Anh.
2. Chọn 10 cảnh mạnh, liên quan, cắt thành 30 giây mở đầu nằm trong tổng 22:32. Danh sách hiện tại chỉ là kế hoạch, phải xem clip thật trước khi chốt.
3. Cắt theo ý lời; luân phiên toàn cảnh, cận vật chứng, thao tác nghiên cứu và mô hình. Dùng hòa hình ngắn có chủ đích và bù phần chồng lấn.
4. Xóa toàn bộ âm thanh clip gốc. Phim chính chỉ có voice tiếng Anh, không thêm nhạc hoặc tiếng hiệu ứng.
5. Cảnh thiếu được thay bằng **video chuyển động liên quan**, không dùng ảnh tĩnh hoặc thẻ chữ để lấp chỗ trống.
6. Giữ đúng thời lượng của voice, kiểm tra đầu/cuối và các ranh giới chương, xuất video và xác minh bản tải công khai.

## Hoàn tất tiếng Anh theo nhóm

Lượt sửa tuần tự 43055537796 đã dừng có lưu checkpoint với ít nhất 50/136 đoạn Anh. Quy trình 43059788576 chia 136 mốc thành bốn nhóm liên tiếp, mỗi nhóm 34 mốc, tối đa hai nhóm đồng thời. Mỗi nhóm chỉ tải lại đoạn thiếu hoặc sai chữ ký; các nhóm lưu cache riêng, không ghi đè nhau. Bước ghép cuối kiểm tra chữ ký nội dung, giọng và nhịp đọc trước khi dựng đủ 136 mốc rồi kiểm tra 64.896.000 mẫu ở 48 kHz.

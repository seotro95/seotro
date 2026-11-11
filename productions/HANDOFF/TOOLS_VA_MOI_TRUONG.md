# Công cụ và phần cần nối lại ở tài khoản mới

Tài khoản mới cần tự có khả năng đọc ZIP/tệp và truy cập GitHub công khai. Nếu muốn tổng hợp voice, chạy ffmpeg, lưu repo hoặc chạy Actions, cần công cụ tương ứng và quyền GitHub được kết nối trong phiên mới. Không chuyển được đăng nhập, bộ nhớ tài khoản, các job đang chạy hoặc workspace bằng một prompt.

Backend đã dùng cho16giọng nam: online_backend của Melo-Viet-Studio1.3.1, providerEdge, không phải mở EXE giao diện Windows từ chat. Sourcecommit4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043; ba file online_backend.py/documents.py/timing.py được ghim URL/SHA trong CAU_HINH/source_integrity.json. Các voiceID và provider không được tự đổi sang một engine khác rồi gọi là cùng giọng. Pipeline dùng edge-tts7.3.1, ffmpeg/ffprobe, Python; các bản nam chạy bằng GitHub Actions và có checkpoint.

H’Mông: Voice-Studio-Hmong1.6.6, sourcecommit061430d958b8d5fc14d04209c6f0cd20492382c2, đường dẫn voice-studio trong repo. NativeVITS+OpenVoiceV2, hmong-female-3, presetclear-v1. Mẫu tham chiếu: https://raw.githubusercontent.com/seotro95/seotro/061430d958b8d5fc14d04209c6f0cd20492382c2/voice-studio/assets/hmong/female-3.wav ; SHA256ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17. File/mô hình lớn không kèm trong gói, đọc cấu hình tool trước khi tải đúng bản. Chưa xác nhận độc lập phương ngữ H’Mông Trắng.

Môi trường phiên trước là Linux trong/workspace, có ffmpeg/ffprobe, Python và các venv riêng. Đường dẫn/workspace/work/... trong script là đường dẫn máy cũ; phải ánh xạ lại ở máy/phiên mới trước khi chạy. Không giả định những venv, model hoặc file clip đó tồn tại ở tài khoản mới. Khi dựng trên Windows, sửa đường dẫn font tương đối trong script thay cho font Linux nếu cần.

Các script được đính kèm để tham khảo và tái lập có kiểm soát. Script staging/phát hành có thể ghi GitHub hoặc tạo release; không tự chạy khi chỉ nhập ngữ cảnh. Kiểm commit/sourcehash, nội dung request hiện tại, thời lượng và đường dẫn trước khi dùng cho tập mới. Không mang hằng số1215giây/122mốc của19 sang mọi tập.

File movie, MP3 và dự án dựng tập19 được tải từ release công khai trong TIEN_DO_VA_LINK_TAI.md. Dự án dựng có voiceAnh và chỉ dẫn nối lại clip bằng hash, không có rawclip. File đính kèm cũ của cuộc trò chuyện không tự xuất hiện ở chat mới: người dùng giữ nguồn đã tải và gửi lại clip khi muốn dựng/sửa từ nguồn.

Khi không có công cụ: có thể đọc hồ sơ, lên kịch bản/prompt và cung cấp script chạy được; phải nói rõ chưa chạy tổng hợp/render và không dựng link giả. Không gửi mật khẩu, token hoặc cookie trong chat hay đóng gói vào ZIP.

## Tool edit đã nâng cấp: AutoDoc Studio 2.0.1

Windows portable: https://github.com/seotro95/seotro/releases/tag/autodoc-studio-v2.0.1 . Mã nguồn hiện hành tại `tools/autodoc-studio`; cấu hình và link tải tại `productions/series/EDITING_TOOL.json`. Báo cáo kiểm tra EXE, preview và hash file tải tại `tools/autodoc-studio/QA/2.0.1/`.

Đầu vào: voice chính, thư mục ảnh/video, TXT/SRT tùy chọn và logo tùy chọn. Tự xếp cảnh, chọn từng cảnh để xem hình và nghe đúng đoạn voice; sửa nguồn, điểm lấy, tốc độ, cắt/phóng, tâm cắt, chia/gộp, chuyển cảnh và hiệu ứng. Lưu dự án JSON rồi bấm Xuất để chọn MP4/MKV,720/1080p,FPS,chất lượng,CPU/GPU và nơi lưu. Mặc định chỉ có voice; có thể bỏ chọn tắt tiếng clip để trộn tiếng nguồn. Có kiểu phụ đề burn, phụ đề mềm hoặc không phụ đề. Gói preset bổ sung tự tải theo manifest chính thức và kiểm SHA256.

Có SRT đúng mốc thì bỏ qua nhận dạng voice. Cache AI dùng lại giữa dự án; cache từng cảnh giảm dựng lại. Giữ các nguồn và cache đúng đường dẫn để mở lại JSON. Dự án v1 không nhập trực tiếp vào schema v2; bản v1 và hồ sơ 17 giọng vẫn được giữ. Không sửa các voiceID/preset đã khóa khi chỉ nâng cấp tool edit. Lọc trẻ em và chọn hình theo lời vẫn là ước lượng, cần xem lại trước đăng.

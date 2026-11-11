# Công cụ và phần cần nối lại ở tài khoản mới

Tài khoản mới cần tự có khả năng đọc ZIP/tệp và truy cập GitHub công khai. Nếu muốn tổng hợp voice, chạy ffmpeg, lưu repo hoặc chạy Actions, cần công cụ tương ứng và quyền GitHub được kết nối trong phiên mới. Không chuyển được đăng nhập, bộ nhớ tài khoản, các job đang chạy hoặc workspace bằng một prompt.

Backend đã dùng cho16giọng nam: online_backend của Melo-Viet-Studio1.3.1, providerEdge, không phải mở EXE giao diện Windows từ chat. Sourcecommit4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043; ba file online_backend.py/documents.py/timing.py được ghim URL/SHA trong CAU_HINH/source_integrity.json. Các voiceID và provider không được tự đổi sang một engine khác rồi gọi là cùng giọng. Pipeline dùng edge-tts7.3.1, ffmpeg/ffprobe, Python; các bản nam chạy bằng GitHub Actions và có checkpoint.

H’Mông: Voice-Studio-Hmong1.6.6, sourcecommit061430d958b8d5fc14d04209c6f0cd20492382c2, đường dẫn voice-studio trong repo. NativeVITS+OpenVoiceV2, hmong-female-3, presetclear-v1. Mẫu tham chiếu: https://raw.githubusercontent.com/seotro95/seotro/061430d958b8d5fc14d04209c6f0cd20492382c2/voice-studio/assets/hmong/female-3.wav ; SHA256ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17. File/mô hình lớn không kèm trong gói, đọc cấu hình tool trước khi tải đúng bản. Chưa xác nhận độc lập phương ngữ H’Mông Trắng.

Môi trường phiên trước là Linux trong/workspace, có ffmpeg/ffprobe, Python và các venv riêng. Đường dẫn/workspace/work/... trong script là đường dẫn máy cũ; phải ánh xạ lại ở máy/phiên mới trước khi chạy. Không giả định những venv, model hoặc file clip đó tồn tại ở tài khoản mới. Khi dựng trên Windows, sửa đường dẫn font tương đối trong script thay cho font Linux nếu cần.

Các script được đính kèm để tham khảo và tái lập có kiểm soát. Script staging/phát hành có thể ghi GitHub hoặc tạo release; không tự chạy khi chỉ nhập ngữ cảnh. Kiểm commit/sourcehash, nội dung request hiện tại, thời lượng và đường dẫn trước khi dùng cho tập mới. Không mang hằng số1215giây/122mốc của19 sang mọi tập.

File movie, MP3 và dự án dựng tập19 được tải từ release công khai trong TIEN_DO_VA_LINK_TAI.md. Dự án dựng có voiceAnh và chỉ dẫn nối lại clip bằng hash, không có rawclip. File đính kèm cũ của cuộc trò chuyện không tự xuất hiện ở chat mới: người dùng giữ nguồn đã tải và gửi lại clip khi muốn dựng/sửa từ nguồn.

Khi không có công cụ: có thể đọc hồ sơ, lên kịch bản/prompt và cung cấp script chạy được; phải nói rõ chưa chạy tổng hợp/render và không dựng link giả. Không gửi mật khẩu, token hoặc cookie trong chat hay đóng gói vào ZIP.

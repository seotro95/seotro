# Mã tạo giọng tập 3

Lưu mã để tái lập cách đọc có nhấn nhá. Giữ các source commit và SHA của backend, voice ID và mẫu Hmong trong hồ sơ. Không có credential trong các tệp này. Native models tải bằng cơ chế xác thực mã nguồn của tool người dùng.

Các script này là bản của tập 3: đường dẫn mặc định /workspace/work/malta, tiền tố MALTA_03, mục tiêu1200s/120cue và12chương. Khi làm tập mới, đổi cấu hình tập và lời, đo lại thời lượng; không đổi giọng hay dùng audio tập cũ cho nội dung mới. render_common và render_online nhận PRODUCTION_WORK_DIR; MELO_TOOL_DIR trỏ backend đã xác minh. Hmong dùng đường dẫn tool/model riêng được ghi trong renderer.

prosody.py là adapter quanh backend gốc, không chèn SSML vào văn bản. Có thay đổi tốc độ/nghỉ và nhấn âm lượng theo mốc từ khi có; giữ cao độ. Hmong không có mốc từng từ hoặc mô hình cảm xúc.

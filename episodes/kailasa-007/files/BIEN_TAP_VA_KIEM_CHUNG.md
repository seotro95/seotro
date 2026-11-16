# Biên tập, kiểm tra và cách dùng báo cáo

## Kịch bản và dịch

Tập 007 được viết mới bằng tiếng Anh, đối chiếu tiếng Việt và định vị 135 cue theo hình. Mười bốn bản còn lại được biên tập trực tiếp theo từng cue Anh cho ngôn ngữ đích. Không dùng hồ sơ bản dịch nháp của tập Baalbek để đại diện cho tập này. Các bản giữ chung thứ tự luận điểm, các nhãn giả định và hai phép tính 2,8/280 tấn, dùng câu ngắn phù hợp khung 10 giây.

Tiếng Na Uy dùng Bokmål; Bồ Đào Nha theo Portugal; tiếng Tây Ban Nha dùng biến thể Spain. Các giọng Nhật, Hàn và Ý dùng cùng preset nam M1 của Supertonic nhưng mỗi bản phát âm ngôn ngữ tương ứng. “Cùng preset” không có nghĩa cùng âm thanh hoặc cùng bản dịch.

Có biên tập ngôn từ và đối chiếu ý từng cue. **Chưa có người bản ngữ độc lập nghe trọn toàn bộ 16 tệp**. Không gọi kết quả này là chứng nhận phát âm, bản dịch bản ngữ đã duyệt hoặc bản lồng tiếng thương mại đã kiểm định. Có thể nghe lại mẫu và toàn bộ trước khi xuất bản, đặc biệt tên Kailasa, Ellora, Krishna, Elapura và từ địa chất.

## Nguồn công cụ và giọng

Dùng mã backend từ Melo-Viet-Studio-1.3.1-Them-Giong-Windows của kho người dùng, thực thi Python trên Linux. Không giả lập thao tác chạy EXE/BAT Windows. `TOOL_PROVENANCE.json` ghi release nguồn, commit, Git blob và các thành phần model đã đối chiếu; `VOICE_PROFILES_LOCKED.json` ghi engine, locale, mã giọng nam và model hash để tái sử dụng.

Andrew `en-US-AndrewNeural` là bản chính; Nam Minh `vi-VN-NamMinhNeural` cho tiếng Việt. Không tự đổi sang giọng khác khi dịch vụ chậm. Đây là âm thanh tổng hợp mới cho Kailasa; không lấy audio Baalbek hay một file nhân bản cho các quốc gia.

## Kiểm tra kỹ thuật áp dụng cho cả 16 bản

- Tệp tồn tại, giải mã được, SHA-256 trùng báo cáo dựng.
- 135 cue đủ ID 1–135, mỗi text thực tế gửi TTS trùng lời giao cuối; chặn audio cũ sau khi sửa lời.
- Từng cue có waveform hữu hạn và năng lượng khác không; kiểm tra peak để phát hiện clipping cứng.
- Giữ toàn bộ phần lời; co giãn nhịp có giữ cao độ tối đa 1,5 lần. Cue quá dài phải biên tập lại rồi tạo lại, không cắt lời để vừa 10 giây.
- Master FLAC 24 kHz mono có đúng 32.448.000 sample; giải mã MP3 ra cùng số mẫu; 135 ô 10 giây và hai giây kết im lặng.
- Chuẩn hóa loudness hai lượt với đích -18 LUFS, true peak -2 dBTP; không khẳng định mọi đoạn có cùng loudness tức thời.
- Bảng CSV cung cấp thời lượng giải mã, peak và tempo tối đa của từng bản; đây là chỉ số đo, không đánh giá cảm xúc hoặc giọng bản địa.
- ZIP được thử CRC, tài sản tải lên GitHub được so dung lượng và SHA-256 phía máy chủ.

MP3 có delay/padding codec nên trường duration của container có thể lớn hơn 1.352 giây một lượng nhỏ. Bảng QA tách thời lượng container với thời lượng giải mã; timeline phim vẫn đúng 22:32.

Nếu có `asr-additional-*.json`, đó là kiểm tra nhận dạng tự động trên một số cue được chọn, không phải nghe toàn bộ. ASR có thể nhận sai tên riêng và số thập phân. Báo cáo chỉ được đưa vào khi hash trùng audio giao cuối; lỗi nhận dạng phải được đọc trong ngữ cảnh, không tự gọi là lỗi TTS hay chứng nhận chính xác.

## Kiểm tra prompt và ảnh xuất sau này

Kiểm tra đủ 136 số thứ tự, 14 TXT, mỗi prompt có điều kiện im lặng và không trẻ em. 135 clip dùng đủ 10 giây, clip 136 dùng hai giây đầu. Mỗi góc quay gắn với ý của cue tương ứng. Các điều kiện bắt buộc lặp trong từng prompt để có thể sử dụng độc lập.

Chưa tạo clip hoặc thumbnail trong gói này. Sau khi tạo hình, người dựng cần kiểm tra đúng Cave 16, các phần đền/sân, không có trẻ em kể cả tượng/phù điêu, không sai hình học đỡ mái, không dùng máy móc hiện đại trong phục dựng cổ và không có chữ bịa. Mô hình minh họa phải được ghi nhãn trong bản dựng; AI không tạo ra bằng chứng khảo cổ mới.

## Bảo toàn và tái sử dụng

Các voice ID được kế thừa bộ giọng đã lưu; thông tin lần xuất thành công mới được ghi thêm cho tập Kailasa. Những profile cũ ngoài 16 ngôn ngữ của yêu cầu hiện tại được giữ nguyên trong bộ nhớ công việc, không đưa thành audio bổ sung của tập này. Dịch vụ online có thể thay đổi phát âm theo thời gian; giữ voice ID không bảo đảm bit giống hệt trong tương lai.

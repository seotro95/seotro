# Quy trình cho chủ đề 2–100

## Nguồn sự thật

Đọc SERIES_STATE.json và danh sách 100 chủ đề đã lưu. Dùng đúng số và tên chủ đề người dùng yêu cầu. Làm một chủ đề tại một thời điểm; không tự tạo đồng loạt toàn bộ hàng đợi.

Chủ đề 1 được lưu tại productions/beringia-video-01. Danh sách gốc: productions/beringia-video-01/100_CHU_DE.txt. Video tham chiếu do người dùng cung cấp nằm ở release tag video; SHA-256 là f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c. Phân tích đã lưu; không cần yêu cầu người dùng gửi lại khi các nguồn này còn truy cập được.

## Kịch bản và hình

1. Nghiên cứu từng chủ đề bằng các nguồn thích hợp, ưu tiên công bố khoa học và cơ quan nghiên cứu. Kiểm tra ngày, địa danh, đơn vị và mức chắc chắn; không coi danh sách ý tưởng là 100 hồ sơ đã kiểm chứng.
2. Viết kịch bản mới tiếng Anh cho khoảng 20 phút. Tập 1 có 2.962 từ; độ dài từ chỉ dùng để dự tính, thời lượng voice phải đo thực tế.
3. Học cấu trúc video mẫu: chi tiết nhỏ có con người hoặc vật chứng → câu hỏi lớn → bài toán cụ thể → bằng chứng và giải thích → nối các phần → đoạn kết quay về câu hỏi mở. Luân phiên tái hiện, cận vật chứng, cảnh quan, bản đồ và phòng thí nghiệm theo ý lời. Không chép câu chữ, logo hoặc tự nhận mô hình AI nào là công cụ gốc của tác giả.
4. Chia 120 đoạn, ID 001–120, mốc dự kiến 10 giây. Tạo 120 prompt riêng có hành động, góc nhìn, chuyển động máy, bối cảnh và thời đại; mỗi prompt tạo clip 10 giây im lặng.
5. Đóng gói 12 TXT, mỗi TXT đúng 10 prompt. Bàn giao thêm kịch bản TXT, SRT dự kiến, shotlist và nguồn nghiên cứu.
6. Gửi các tệp tài liệu trước, sau đó mới tạo voice theo yêu cầu đã có. Không bắt người dùng xác nhận lại các lựa chọn đã lưu.
7. Phân biệt cảnh tái hiện và hình chứng cứ. Thêm số liệu, bản đồ chính xác và chữ trong edit. Clip 10 giây là nguyên liệu; có thể chia nhịp dựng mà giữ tổng 20 phút.

## Giọng và ngôn ngữ

Đọc VOICE_PROFILES_LOCKED.json. Tiếng Anh là bản chính. Giữ các locale en-US, vi-VN, es-ES, fr-FR, ja-JP, ko-KR, de-DE, it-IT, pt-PT, nl-NL, pl-PL, sv-SE, da-DK, fi-FI, nb-NO, cs-CZ và mww theo đúng hồ sơ. 16 giọng nam; Hmong là nữ.

- Các giọng ngoài Hmong đã được tạo bằng online_backend.py của Melo-Viet-Studio 1.3.1, commit 4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043, dùng Microsoft Edge qua edge-tts. Dùng ID thật từ hồ sơ và danh mục dịch vụ; không thay giọng âm thầm nếu dịch vụ không còn cung cấp.
- Hmong dùng Voice-Studio-Hmong 1.6.6, commit 061430d958b8d5fc14d04209c6f0cd20492382c2, bộ Native VITS + OpenVoice V2, preset hmong-female-3, audio_profile clear-v1, tốc độ native 1.0.
- Mẫu Hmong: voice-studio/assets/hmong/female-3.wav tại commit trên. SHA-256: ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17. Native nhận tham chiếu âm thanh, không bắt buộc lời mẫu như F5.
- Không nhầm giọng Hmong pilot trong Melo với preset Hmong nữ 3. Độ sẵn sàng kỹ thuật và giới tính theo hồ sơ không phải chứng nhận phương ngữ hay phát âm.
- Giữ chữ thanh điệu RPA. Kiểm tra tên riêng, số và thuật ngữ. Bản Hmong cần người bản ngữ kiểm tra; không dùng bản dịch có lỗi đã biết chỉ để đủ số tệp.
- Dịch và biên tập theo ngôn ngữ đích. Kiểm tra ngày ở dạng số trước khi cho đọc, đặc biệt cách viết năm như 2018 và 2023; phân biệt nghĩa khảo cổ của dating, địa chất của continental shelf, và human footprints.
- Tôn trọng giới hạn dịch vụ; giữ checkpoint để tiếp tục, không lặp yêu cầu lỗi liên tục hoặc hứa chất lượng bản ngữ khi chưa được kiểm tra.

## Thời lượng và kiểm tra

Giữ đầy đủ lời, không cắt đuôi để ép thời gian. Có thể biên tập lời cho gọn và dùng điều chỉnh tốc độ giữ cao độ trong mức nghe được; nếu không vừa thì sửa lời hoặc cách chia trước khi xuất.

Tập 1: bản Anh căn 120 ô 10 giây; các bản dịch căn 12 chương 100 giây. Chúng khớp tổng thời lượng, không được mô tả là căn chính xác từng từ giữa mọi ngôn ngữ.

Đo WAV/PCM và giải mã MP3 để kiểm tra lại. Mốc tham chiếu của tập 1 là 57.600.000 mẫu tại 48 kHz, tương đương 1.200 giây. Báo cáo phải ghi số thực đã đo, mã giọng, engine, hash tệp, cách căn và trạng thái rà soát ngôn ngữ. Không báo đã xong chỉ vì có SRT 20 phút.

## Lưu và tiếp nối

Tạo thư mục riêng cho mỗi tập; gợi ý productions/video-02-white-sands và productions/video-03-malta. Không ghi đè tài sản tập trước. Lưu giọng theo ngôn ngữ riêng, kèm lời dùng, SRT thực, báo cáo đo, manifest và hồ sơ tham chiếu.

Cập nhật trạng thái chủ đề vừa làm và next_topic_id sau khi bàn giao. Giữ trạng thái rà soát bản dịch/phương ngữ tách biệt với việc đã tạo tệp. Không ghi nhận video thành phẩm nếu chỉ mới có prompt và audio.

Lưu lại đường dẫn GitHub để người dùng có thể tiếp tục ở cuộc trò chuyện mới, kể cả khi môi trường chạy cũ không còn.

# Chủ đề 3 — Mal’ta, 20 phút

**Mal’ta: The Child Who Revealed a Missing Ancestry**

Đã hoàn tất kịch bản tiếng Anh gốc 3.087 từ, 100 prompt trong 10 TXT, 20 ô dùng lại và 17 voice riêng, mỗi bản đo đúng20:00 sau giải mã. Tất cả voice áp dụng yêu cầu đọc có nhấn nhá, giữ mã giọng và mẫu tham chiếu của các tập trước. Video chính chỉ dùng tiếng Anh. Đã hoàn tất bản dựng20:00, chỉ dùng voice Anh có nhấn nhá gốc, bỏ mọi âm thanh clip nguồn.

## Tải tài liệu và voice

- [ZIP kịch bản, prompt, timeline và bản đồ](https://github.com/seotro95/seotro/releases/download/malta-video-03-20min/MALTA_VIDEO_03_TAI_LIEU_20_PHUT.zip)
- [Kịch bản tiếng Anh](KICH_BAN_EN_20_PHUT.txt) · [120 mốc lời](KICH_BAN_EN_CO_MOC.txt)
- [100 prompt trong10 TXT](PROMPTS/) · [Timeline120 cảnh](TIMELINE_120_CANH.csv)
- [20 ô dùng lại, không tạo clip mới](CANH_DUNG_LAI_KHONG_TAO_MOI.csv)
- [Kế hoạch8 shot cho30 giây đầu](HOOK_30_GIAY_8_SHOT.csv)
- [ZIP đủ17 voice có nhấn nhá](https://github.com/seotro95/seotro/releases/download/malta-video-03-20min/MALTA_03_17_VOICES_TEN_QUOC_GIA.zip)
- [Bảng tải riêng từng ngôn ngữ](VOICES/README.md) · [Voice Anh đầy đủ20 phút](https://github.com/seotro95/seotro/releases/download/malta-video-03-20min/MALTA_03_My_Tieng_Anh.mp3)
- [Bản dịch, báo cáo và phụ đề thời gian](https://github.com/seotro95/seotro/releases/download/malta-video-03-20min/MALTA_03_HO_SO_GIONG_TEN_QUOC_GIA.zip)
- [Hồ sơ giọng](VOICES/VOICE_PROFILES_LOCKED.json) · [Hồ sơ nhấn nhá](VOICES/NARRATION_STYLE_LOCKED.json) · [Manifest audio](VOICES/AUDIO_MANIFEST.json)

## Phong cách đọc

science-documentary-expressive-v1: giọng kể tài liệu thân thiện, câu hỏi dẫn chuyện rõ, nhịp chậm nhẹ ở bằng chứng và đoạn kết, nghỉ theo ý.16 giọng nam dùng backend của Melo-Viet-Studio1.3.1 với adapter tốc độ và mốc từ do Edge trả về để nhấn âm lượng nhẹ. Hmong nữ3 dùng Voice-Studio-Hmong1.6.6 Native VITS+OpenVoice V2, điều khiển theo cụm. Giữ nguyên ID/mẫu giọng, không dịch cao độ; không tự nhận engine có mô hình cảm xúc hoặc Hmong có mốc từng từ. Các điều khiển được ghi trong hồ sơ.

Từng tệp được kiểm tra đúng57.600.000 mẫu ở48 kHz=1.200 giây sau giải mã. Tiếng Anh căn120 ô10 s; các bản dịch căn12 chương100 s. Khớp tổng và chương không phải căn từng từ giữa mọi ngôn ngữ. Tốc độ hậu kỳ được tính lại cho tập này.

## Dựng hình

Bộ prompt gốc dự kiến100 clip MA03_001.mp4 đến MA03_100.mp4. Bản dựng thực tế kiểm kê100 clip đã nhận, chọn66 clip phù hợp và bổ sung17 đồ hoạ; tra EDIT/EDIT_TIMELINE.csv để xem nguồn từng shot. Số clip khác số cảnh001–120. Tra cộtclip_id để đặt đúng hình, bỏ toàn bộ âm thanh clip, ghép voice Anh. Kế hoạch30 giây mở đầu chỉ thay cách đặt hình, không cộng thời gian intro. Các cảnhAI/replica/sơđồ là minh hoạ; không coi đó là ảnh khai quật hay chân dung xác thực của đứa trẻ. Bản đồ hiện đại từNatural Earth và NPS21.000 BP được chú thích riêng, không coi là đường bờ24.000 năm chính xác hoặc tuyến đi của MA-1. Thêm toàn bộ chữ, nhãn, số liệu trong editor.

## Trạng thái ngôn ngữ và tiếp nối

Bản Việt và Hmong đã được trợ lý viết lại để sửa các lỗi thuật ngữ đã phát hiện; các ngôn ngữ khác đã kiểm tra mốc và thuật ngữ quan trọng. Các bản dịch vẫn cần người bản ngữ nghe/đọc rà soát. Phương ngữ H’Mông Trắng chưa được xác nhận độc lập. Kiểm tra file phát được và đủ phút không thay cho kiểm định ngôn ngữ.

ZIP tài liệu gốc và MANIFEST.json ở thư mục gốc là bản chụp lúc bàn giao tài liệu trước khi tạo voice, không phải manifest cho mọi tệp được cập nhật sau đó. Manifest audio hoàn tất là VOICES/AUDIO_MANIFEST.json. Cập nhật phong cách và hồ sơ audio hoàn tất nằm trong VOICES. Đã lưu trạng thái để lần sau tiếp tục chủ đề4—Yana; chưa bắt đầu tập4.

## Quy trình cho các tập sau

Đã lưu [quy trình áp dụng từ tập3](../series/QUY_TRINH_AP_DUNG_TU_CHU_DE_03.md), [các bước thực tế của tập3](PRODUCTION_STEPS_APPLIED.md) và [quy tắc tên voice theo quốc gia](../series/VOICE_FILE_NAMING.json). Các bản dịch, báo cáo chi tiết và SRT tải trong ZIP hồ sơ giọng; bảng tải trên đây dùng tên quốc gia/ngôn ngữ.


## Video hoàn chỉnh

- [Tải video20:00,720p/24fps](https://github.com/seotro95/seotro/releases/download/malta-video-03-final-20min/MALTA_03_EN_FINAL_20m_720p.mp4)
- [Tải đoạn mở đầu30giây](https://github.com/seotro95/seotro/releases/download/malta-video-03-final-20min/MALTA_03_OPENING_30s.mp4)
- [Project dựng, voice Anh gốc, đồ hoạ, code và timeline](https://github.com/seotro95/seotro/releases/download/malta-video-03-final-20min/MALTA_03_EDIT_PROJECT.zip)
- [5 tiêu đề và5 promptthumbnail](https://github.com/seotro95/seotro/releases/download/malta-video-03-final-20min/TITLES_AND_THUMBNAIL_PROMPTS.txt)
- [Báo cáo QA](https://github.com/seotro95/seotro/releases/download/malta-video-03-final-20min/FINAL_VIDEO_QA.json)

Mở đầu8shot trong đúng30giây của voice; không nối intro, không nhạc/SFX hoặc tiếng từ clip.12chương,120mốc lời10s, phụ đề Anh bật/tắt. Giữ bản sắc, nhịp và cao độ của voice có nhấn nhá đã bàn giao; chỉ cân bằng âm lượng.

Đã sửa lỗi khép đa giác qua kinh tuyến180° trên3nền Natural Earth cũ. Thư mục REFERENCES hiện tại và project dựng chứa nền đúng; ZIP tài liệu kịch bản ban đầu là bản chụp cũ, nên dùng nền mới khi tạo composite. NPS bathymetry vẫn giữ nguyênnhãn21.000BP và credit, không phải bản đồ tuyến đi của MA-1 hoặc bờ24.000năm chính xác. Sơ đồ gene là minh hoạ, không phải số liệu đo thật, tỷ lệ gene phổ quát hoặc phả hệ trực tiếp từ đứa trẻ.

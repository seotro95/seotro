# Mal’ta — chủ đề 3, bản dựng hoàn chỉnh 20:00

MALTA_03_EN_FINAL_20m_720p.mp4: H.264, 1280×720, 24fps, AAC 48kHz. Chỉ có voice tiếng Anh gốc đã có nhấn nhá (en-US-AndrewNeural, science-documentary-expressive-v1). Không tạo lại giọng, đổi cao độ hay thay tốc độ; chỉ cân bằng âm lượng. Không nhạc, SFX hoặc tiếng từ clip nguồn. Phụ đề tiếng Anh có thể bật/tắt và có SRT riêng. 120 mốc lời, mỗi mốc10s; 12 chương100s.

Mở đầu8shot/30s: hạt trang sức → bàn tay chế tác → người và thung lũng Siberia → mô hình bối cảnh chôn cất không có thi thể → đồ trang sức replica → hộp lưu trữ → thao tác phòng thí nghiệm → bản đồ quan hệ tổ tiên. Giữ nguyên thời gian voice, không nối thêm intro. Phần còn lại dùng cắt thẳng, cutaway theo lời kể,5 chuyển cảnh ngắn ở đổi bối cảnh và đoạn kết, tiêu đề chương, chú thích và sơ đồ có nhãn.

Đã kiểm kê100 clip10s, chọn66 clip phù hợp và bổ sung17 đồ hoạ.30 clip đầu vào có audio; toàn bộ audio clip bị loại khỏi đường tiếng cuối. EDIT_TIMELINE.csv ghi vị trí, nguồn, source-in và thời lượng từng shot. SOURCE_CLIP_MANIFEST.csv ghi SHA256 và clip nào được dùng. Cảnh có bản đồ sai, biểu đồ giả, mẫu xương sai loại hoặc không phù hợp lời kể đã được thay. HìnhAI, hiện vật replica và cảnh thực nghiệm đều là minh hoạ; không coi là ghi hình thực địa gốc, mẫu MA-1 thật hoặc chân dung xác thực của đứa trẻ.

Đã sửa lỗi khép mảnh đa giác khi hiển thị đường bờ quanh kinh tuyến180° trên3 nền bản đồ cũ. Bản cuối dùng vòng đa giác Natural Earth nguyên vẹn và bản sao dịch kinh độ cả vòng; không cuộn từng điểm rồi nối tắt qua Siberia. Nền bờ biển/hồ là địa lý hiện đại tổng quát. NPS bathymetry giữ nguyên nhãn và credit khoảng21.000BP, không coi là bờ24.000năm hay tuyến đi của MA-1. Dòng nối nét đứt chỉ quan hệ di truyền, không phải hành trình đã chứng minh. Sơ đồ gene không phải kết quả đo thật, tỷ lệ tổ tiên phổ quát hoặc phả hệ cá nhân.

FINAL_VIDEO_QA.json ghi kiểm tra thời lượng, frame, số đường tiếng, đồng bộ dạng sóng ở13 vị trí, loudness và giải mã toàn bộ. Rà hình bằng ảnh tổng quan100 clip và lấy mẫu phần mở đầu, đồ hoạ, các chương, đoạn kết; không tuyên bố đã xem thủ công liên tục cả20phút.

MALTA_03_EDIT_PROJECT.zip chứa kế hoạch dựng, code, đồ hoạ, overlay, voice Anh gốc, phụ đề, hồ sơ nguồn, ảnh kiểm tra và nền bản đồ đã sửa. Không đóng lại100 clip nguồn: giữ tệp người dùng upload để tái dựng. Khi chuyển máy cần ánh xạ lại đường dẫn clip/frame trong inventory.json, đường dẫn ROOT và đầu vào package/voice/references trong các script. Thư mục script_inputs chứa kịch bản, CHAPTERS_12 và ánh xạ clip; original_english_voice chứa MP3 có SHA256 trong báo cáo. ZIP tài liệu kịch bản trước đây là bản chụp cũ: dùng nền bản đồ mới trong project/REFERENCES khi tạo composite.

17 voice riêng theo tên quốc gia vẫn ở release https://github.com/seotro95/seotro/releases/tag/malta-video-03-20min
Không thay đổi bản dịch, giọng khác hoặc hàng đợi chủ đề4. Nguồn khoa học xem SCIENCE_REFERENCES.md. Tham chiếu cách kể/dựng là video người dùng cung cấp, SHA256f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c.

# Phân tích video nguồn và áp dụng vào tập 40

Nguồn: https://github.com/seotro95/seotro/releases/tag/video ; asset video.c.a.toi.mp4.
Tệp nguồn đã được tải từ tập trước và đối chiếu lại metadata release trong phiên này: SHA256 f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c; 1262,933333 giây; 1280×720; 60 fps. Phạm vi phân tích là metadata và khung hình lấy mẫu xuyên suốt, có xem lại bảng hình trong phiên này; không phải tuyên bố đã nghe/xem liên tục toàn bộ hay thống kê toàn kênh.

Nguồn luân phiên cảnh quan, tái dựng hoạt động con người, cận vật liệu và sơ đồ giải thích. Các khung lấy mẫu cho thấy đời sống vùng lạnh, di chỉ, sách, vật liệu may mặc, bàn tay thao tác, không gian nghiên cứu và mô hình. Cách kể áp dụng là mở bằng một điều quen nhưng gây tò mò, đặt câu hỏi, giải thích từng lớp, đi qua ví dụ cụ thể và quay lại hình đầu với ý nghĩa mới. Không sao chép lời kể, logo, nhân vật, cờ hay hình trẻ em từ nguồn.

Tập 40 mở bằng bình gốm nửa vùi trong cát. Điều giữ người xem là câu hỏi: nếu lấy bình lên ngay, điều gì có thể mất dù chiếc bình còn nguyên? Mạch kể: bối cảnh → tìm kiếm và khảo sát → ghi chép → ảnh 3D → quá trình hình thành di chỉ → Uluburun → Antikythera → Pavlopetri → Mary Rose và bảo tồn → quyết định để lại tại chỗ → dấu người bình thường → trở lại chiếc bình. Lời kể gốc 3.006 từ; các ca không bị gộp vào một xác tàu.

Nhịp dựng: cắt trực tiếp khi đổi ý; chỉ hòa cảnh ngắn khi đổi địa điểm hoặc thời kỳ, và bù thời gian chồng để vẫn đúng 20:22. Luân phiên toàn cảnh biển/đáy biển, trung cảnh thao tác khảo sát, macro vật chứng, phòng bảo tồn và mô hình minh họa. Không đổi góc máy vô cớ ở mọi câu. Cảnh dưới nước giữ chuyển động chậm, đúng nổi và quán tính; bọt, bụi lơ lửng và sương không được dùng như hiệu ứng che lỗi hình.

Tất cả prompt tạo clip 10 giây, 16:9, mục tiêu 1080p/24fps, hoàn toàn im lặng. Mỗi cảnh có một hành động chính, một chuyển động máy hoặc đổi nét được chỉ định. Nhịp 0–2 giây thiết lập, 2–8 giây phát triển, 8–10 giây ổn định để cắt. Prompt chỉ yêu cầu, không bảo đảm generator tuân thủ; kiểm tra và loại audio track trước dựng nếu generator vẫn tạo tiếng.

Có 120 prompt mới, 12 TXT × 10, đánh số liên tục 1–120. Timeline có 123 mốc: 122×10 giây + 2 giây. Mốc 121 dùng lại clip003, mốc122 dùng clip001, mốc123 lấy 2 giây ổn định clip001. Đoạn kết trở lại vật mở đầu là dụng ý kể, không kéo chậm ảnh để lấp thời lượng.

HOOK_30_GIAY_10_SHOT.csv là phương án 10 góc/cảnh trong 30 giây đầu từ các clip đã có. Dùng những hình bình, bối cảnh, đo và ghi chép phù hợp chính lời 0–30 giây. Giữ nguyên voice; thay phần hình cảnh1–3, không cộng intro hoặc đổi tổng thời lượng. Có thể giữ timeline một clip/mốc10 giây nếu cần đối chiếu lời chặt hơn.

Điều kiện hình: người trưởng thành rõ ràng từ25 tuổi; không trẻ em ở nền, ảnh, màn hình, bóng, phản chiếu hoặc tranh. Không hài cốt người, cảnh tai nạn, thợ lặn hoảng loạn, kho báu vàng hoặc thành phố huyền thoại. Không tạo chữ, bản đồ có tọa độ, ngày tháng hay dữ liệu sonar giả. Tên địa điểm và năm thêm trong editor. Mô hình giả định phải được nhận diện là minh họa trong phim.

Voice chính tiếng Anh theo123 mốc. 16 bản còn lại căn theo13 chương: 12×100 giây +22 giây. Mỗi bản phải giải mã đủ58.656.000 mẫu ở48kHz =1222 giây. Khớp chương và tổng thời lượng không đồng nghĩa khớp từng từ giữa ngôn ngữ. Giữ16 nam và H’mông Trắng nữfemale-3 theo hồ sơ đã khóa. Bản dịch và phương ngữ cần người bản ngữ nghe duyệt độc lập trước phát hành.

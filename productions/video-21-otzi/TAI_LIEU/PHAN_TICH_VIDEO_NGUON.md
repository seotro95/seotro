# Phân tích nguồn và cách áp dụng cho Ötzi 21

Nguồn: https://github.com/seotro95/seotro/releases/tag/video — `video.c.a.toi.mp4`.
Tải lại trong phiên này và tính SHA-256: `f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c`, khớp hồ sơ bàn giao. Video khoảng 21:03, hình 1280×720. Ngôn ngữ Nga được ghi trong phân tích bàn giao.

Phạm vi: xem bảng 6 khung hình của 30 giây mở đầu và bảng khung hình lấy mẫu cách 75 giây xuyên suốt; đọc phân tích nguồn đã lưu trên nhánh sản xuất. Đây là phân tích lấy mẫu, không phải xem/nghe tay liên tục toàn bộ video. Phần diễn giải lời Nga dựa trên hồ sơ phân tích trước, không phải bản dịch mới đã kiểm độc lập. Không xác định phần mềm dựng, model hay prompt nội bộ của tác giả.

Mở đầu quan sát được đi từ người trong môi trường lạnh sang địa điểm khai quật, cận hai chiếc răng, địa cầu và hành trình. Hình lấy mẫu sau đó xen phòng thí nghiệm, mô hình cơ thể, trang phục, cấu trúc trú ẩn, tư liệu đen trắng và cảnh quan. Sự đổi quy mô giúp các ý trừu tượng có vật thể để bám vào. Nguồn có chữ/nhãn; prompt mới để sạch chữ và thêm nhãn đã kiểm trong phần mềm dựng.

Phân tích bàn giao mô tả trục kể: vật chứng nhỏ → câu hỏi lớn → định vị thời gian/không gian → kiểm chứng → giải thích cơ chế → quay về vật chứng. Bản mới mở bằng mũi tên, đưa câu hỏi về hành trình, rồi lần lượt xét phấn hoa, bàn tay, công cụ, quần áo, bữa ăn, vai và quá trình bảo tồn. Đoạn kết quay lại mũi tên với ý nghĩa mới: nó chứng minh thương tích, nhưng không ghi lại toàn bộ cảnh tấn công.

Nhịp nguồn không cố định 10 giây/cảnh. Phân tích cũ ghi một lượt dò FFmpeg có trung vị khoảng 5,7 giây giữa các ứng viên đổi cảnh; đây không phải shot count đã gán nhãn và phiên này không chạy lại phép đo đó. Bộ mới tuân yêu cầu clip nguồn 10 giây. Khi dựng có thể đổi hình theo vế voice bằng cảnh dự phòng hoặc cắt đổi khung có chủ đích; crop không được gọi là góc quay mới. Giữ tổng timeline 1.242 giây.

Áp dụng hình: toàn cảnh núi để định vị; trung cảnh người lớn để thấy hành động; macro vật liệu để hiểu kỹ thuật; mô hình rõ là minh họa để giải thích pháp y. Một hành động và một chuyển động máy mỗi clip. Gam đất/nâu cho vật liệu, xanh xám tiết chế ngoài trời, ánh trung tính trong phòng nghiên cứu. Không sao chép footage, câu chữ, watermark hay nhận diện của nguồn.

Ưu tiên hard cut ở chỗ đổi ý. Dissolve ngắn chỉ cho chuyển thời gian hoặc không gian; nếu thêm phải bù overlap để bản dựng vẫn đúng 20:42. Voice là trục dựng. Không đưa âm thanh từ clip tạo sinh vào phim; kiểm tra và tắt/xóa audio stream khi nhập, kể cả khi generator không tuân prompt im lặng.

Đặc tả: 125 cảnh chính, 124×10s + 2s cuối. Tạo clip125 dài10s rồi dùng2s; 126–130 là thay thế tùy chọn, không nối thêm. Có13TXT, mỗiTXT10prompt, số1–130. Tệp13 có5cảnh chính và5cảnh dự phòng. Bộ tài liệu này chưa tạo footage hay dựng MP4.

Không có trẻ em trong prompt, kể cả người nền, hình trên màn hình, bóng hay ảnh phản chiếu. Mọi người từ30tuổi trở lên. Không tái hiện kẻ bắn, cú đánh đầu hay giây chết như sự kiện đã xác nhận. Dùng vật chứng bản sao/mô hình; ảnh CT, bản đồ và ảnh cổ vật thật phải nhập từ nguồn đã kiểm và ghi credit, không để hình tạo sinh giả thành dữ liệu thật.

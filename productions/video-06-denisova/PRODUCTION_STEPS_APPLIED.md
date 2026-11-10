# Quy trình đã áp dụng — chủ đề 6 Denisova

1. Đọc trạng thái đã lưu, chọn đúng chủ đề 6 theo yêu cầu; giữ nguyên tập 1–4 đã bàn giao và tập 5 đang xếp hàng. Không tự bắt đầu tập 7.
2. Đối chiếu video nguồn bằng SHA256. Phân tích cách mở đầu bằng vật chứng nhỏ, đặt câu hỏi, chuyển giữa cảnh vĩ mô, môi trường, bản đồ và phòng thí nghiệm; học nhịp dựng và viết lời mới từ nguồn khoa học.
3. Kịch bản Anh mới 3425 từ, 126 đoạn 10 giây, tổng 1260 giây. 12 chương có ranh thật: sáu chương 110 giây rồi sáu chương 100 giây. Không dùng thời lượng hoặc ranh chương của tập trước.
4. Tạo 110 prompt mới, đánh số liên tục trong 11 TXT, mỗi TXT 10 prompt. Đánh dấu 16 ô REUSE và nguồn clip trong timeline 126 cảnh; không yêu cầu tạo lại các ô đó. Mỗi clip 10 giây hoàn toàn im lặng.
5. Không có trẻ em ở bất kỳ vị trí nào: nền, bóng, phản chiếu, ảnh, màn hình, tượng. Chỉ người trưởng thành rõ 25–60 tuổi. Không dựng chủ mẫu Denisova 3/11; chỉ vật chứng mô phỏng rời và người lớn minh họa. Chỉ dùng răng vĩnh viễn trưởng thành trong mô hình giảng giải nha khoa. Không đặt đồ hiện đại trong cảnh cổ.
6. Đối chiếu 27 nguồn, phân biệt DNA ty thể, DNA nhân và protein, giới hạn tuổi tối thiểu, liên hệ phân tử và tên phân loại; không suy ra mặt/ngôn ngữ/tiểu sử từ một mẫu. Bốn bản đồ hiện đại không phải đường bờ cổ hoặc lộ trình di cư. Ba sơ đồ là giảng giải, không phải dữ liệu đo.
7. Phát hành tài liệu trước voice, giữ ZIP gốc bất biến. 16 bản dịch giữ ý, kiểm tra thuật ngữ và số. Viết lại toàn bộ 12 chương Việt và H’Mông; làm rõ các đoạn dễ dịch sai ở 14 locale và kiểm tra dịch ngược các chương 2/4/5/10. Dùng cách viết của Bồ Đào Nha cho pt-PT. Việc này không thay thế biên tập/nghe độc lập của người bản ngữ.
8. Giữ đúng 17 ID của science-prehistory-17-v1: 16 nam, H’Mông nữ 3, cùng mẫu tham chiếu gốc SHA256 và style science-documentary-expressive-v1. Dùng backend Melo đã ghim mã nguồn; H’Mông dùng VITS+OpenVoiceV2 của tool riêng. H’Mông tách chữ/số trước bộ chuẩn hóa số của tool, không xóa số hoặc thay engine.
9. Preview Anh 30 giây, rồi chạy 16 locale trên GitHub Actions có checkpoint; H’Mông native chạy riêng. Dùng nhịp, nghỉ và nhấn âm lượng nhẹ; không đổi cao độ. Chỉ xử lý lại phần lỗi nếu có; giữ đầu vào đã rà soát.
10. Khi đo thực tế, giữ các locale/chương đã đạt và chỉ sửa phần vượt thời lượng. Đo checkpoint trước khi sửa; Nhật chương 8 được viết lại hoàn toàn vì còn lẫn tiếng Anh. Giữ nguyên 3425 từ Anh: riêng 11 ô dùng một yêu cầu trọn ô, tốc độ trong khoảng style cũ và chỉ bỏ khoảng lặng bằng số 0 ở mép, chừa 30 ms; không cắt mẫu tiếng nói. Căn Anh theo 126 ô 10 giây; bản dịch theo 12 chương 110/100 giây. Giới hạn tempo sau tổng hợp: Anh 1,4, các bản khác 1,5. Không cắt lời. Mỗi bản giải mã đúng 60.480.000 mẫu tại 48 kHz = 21:00. Khớp chương/tổng không có nghĩa khớp từng từ giữa mọi ngôn ngữ.
11. Đổi tên theo quốc gia bằng sao chép nguyên byte, kiểm SHA256, phát hành 17 MP3 riêng và ZIP tổng/hồ sơ. Kiểm 17 digest từ máy chủ với báo cáo, đúng ID/giới tính/style/thời lượng, toàn bộ 3425 từ/126 cue Anh và giải mã độc lập file Anh công khai.
12. Lưu script 17 locale, timing, báo cáo, hồ sơ giọng, link tải, mã nguồn và trạng thái để tiếp tục. Video tập 6 nay đã dựng xong; xem phần cập nhật dưới đây. Khi có clip: dùng đúng voice Anh đã khóa, bỏ mọi âm thanh clip, mở đầu 12 shot/30 giây nằm trong 21 phút, không cộng intro.

Khi làm tập sau, lấy thời lượng/chủ đề/số cảnh/ranh chương từ yêu cầu mới và trạng thái; giữ hồ sơ giọng, style, tên quốc gia và nguyên tắc không có trẻ em. Không chạy nguyên script tập 6 cho tập khác.



## Cập nhật dựng video chủ đề6

1. Nhận104clip518–621, kiểmSHA256/metadata và lấy mẫu0,8/4,9/9,1giây. Tất cả10giây,720p24fps;33clip có tiếng. Đối chiếu với110prompt, xử lý6ô thiếu bằng bản đồ và cảnh phù hợp.
2. Chọn63clip phù hợp, thay bản đồ và dữ liệu doAIvẽ lại bằng30đồ họa có chú thích; bỏclip025 đổi danh tính chủ thể. Không có hình trẻ em trong cảnh được chọn qua kiểm tra mẫu.
3. Dựng224shot trong126ô10giây, mở đầu12shot/30s và9dissolve ngắn nằm trong tổng21:00. Chữ mở đầu nhấn vật chứng/năm2010/Denisovans.
4. Giữ nguyên voiceAnhSHA256d733faf7cb437ff9db733a7f5f9f527aa177a3e688abdd270f313af2ab3605ad. Bỏmọi tiếngclip bằng-mapvà-an; chỉ chuẩn hóa độ lớn khi xuất, không đổi nhịp hoặc cao độ.
5. Dựng trực tiếp sau khi duyệt tự động từ chối công khai clip nguồn. Không tạo nhánh chứa video gốc; chỉ phát hành bản dựng và tài liệu. Giữ toàn bộ nguồn người dùng; giải phóng file dựng trung gian đã ghép với khoảng an toàn60giây để đủ chỗ.
6. Kiểm30240frame,1260giây,1audioAnh,12chương,126cueSRT,3425từAnh,giải mãtoànbộ,không khoảng đen dài và15điểm đồng bộ sóng âm. Rà44khung hình từbản cuối; không tuyên bố xem tay liên tục21phút.
7. Đưa chỉ sản phẩm hoàn chỉnh lênGitHubRelease, xác minhSHA256từngasset và tải kiểmtoànbộMP4côngkhai; tệpTXT/ZIP dùng linkAsset để tải trực tiếp. Lưu kế hoạch,code,báocáo,hồsơvàlinktrongEDITING. Giữ17voice đã bàn giao vàtập5queued.

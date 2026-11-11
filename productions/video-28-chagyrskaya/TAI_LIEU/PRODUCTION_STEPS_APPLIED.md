# Các bước đã thực hiện — Chagyrskaya28

1. Xác định chủ đề028từ danh sách người dùng đã lưu. Chỉ làm tập28, không khởi động tập khác trong hàng đợi.
2. Dùng lại tệp nguồn đã tải trong phiên trước, tính lạiSHA-256khớp và xem lại bảng hình lấy mẫu. Đối chiếu phân tích nguồn đã lưu; không tuyên bố dịch/nghe/xem tay toàn bộ mới.
3. Tra bài nghiên cứuNature2022, tài liệuMaxPlanck, nghiên cứu bộ gene2020và nghiên cứu răng2026. Giữ các giới hạn về11+2cá thể, quan hệ, thời gian, mô hình nhóm và di cư.
4. Viết3.548từAnh,137mốc và14chương. Thiết kế140prompt, gồm137cảnh chính và3thay thế. Chia14TXT×10prompt. Không có trẻ em trong cảnh; quan hệ dùng ký hiệu mẫu/nút trừu tượng.
5. Giữ17VoiceID/mẫu từ tập21:16nam vàH’mông nữfemale-3. BackendMelo-Viet1.3.1 commit4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043; Hmong1.6.6 commit061430d958b8d5fc14d04209c6f0cd20492382c2. Chạy mãbackendtrênLinux, không chạyGUIWindows.
6. Tạo bản dịch nháp, chuẩn hóa năm trước khi dịch, kiểm cách dùng theo ngữ cảnh. Viết lạiViệt/H’mông; các bản khác dựa trên dịch tự động có điều chỉnh thuật ngữ/năm và một số cách dùng địa phương. Không có kiểm bản ngữ độc lập.
7. Tạo16voiceonlinevớiWordBoundarymetadata; lưu checkpoint và đối chiếu văn bản. Dịch vụ từng trảNoAudiovà quá trình xuất từng chạm giới hạn dung lượng; tiếp tục từ checkpoint. Chỉ chuyển thư mục tập28sang vùng lưu trữ tạm còn trống, giữ nguyên dữ liệu tập trước.
8. Tạo14chươngH’mông bằngVITS+OpenVoiceV2, mẫu nữ3đúngSHA-256, FP32,clear-v1, giữ dấu nhận diện âm thanh củatool. [LượtGitHubActions thành công](https://github.com/seotro95/seotro/actions/runs/42971383014). Tải đủ cácrawvề để ghép và kiểm thời lượng.
9. CănAnh137mốc(136×10s+2s); bản khác14chương(13×100s+62s). Dùngatempo giữ cao độ, nghỉ cuối ngắn,loudnormmục tiêu-19LUFS/-2dBTP,mono48kHz MP3 96k. Không bù bằng đoạn im lặng dài.
10. Kiểm giải mã toàn file và65.376.000mẫu/voice, tương đương1.362giây. Kiểm metadata cho16voiceonline, biên độ và khoảng tín hiệu rất thấp. H’mông không có đối chiếu từng từ. Không thay kiểm kỹ thuật bằng chứng nhận nghe/ngôn ngữ.
11. Đóng gói kịch bản,prompt,nguồn,QA,hồ sơ giọng và17MP3. Bản phát hành có link riêng vàSHA-256; kiểm lại truy cập công khai và nội dungZIP.

Chưa tạo footage/dựngMP4. Người bản ngữ chưa biên tập/nghe độc lập các bản dịch. Phương ngữH’môngTrắng chưa được xác nhận độc lập; giữ nhãn cần rà soát này trong hồ sơ.

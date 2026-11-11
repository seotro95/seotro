# Các bước đã thực hiện

1. Đọc danh sách chủ đề và hồ sơ giọng từ tệp người dùng cung cấp; xác định21làÖtzi. Không khởi động chủ đề khác trong hàng đợi.
2. Tải video nguồn, kiểmSHA-256, xem bảng hình mở đầu và bảng lấy mẫu xuyên suốt; đối chiếu phân tích nguồn đã lưu. Phần lờiNga dựa vào hồ sơ cũ, không tuyên bố dịch/nghe mới toàn bộ.
3. Tra nguồn bảo tàng và công trình khoa học, gồm nghiên cứu pháp y2025 và số hóa2026. Giữ tranh luận về thời gian sống sau trúng tên, chấn thương đầu và quá trình bảo tồn.
4. Viết3.172từAnh,125mốc cảnh,13chương; thiết kế130prompt gồm125cảnh chính và5cảnh thay thế. Chia13TXT×10prompt. Mỗi clip nguồn10s; phim dùng124×10s+2s.
5. Giữ16voiceIDnam và mẫuH’mông nữfemale-3 từtập19. BackendMelo commit4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043; backendHmong commit061430d958b8d5fc14d04209c6f0cd20492382c2. Đây là sử dụng mã backend trênLinux, không phải chạy giao diệnWindows.
6. Dịch bản nháp cho các locale, chuẩn hóa năm bằng số trước khi dịch để tránh sai năm. Viết lại toàn bộ bảnViệt vàH’mông theo ngữ cảnh; điều chỉnh một số cách dùngBồĐàoNha.14bản khác vẫn dựa trên dịch tự động. Chưa có kiểm bản ngữ độc lập.
7. Tạo16voiceonline bằng backendtool, ghiWordBoundarymetadata. Phát hiện một đoạnHàn bị bỏ phần lớn lời dù provider trả file hợp lệ; tạo lại cùngvoiceIDvà kiểm lại bằng metadata.
8. Xác minhSHA-256của mô hìnhH’mông và mẫu nữ3. Tạo các chương bằngnativeVITS+OpenVoiceV2, FP32, clear-v1, giữ dấu nhận diện âm thanh củatool. [LượtGitHubActions13chươngthànhcông](https://github.com/seotro95/seotro/actions/runs/42957590549). Thu đủraw, ghép và chuẩn hóa thời gian tại máy hiện tại.
9. CănAnh theo từngmốc10s vàmốc cuối2s;16bảnkhác theo12chương100s vàchươngcuối42s. Dùngatempo giữcaođộ, nghỉcuối ngắn vàloudnorm; không chèn khoảngimlặngdài để bù thời lượng. Thôngsốthựctế từngcue/chương nằmtrongREPORTS.
10. Giải mã toàn bộMP3và đếm59.616.000mẫu/voice tại48kHz, tươngđương1.242s. Đối chiếu metadata với văn bản chuẩn hóa cho16voiceonline. Kiểm biên độ và khoảng tín hiệu rất thấp. Đây là kiểm kỹ thuật, không phải nghe/ASRđộc lập toàn bộ.
11. Đónggói kịchbản, prompt, nguồn, bản dịch,QA,hồsơkhóagiọng và17MP3. KiểmhashcácfiletrongZIP. Linktải vàSHAđược lưu cùngbảnpháthành.

Chưa tạo footage hoặc dựngMP4tập21. Chưa có người bảnngữ kiểm/nghe độc lập cácbản dịch; phươngngữH’môngTrắng chưa được xác nhận độc lập. Những giới hạn này phải đi cùng hồ sơ khi tái sử dụng.

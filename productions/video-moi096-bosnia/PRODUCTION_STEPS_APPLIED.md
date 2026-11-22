# Quy trình đã áp dụng cho MỚI-096

1. Đọc trạng thái/khóa giọng từdựán hoàn tất; tạo thưmục vànhánhriêng, giữmọitậpcũ.
2. Kiểm metadata clipthamkhảo; chọnchínquytắckểchuyện người dùng cho phép. Tra nguồn khảo cổ, địa chất, di sản chính thức vàbàitrìnhbày2025 của bên đềxướng; ghiđúng phạmviđãđọc.
3. Viết kịchbản Anh mới200block/mườiphần, kiểm số viếtbằngchữ, hookmộtvật10s, promise<30s, payoff<2phút, rehook60–90s, caveat>=120s vàcâukếtđơn.
4. Lập kếhoạchhình theo200block, dựng timeline128cảnh và130prompt/13TXT; hai dựphòng129–130đánh dấu. Toàn bộ ngoài trời, khônglab/trẻem/âmthanh/chữđọcđược; cảnh làminhhọa.
5. Pháthành tàiliệu trước khi tạo audio; chỉchạybackend khi kiểm đầu vào qua. AnhAndrew200block căn bằngwordmetadata thậttừ50nhómrequest.
6. Chuyểnthể10phầncho15ngônngữcòn lại; giữquốcgia/giọng, ràcác từđanghĩa nhưjoint, cement, matrix, mortar, course, record, datevàcontext. Việtviếtlạibằnglờitựnhiên; côngkhai phạmvikiểmbảndịch, khôngnhậnđãkiểmnghebảnngữđộclập.
7. Chạyvoicequốcgiamax5job, giữrawcheckpointcủaphầnthànhcông; chỉsửaphầnhỏng. KhôngđổiID,pitch,nớitempohoặccắtchữđểépthờilượng. TừngMP3phảigiảimã59.616.000mẫumono48kHz.
8. Kiểm16hashkhácnhau, IDssođốikhóa, coveragewordmetadata, ranhgiớichương, scriptSHA, fullMP3decode vàCRCZIP. Đăng16MP3riêng/ZIP/tàiliệu/linkTXT.
9. Tảilạicôngkhai3ZIP, soSHAtrênGitHub, giải mãlại16MP3vàHEADtừngURL. KiểmTXTtiêuđề/thumbnailvàkịchbản. LưuQA, manifest, quytrình, scriptvàgiọngởthưmục đọcđượctrongGitHub.
10. Đốichiếutreevớibaseline, chỉchophépcậpnhậthai tệptrạngtháichung/khóagiọng, giữcácblobcũcònlại. Fast-forwardnhánhlàmviệcchínhsaukhiđạt. Khôngtựchạychủđềtiếptheo. Chưatạofootage, thumbnailhoặcMP4ởgiaiđoạnnày.

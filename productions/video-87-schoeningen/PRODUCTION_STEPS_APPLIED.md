# Quy trình áp dụng tập87 — tiếp tục từ tập85

1. Đọc catalogue gốc:Schöningen. Thời lượng người dùngghiđè1.222giây. Giữ17ID từ71,cụthểNamMinhNeural nam vàHmongfemale-3 nữ;khôngsửaaudiotậpcũ.
2. Kiểmnguồn vàthamkhảo,tránhniênđạicũ300kađứngmộtmình. ViếtkịchbảnAnhnguyênbản3.249từ,123mốc;13chương:12×100+22giây.
3.110prompt10giây trong11TXT,13mốcdùnglạiđánhdấu. Mỗipromptcấmtrẻem/thiếuniên,mọilờinóiâmthanh. Gócmáyriêng,đồgỗlàbảnsao/môhình,khôngdựngsănchết/chântướngmaker.
4. Pháthànhtàiliệu/trangdownloadtrướckhitạovoice. Kiểmsốprompt,thứtự,timeline123mốcvàCRC/SHA.
5. PreviewAnh30giây vàNamMinh10giây. NamMinhphảixácminhcatalognam+voiceIDthật,khôngđổinhãnvoicekhác.
6. Việt vàH’môngviếtlại13chương;14ngônngữkháccóbảndịchnháp vàràthuậtngữ/niênđạichính. H’môngchuẩnhóavănbảntheobackendriêng.Kiểmbảnngữđộclậpcònchờ.
7. Melo1.3.1backendonlineđượcpincho16voice;Hmong1.6.6nativeVITS/OpenVoiceV2female-3cho1voice. GiữSHAmodel/ref/source,cachetheovănbản/voice/rate. Khôngchuyểnbackendkháckhi401/403/429.
8. Anhnhóm3mốclời/request,cắttheoword-boundarykhớpđủscript.14bảndịch+NamMinhcan13chương,giữđộdài. H’môngnativecóphầnngắtvànắnratenhẹ,khôngpitchshift.
9. ĐầuraMP3mono48kHz96kbps,loudnesstarget-19LUFS/truepeak-2dB. Căntempo giữpitchcógiới hạn,khôngcắtmấtlời;đọclạimỗiMP3đúng58.656.000mẫu. Kiểmwordmetadata16online,hashvănbản/refHmong,17voiceID vàSHAriêng.
10. Pháthành17MP3tênquốcgia,ZIPvoice,script/prompt/SRT/timeline,5title/thumbnailvàbáocáo. TảilạipublickiểmCRC/SHA/17linkHTTP vàgiảimãduration,refreshdocsQAcuốirồilưucanonicalGitHub.
11. Chưacófootage/MP4tập87. Khiđủclip,dựng10cảnh/30giâyđầu nằmtrong20:22,phimchínhchỉAnh,xóatiếngclip,thiếucảnhdùngvideoliênquan,khôngảnhchữ.

import json,os
from pathlib import Path
folder=Path(os.environ['QA_FOLDER']);notes=Path('release-melo-viet/RELEASE.md').read_text()
local=json.loads((folder/'LOCAL-27-MODEL-QA.json').read_text())
assert local['status']=='passed' and len(local['results'])==54
record=json.loads((folder/'ONLINE-QA-EXTENDED.json').read_text())
passed=[r['locale'] for r in record.get('results',[]) if r['status']=='passed']
notes+='\n\nKiểm tra phát hành: **84 kiểm thử Python, kiểm thử trình duyệt và 14 tình huống launcher Windows PowerShell 5.1 (WSL giả lập) đạt**. Cài CPU nhanh trên Ubuntu 22.04, chép toàn bộ mô hình từ bản đầy đủ và **54 WAV thật / 27 mô hình Piper** được kiểm tra. Các WAV này tạo với chế độ ngoại tuyến sau khi tải mô hình. Melo/VieNeu gốc không đổi mô hình/trọng số so với bản 1.1.0, đã thử bảy tiếng ở bản đó.\n'
notes+='\nKiểm thử trực tuyến: **'+str(len(passed))+'/8 locale tạo mẫu thật thành công** trong lần kiểm tra này: '+', '.join(passed)+'. Xem ONLINE-QA-EXTENDED.json; khả năng kết nối từ mạng/WSL của bạn vẫn cần Nghe thử. Không thay giọng tự động khi lỗi.\n'
Path(os.environ['RUNNER_TEMP'],'release-notes.md').write_text(notes)

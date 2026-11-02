import json,os
from pathlib import Path
folder=Path(os.environ['QA_FOLDER']);notes=Path('release-melo-viet/RELEASE.md').read_text()
def report(name):return json.loads(next(folder.rglob(name)).read_text())
local=report('LOCAL-MODEL-QA.json');assert local['status']=='passed' and len(local['results'])==102
multi=report('MULTILINGUAL-QA.json');assert multi['status']=='passed' and len(multi['results'])==70
hmong=report('HMONG-QA.json');assert hmong['status']=='passed' and hmong['offline_app_restart_passed']
mp3=report('EXPRESSIVE-MP3-QA.json');assert mp3['status']=='done' and mp3['mp3_status']=='done'
record=report('ONLINE-QA-EXTENDED.json');passed=[r['locale'] for r in record.get('results',[]) if r['status']=='passed']
notes+='\n\nKiểm tra phát hành: **103 kiểm thử Python, kiểm thử trình duyệt và 14 tình huống launcher PowerShell 5.1 (WSL giả lập) đạt**. Cài/cập nhật trên Ubuntu 22.04 và chép gói mô hình qua bộ cài thật; **102 WAV Piper / 51 preset**, **70 WAV Supertonic / 31 tiếng, đủ 10 preset**, ba mẫu Hmong RPA và khởi động lại Hmong ngoại tuyến thành công. Luồng nhấn nhá → WAV → MP3 thật đạt. Chưa kiểm định chất lượng bằng người nghe bản ngữ cho toàn bộ giọng.\n'
notes+='\nTrực tuyến: **'+str(len(passed))+'/8 locale tạo mẫu thật thành công**: '+', '.join(passed)+'. Xem ONLINE-QA-EXTENDED.json; kết nối trên mạng/WSL của bạn có thể khác.\n'
Path(os.environ['RUNNER_TEMP'],'release-notes.md').write_text(notes)

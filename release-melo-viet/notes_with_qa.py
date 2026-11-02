import json,os
from pathlib import Path
root=Path(os.environ['RELEASE_ASSETS'])
record=json.loads((root/'ONLINE-QA.json').read_text())
notes=Path('release-melo-viet/RELEASE.md').read_text()
if record['status']=='passed':
    summary=f"\n\nKiểm thử dịch vụ trực tuyến trong lần phát hành này: **đạt**, tạo mẫu thật ở {len(record['results'])} ngôn ngữ/quốc gia; danh mục có {record['catalog_voice_count']} giọng / {record['catalog_locale_count']} locale lúc thử. Xem ONLINE-QA.json. Chưa thử sinh đủ một giờ lời đọc.\n"
else:
    summary='\n\n**Kiểm thử dịch vụ trực tuyến không hoàn tất trong lần CI này.** Tính năng lấy danh mục/tạo giọng cần được thử trên mạng của bạn; chưa có số đo tốc độ trực tuyến đáng tin từ lần phát hành này. Các bộ đọc ngoại tuyến được kiểm tra riêng. Xem ONLINE-QA.json.\n'
Path(os.environ['RUNNER_TEMP'],'release-notes.md').write_text(notes+summary)

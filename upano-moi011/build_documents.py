import csv
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

R = Path(__file__).parent
D = R / 'documents'
P = D / 'PROMPTS'
S = R / 'voice/scripts'
TARGET = 1222
FRAMES = 58656000
PREFIX = 'UPANO_MOI011'
TAG = 'upano-moi-011-20m22s'
BASE = 'https://github.com/seotro95/seotro/releases/download/' + TAG + '/'
for folder in [D, P, S]:
    folder.mkdir(parents=True, exist_ok=True)

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def stamp(value):
    milliseconds = round(value * 1000)
    return f'{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02},{milliseconds % 1000:03}'

rows = []
for line in (R / 'CUES_DRAFT.tsv').read_text(encoding='utf-8').splitlines():
    number, voice = line.split('\t', 1)
    number = int(number)
    rows.append(dict(id=number, start=(number - 1) * 10, end=min(number * 10, TARGET), voice=voice))
assert [row['id'] for row in rows] == list(range(1, 124))
assert rows[-1]['end'] == TARGET
visuals = {}
for line in (R / 'VISUALS_DRAFT.tsv').read_text(encoding='utf-8').splitlines():
    number, kind, visual, camera = line.split('\t')
    visuals[int(number)] = dict(kind=kind, visual=visual, camera=camera)
assert set(visuals) == set(range(4, 124))

intro = [
    ('LANDSCAPE', 'A cinematic present-day rainforest edge in the eastern Ecuadorian Andean foothills opens toward a river terrace and a few distant clearings. This is geographic illustration, not asserted location footage.', 'Wide high oblique aerial glide through thin morning mist.'),
    ('EARTHWORK', 'A subtle straight shallow depression appears between patches of grass and low vegetation on a foothill terrace. Keep the ground relief modest, without a visible complete city.', 'Low aerial side track with grazing daylight.'),
    ('EARTHWORK', 'A low rectangular grass-covered earth bank comes into clear view beside lower open ground. Soil and plant textures remain ordinary and realistic.', 'Close ground-level sideways dolly.'),
    ('MODEL', 'A restrained physical teaching terrain model shows several small platform groups linked across a terrace. The model-board edge is visible; this is not actual surveyed Upano data.', 'High oblique slow push toward the connected groups.'),
    ('EXPLAINER', 'A transparent classroom canopy diorama allows a few discrete light paths through genuine gaps between opaque leaves to a soil tray, while other paths stop at vegetation.', 'Close side tracking that keeps both leaves and soil in view.'),
    ('SECTION', 'A small modern soil-profile teaching model reveals a shallow U-shaped route cut and low banks beside it. No paving, tunnel, stone wall or buried house.', 'Low cross-sectional close slide.'),
    ('PROCESS', 'Rainwater moves gently along a shallow drainage demonstration beside a raised dry earthen edge. The water follows a plausible downhill gradient.', 'Macro low angle tracking along the flowing water.'),
    ('MODEL', 'Small field plots, edge drains and a modest platform base coexist in one physical research model. Leave building roofs absent and functions illustrative.', 'Overhead gentle arc connecting the field and platform.'),
    ('LAB', 'A generic adult gloved hand aged 40 to 60 places one plain reference potsherd beside a soil sample on a modern laboratory tray. Neither is claimed as an authentic Upano find.', 'Extreme close slow rack focus between pottery and soil.'),
    ('MODEL', 'An earth-tone educational landscape model brings platforms, routes, cultivation spaces and drainage into a single coherent view. No exact ancient layout or population is asserted.', 'Slow high oblique pullback preparing the transition to the main story.'),
]

shots = []
for index, (kind, visual, camera) in enumerate(intro, 1):
    shots.append(dict(shot_id=index, start=(index - 1) * 3, end=index * 3, kind=kind, visual=visual, camera=camera))
for cue in rows[3:]:
    shots.append(dict(shot_id=cue['id'] + 7, start=cue['start'], end=cue['end'], **visuals[cue['id']]))
assert len(shots) == 130 and shots[-1]['end'] == TARGET
assert all(a['end'] == b['start'] for a, b in zip(shots, shots[1:]))
assert sum(x['end'] - x['start'] for x in shots) == TARGET

silent = 'Video không có âm thanh, không có lời nói.'
prompts = []
for shot in shots:
    overlaps = [r for r in rows if r['start'] < shot['end'] and r['end'] > shot['start']]
    shot.update(prompt_id=shot['shot_id'], generation_seconds=10, use_seconds=shot['end'] - shot['start'],
                voice_cue_ids=[r['id'] for r in overlaps], voice=' '.join(r['voice'] for r in overlaps),
                action='CREATE', source_filename=f"UPANO_{shot['shot_id']:03}.mp4")
    prompt = (
        'One continuous 10-second shot, cinematic scientific documentary, 16:9, stable realistic motion and restrained natural color. '
        + shot['visual'] + ' Camera: ' + shot['camera']
        + ' Any modern people or visible hands must belong to clearly adult individuals aged 35 to 65. '
        + 'No children, infants, adolescents, minors, youthful silhouettes, child portraits, or minors on screens or in reflections. '
        + 'Historical reconstructions and terrain, soil, light-pulse or point-cloud models must look illustrative, never like authenticated field evidence or actual measured Upano datasets. '
        + 'No imported stone pyramids, fantasy buildings, invented artifacts, impossible water flow, transparent solid foliage, time-lapse, morphing, lip-sync, readable text, captions, logos or watermarks. '
        + silent
    )
    assert prompt.endswith(silent)
    shot['prompt'] = prompt
    prompts.append(dict(id=shot['prompt_id'], source_filename=shot['source_filename'], generation_seconds=10,
                        timeline_start=shot['start'], timeline_end=shot['end'], use_seconds=shot['use_seconds'],
                        voice_cue_ids=shot['voice_cue_ids'], kind=shot['kind'], prompt=prompt))
assert len({x['prompt'] for x in prompts}) == 130
for old in P.glob('*.txt'):
    old.unlink()
for offset in range(0, 130, 10):
    batch = prompts[offset:offset + 10]
    name = f'PROMPT_{offset // 10 + 1:02}_{offset + 1:03}-{offset + 10:03}.txt'
    body = '\n\n'.join(f"{p['id']:03d}. {p['prompt']}" for p in batch) + '\n'
    (P / name).write_text(body, encoding='utf-8')
assert len(list(P.glob('*.txt'))) == 13

dump(S / 'en-US.json', rows)
dump(D / 'ENGLISH_CUES_123.json', rows)
dump(D / 'SCENES_AND_PROMPTS.json', shots)
dump(D / 'ALL_PROMPTS.json', prompts)
dump(D / 'OPENING_10_SHOTS_30s.json', shots[:10])
chapters = []
for i in range(0, len(rows), 10):
    group = rows[i:i + 10]
    chapters.append(dict(id=i // 10 + 1, start=group[0]['start'], end=group[-1]['end'],
                         source_cue_ids=[r['id'] for r in group], voice=' '.join(r['voice'] for r in group)))
assert len(chapters) == 13 and [c['end'] - c['start'] for c in chapters] == [100] * 12 + [22]
dump(D / 'CHAPTERS_13.json', chapters)
(D / 'KICH_BAN_EN_20m22s.txt').write_text('\n\n'.join(r['voice'] for r in rows) + '\n', encoding='utf-8')
(D / 'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{r['id']:03d} | {stamp(r['start'])} → {stamp(r['end'])}\n{r['voice']}" for r in rows) + '\n', encoding='utf-8')
(D / 'en-US.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows) + '\n', encoding='utf-8')
with (D / 'TIMELINE_130_CANH.csv').open('w', encoding='utf-8-sig', newline='') as f:
    fields = ['shot_id', 'start', 'end', 'use_seconds', 'generation_seconds', 'voice_cue_ids', 'voice', 'source_filename', 'kind', 'action', 'camera', 'visual', 'prompt']
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(shots)

for name in ['NGUON_KIEM_CHUNG.md', 'PHAN_TICH_VA_KE_HOACH_DUNG.md', '5_TIEU_DE_VA_THUMBNAIL.txt',
             'VOICE_PROFILES_LOCKED_BASELINE.json', 'PRODUCTION_STEPS_APPLIED.md']:
    shutil.copyfile(R / name, D / name)
words = sum(len(re.findall(r"\b[\w'-]+\b", row['voice'])) for row in rows)
qa = dict(status='passed', topic_id='MOI-011', catalogue_id='new-100-topics-20261116', target_seconds=TARGET,
          english_words=words, planned_words_per_minute=round(words / (TARGET / 60), 1),
          english_cues=123, ten_second_cues=122, final_cue_seconds=2,
          timeline_shots=130, unique_prompts=130, prompt_txt_files=13, prompts_per_txt=10,
          generated_clip_seconds=10, opening_shots=10, opening_seconds=30,
          timeline_total_seconds=sum(s['use_seconds'] for s in shots),
          all_prompts_silent_suffix=all(p['prompt'].endswith(silent) for p in prompts),
          all_prompts_exclude_minors=all('No children, infants, adolescents, minors' in p['prompt'] for p in prompts),
          translated_chapters=13, chapter_seconds=[100] * 12 + [22], expected_audio_frames_48000=FRAMES,
          requested_voice_count=16, all_requested_voices_male=True, vietnamese_voice_id='vi-VN-NamMinhNeural',
          voices_generated=False, footage_generated=False, video_edited=False)
dump(D / 'DOCUMENT_QA.json', qa)
guide = f'''MỚI-011 — UPANO — 20:22

Đây là chủ đề MỚI-011 trong danh sách mới, không phải chủ đề 11 về kim khâu của bộ cũ.

1. Kịch bản tiếng Anh: {words} từ, 123 mốc lời; 122 mốc 10 giây và mốc cuối 2 giây.
2. Tạo 130 clip 10 giây từ 13 TXT trong PROMPTS, đúng 10 prompt mỗi tệp. Đặt tên UPANO_001.mp4 đến UPANO_130.mp4.
3. TIMELINE_130_CANH.csv nối hình và lời. 10 clip đầu lấy 3 giây mỗi clip cho mở đầu 30 giây. Cảnh 011–129 dùng 10 giây; cảnh 130 dùng 2 giây. Tổng 1.222 giây. Không cộng thêm intro ngoài thời lượng.
4. Các mốc voice 10 giây và các cảnh mở đầu 3 giây có thể cắt ngang nhau; bảng ghi đầy đủ ID mốc lời liên quan. Không mặc định một mốc lời luôn bằng một cảnh.
5. Mọi prompt tạo clip đều dài 10 giây, không có trẻ em, thiếu niên hoặc trẻ trong nền, ảnh, màn hình và phản chiếu. Người và bàn tay phải rõ trưởng thành 35–65 tuổi.
6. Mỗi prompt kết bằng “{silent}”. Khi dựng vẫn xóa âm gốc nếu công cụ tạo clip tự thêm âm.
7. Phim chính chỉ voice tiếng Anh, không nhạc/SFX. Cảnh thiếu thay bằng video chuyển động liên quan, không ảnh đứng có chữ.
8. Cảnh quay tạo sinh là minh họa. Mô hình, point cloud, mặt cắt và phục dựng không phải dữ liệu LiDAR hay tư liệu khai quật Upano thật. Không dùng như chứng cứ đo. Hình LiDAR thực cần kiểm nguồn và quyền sử dụng.
9. Không kim tự tháp đá Maya, thành phố vàng, đường nhựa, xe cổ tưởng tượng hoặc trang phục nghi lễ bịa đặt. Nền đất, đường đào và thoát nước là các hình chính.
10. Giữ 16 ID giọng nam đã chọn, tiếng Việt đúng vi-VN-NamMinhNeural. Dùng backend online của Melo-Viet-Studio 1.3.1 đã khóa mã nguồn trong GitHub; không khẳng định chạy giao diện Windows.
11. Mỗi MP3 mục tiêu giải mã đúng 58.656.000 mẫu ở 48 kHz, tức 20:22. Tiếng Anh căn 123 mốc; bản dịch căn 13 chương chung: 12 × 100 giây + 22 giây cuối. Cùng thời lượng không có nghĩa từng từ cùng thời điểm.
12. SRT Anh dùng làm mốc lời. SRT dịch theo chương cần chia nhỏ trước khi dùng làm phụ đề hiển thị. Không khẳng định là phụ đề từng từ đã kiểm nghe.
13. Đây là tài liệu kịch bản và prompt, chưa có footage hoặc MP4. Các bản dịch và audio cần kiểm nghe bản ngữ trước khi phát hành chính thức.
'''
(D / 'HUONG_DAN_SU_DUNG.txt').write_text(guide, encoding='utf-8')
readme = f'''# MỚI-011 — Upano: mạng lưới đô thị dưới tán rừng — 20:22

Đây là tập MỚI-011 của bộ đề tài ngày 16/11/2026, lưu riêng với bộ chủ đề cũ.

- [Kịch bản và 13 tệp TXT prompt]({BASE}{PREFIX}_TAI_LIEU_20m22s.zip)
- [Kịch bản tiếng Anh]({BASE}KICH_BAN_EN_20m22s.txt)
- [5 tiêu đề và 5 prompt thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản gốc {words} từ Anh, 123 mốc lời; tổng mục tiêu 1.222 giây. Có 130 prompt mới trong 13 TXT, đúng 10 prompt mỗi tệp. Clip nguồn dài 10 giây; timeline có 10 cảnh × 3 giây ở mở đầu, 119 cảnh × 10 giây và cảnh cuối 2 giây.

Mỗi prompt cấm trẻ em, lời nói và âm thanh. Hình tạo sinh, mặt cắt, mô hình và point cloud chỉ minh họa, không phải dữ liệu đo hoặc tư liệu Upano xác thực. Không tạo kim tự tháp đá hay thành phố vàng.

Nguồn chính là Rostain và cộng sự, Science 2024, DOI 10.1126/science.adi6317; đã đọc bản thảo tác giả được công khai cùng nguồn kỹ thuật và nguồn thảo luận bổ sung. Không phát hành lại bài báo hay hình bản quyền. Giữ rõ giới hạn dân số, niên đại, tính đồng thời và giả thuyết núi lửa.

Tài liệu được phát hành trước khi tạo voice đầy đủ. Kế hoạch có 16 giọng nam cố định, gồm Andrew và Nam Minh; mỗi bản cần giải mã đúng 58.656.000 mẫu 48 kHz trước công bố. Chưa có MP4 hoặc footage cho tập này.
'''
(D / 'README.md').write_text(readme, encoding='utf-8')
with zipfile.ZipFile(R / f'{PREFIX}_TAI_LIEU_20m22s.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(D.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(D))
print(json.dumps(qa, ensure_ascii=False), flush=True)

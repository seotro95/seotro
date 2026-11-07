"""Camera requests for silent illustrative geography footage; not measured footage metadata."""
PROFILES={
 'aerial_oblique':('Toàn cảnh trên cao, nhìn chéo 35 độ',24,35,
  'Elevated oblique view looking down about 35 degrees, 24 mm equivalent wide lens.',
  'One slow lateral aerial glide, keeping the horizon and landmark geometry stable.',
  '0–2 s: hold the complete subject clearly in frame; 2–8 s: glide sideways by about five percent of the frame width; 8–10 s: ease into a steady hold.'),
 'aerial_push':('Toàn cảnh trên cao, tiến chậm, nhìn chéo 45 độ',24,45,
  'High oblique view looking down about 45 degrees, 24 mm equivalent wide lens.',
  'One very slow forward aerial push; keep the principal terrain feature visible throughout.',
  '0–2 s: establish the entire subject; 2–8 s: move forward gently with a change in image scale under eight percent; 8–10 s: settle without cutting.'),
 'aerial_pullback':('Đại cảnh mở rộng, lùi máy chậm',24,30,
  'Elevated wide view at about 30 degrees downward, 24 mm equivalent lens.',
  'One smooth, slow pullback to reveal more surrounding terrain, without rotating.',
  '0–2 s: show the main landform clearly; 2–8 s: pull back gently to expose its surroundings; 8–10 s: hold the wider composition.'),
 'topdown':('Toàn cảnh từ trên xuống gần vuông góc 90 độ',35,90,
  'Near-nadir overhead view looking almost vertically down, 35 mm equivalent lens. Choose a virtual altitude high enough to include the entire described pattern.',
  'A very gentle overhead drift with constant heading; no orbit and no changing perspective.',
  '0–2 s: the complete pattern is already visible; 2–8 s: drift no more than five percent of frame width; 8–10 s: lock the framing.'),
 'wide_eye':('Toàn cảnh ngang tầm mắt, ống kính rộng',24,0,
  'Low landscape viewpoint roughly at human eye level, 24 mm equivalent wide lens, horizon level.',
  'One restrained forward dolly with natural foreground parallax.',
  '0–2 s: keep foreground and distant context readable; 2–8 s: advance slowly; 8–10 s: ease into a stable final frame.'),
 'low_landscape':('Góc máy thấp, toàn cảnh có tiền cảnh rõ',24,-5,
  'Low viewpoint roughly half a metre above the foreground, 24 mm equivalent lens with a subtle upward view.',
  'One slow lateral move; do not hide the mountains or forest needed to identify the landscape.',
  '0–2 s: show the main subject and its setting immediately; 2–8 s: slide gently along the foreground; 8–10 s: settle with the subject still fully readable.'),
 'medium_lateral':('Trung cảnh, nhìn chéo nhẹ, trượt ngang',35,10,
  'Medium landscape framing, 35 mm equivalent lens, a gentle oblique angle around 10 degrees.',
  'One slow sideways move with restrained parallax and no abrupt pan.',
  '0–2 s: establish the subject in the centre of the composition; 2–8 s: slide sideways smoothly; 8–10 s: hold the final angle.'),
 'low_rock':('Góc thấp nhìn lên khối đá, giữ rõ điểm tựa',35,-10,
  'Low, slightly upward viewpoint around 10 degrees, 35 mm equivalent lens. Keep the rock and its support visible together.',
  'A very small lateral dolly to reveal the support geometry; the rock never moves.',
  '0–2 s: show the whole supported object; 2–8 s: shift gently to expose its contact surface; 8–10 s: hold the same stable rock arrangement.'),
 'telephoto':('Trung hoặc viễn cảnh nén phối cảnh, máy ổn định',70,0,
  'Distant observational framing with a 70 mm equivalent lens and a stable, level horizon.',
  'Locked tripod-like camera with only a very slow pan of at most three degrees.',
  '0–2 s: show the subject clearly; 2–8 s: use a barely perceptible pan while natural movement continues; 8–10 s: hold without zooming.'),
 'close_texture':('Cận cảnh chi tiết, góc chéo 20 độ',85,20,
  'Close framing with an 85 mm equivalent lens, about 20 degrees oblique to the surface. Use enough depth of field to read the relevant texture.',
  'A tiny, smooth lateral slider move. Keep the object shape and texture consistent.',
  '0–2 s: place the essential detail in sharp focus; 2–8 s: slide by less than five percent of frame width; 8–10 s: settle with the detail still readable.'),
 'macro':('Đặc tả bề mặt hoặc vòng cây, máy gần như cố định',100,15,
  'Macro-like detail, 100 mm equivalent lens, about 15 degrees oblique. Maintain coherent scale and moderate depth of field.',
  'Almost locked camera; only a gentle focus adjustment within the same surface, with no object transformation.',
  '0–2 s: show the key detail immediately; 2–8 s: make a subtle focus adjustment across the same texture; 8–10 s: hold focus.'),
 'locked_wide':('Toàn cảnh cố định, chuyển động tự nhiên trong khung',35,0,
  'Stable wide landscape framing, 35 mm equivalent lens, level horizon.',
  'Locked camera. Only the clouds, water, wind-blown vegetation or other natural elements move.',
  '0–2 s: present the subject clearly; 2–8 s: let natural environmental movement reveal the scene; 8–10 s: maintain the identical composition.'),
 'reconstruction_eye':('Tái dựng: ngang tầm mắt, tiến máy nhẹ',35,0,
  'Eye-level historical reconstruction, 35 mm equivalent lens, restrained and natural perspective.',
  'One very slow forward movement. Keep the layout stable; avoid fantasy architecture and invented readable signs.',
  '0–2 s: establish the relevant historical subject; 2–8 s: advance gently while keeping its structure stable; 8–10 s: hold.'),
 'schematic':('Sơ đồ minh họa: trực giao, máy cố định',None,None,
  'Clean orthographic explanatory view, overhead or cross-section as required by the described mechanism. No photographic lens simulation.',
  'The camera remains fixed. Animate only the physical process named in the subject, with restrained motion and consistent geometry.',
  '0–2 s: establish the elements; 2–8 s: illustrate one process with gentle changes in motion or shading; 8–10 s: hold the resulting state. No labels, numbers, instruments or simulated measurement readouts.')}

def choose_camera(subject,kind,cue_id,slot,count):
 s=subject.lower()
 if kind=='schematic':key='schematic'
 elif cue_id==1:key=['low_landscape','aerial_oblique','topdown','aerial_pullback'][slot]
 elif any(w in s for w in ['macro','annual rings','tree rings','trunk cross-section','fibrous peat']):key='macro'
 elif any(w in s for w in ['close','contact area','contacting','soil sample','plant fragments','rock samples','gloved hand','timber texture','texture']):key='close_texture'
 elif any(w in s for w in ['top-down','top view','overhead','plan view','ice ring','dark ring']):key='topdown'
 elif 'aerial' in s or 'high view' in s or 'high wide' in s:key='aerial_oblique'
 elif kind=='historical reconstruction' and not any(w in s for w in ['airblast','fallen forest','radial fallen','atmospheric flash']):key='reconstruction_eye'
 elif 'reindeer' in s or ('waterfall' in s and any(w in s for w in ['distant','thin'])):key='telephoto'
 elif any(w in s for w in ['boulder','hanging stone','granite block']):key='low_rock' if slot%2==0 else 'medium_lateral'
 elif any(w in s for w in ['summit','belukha','cloud veil','cloud shadow']):key='locked_wide' if slot%2 else 'aerial_oblique'
 elif 'island' in s or 'por-bazhyn' in s:key='aerial_oblique' if slot%2==0 else 'aerial_push'
 elif 'ground-level' in s or 'low view' in s or 'sand ripples' in s:key='low_landscape'
 elif 'waterfall' in s:key='aerial_oblique'
 elif slot==0:key='aerial_oblique'
 elif slot==count-1:key='aerial_pullback'
 elif slot%2:key='medium_lateral'
 else:key='wide_eye'
 vi,lens,angle,framing,motion,beats=PROFILES[key]
 return {'profile':key,'shot_and_angle_vi':vi,'lens_equivalent_mm':lens,'downward_view_degrees':angle,
  'framing_en':framing,'movement_en':motion,'beats_0_to_10_en':beats}

def build_prompt(subject,kind,camera):
 clean=subject.removeprefix('DIAGRAM ').removeprefix('RECONSTRUCTION ')
 if kind=='schematic':style='Restrained scientific explanatory animation. This is an illustrative schematic, not recorded measurements. '
 elif kind=='historical reconstruction':style='Naturalistic cinematic historical reconstruction for a geography documentary. Illustrative reconstruction, not archival footage or a verified exact blueprint. '
 else:style='Photorealistic cinematic geography illustration with restrained documentary colour, physically coherent terrain, detailed natural textures and stable landmark shapes. '
 low=subject.lower();lighting='Natural dusk light.' if any(w in low for w in ['dusk','evening']) else 'Soft natural daylight, realistic contrast and restrained colour.'
 extra=''
 if 'batagaika' in low or 'thaw slump' in low:extra='Show a thaw-related landslide and exposed frozen ground; no lava, volcanic eruption or meteorite impact.'
 if 'tunguska' in low or 'airblast' in low or 'atmospheric flash' in low:extra+='Any blast is an illustrative atmospheric event above the forest; no ground impact bowl, city, people in danger or nuclear mushroom cloud.'
 if 'chara' in low:extra+='Preserve the localized dunes, neighbouring taiga and distant snowy Kodar context when visible; do not turn the scene into an endless sandy desert.'
 return ('Create one continuous 10-second, 16:9 video clip, requested output 1080p. '+style+
  'SUBJECT: '+clean+'. CAMERA: '+camera['framing_en']+' '+camera['movement_en']+
  ' TIMING WITHIN THE 10-SECOND CLIP: '+camera['beats_0_to_10_en']+' '+lighting+' '+extra+
  ' Keep the essential visual subject visible from the first frame. One camera setup, no internal cuts, no abrupt zooms, no flicker, no morphing terrain or changing landmark geometry. '
  'No on-camera presenter, readable text, subtitles, logos, fabricated data displays, portals or aliens. '
  'AUDIO: VIDEO ONLY, ABSOLUTELY SILENT. Do not generate an audio track. No voices, narration, dialogue, music, ambient sound or sound effects.').strip()

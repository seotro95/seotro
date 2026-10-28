"""Measure real speech on the user's CPU; never infer a deadline from core count."""
import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid

from hardware import rendering_presets, calibration_candidates
from performance import speed_report
from state_io import write_json_atomic, write_progress

SAMPLES=(
    'Bản tin sáng nay ghi nhận nhiều thay đổi tích cực trong đời sống của người dân thành phố.',
    'Trên con đường nhỏ, các bạn học sinh cùng bước đến trường trong không khí vui tươi.',
    'Những người làm vườn chăm sóc từng luống rau để chuẩn bị cho phiên chợ cuối tuần.',
    'Một cuốn sách hay có thể mở ra nhiều cách nhìn mới về thế giới rộng lớn quanh ta.',
    'Cô hướng dẫn viên kể lại câu chuyện lịch sử bằng giọng nói rõ ràng và sinh động.',
    'Trong căn phòng yên tĩnh, người nghệ sĩ đang hoàn thiện bức tranh về quê hương.',
    'Đội tình nguyện đã dành buổi chiều để trồng thêm cây xanh dọc hai bên đường làng.',
    'Khi chuẩn bị hành trình mới, chúng ta cần kiểm tra hành lý và nhớ những lời dặn.',
    'Tiếng sóng biển hòa cùng làn gió nhẹ khiến mọi người thư thái sau ngày làm việc.',
    'Những thông tin vừa đọc chỉ là đoạn thử công khai để đo tốc độ tạo giọng trên máy.',
)

# Public, language-native text for measuring the selected voice. These are
# synthesis inputs, rather than silence or subtitle gaps in the speed metric.
NATIVE_SAMPLES={
    'en':(
        'The morning light fills the quiet room as a new day begins.',
        'A good story can help us see familiar places in a different way.',
        'We are reading a short passage to measure the speed of this voice.',
        'Along the river, people are enjoying a peaceful walk together.',
    ),
    'ja':(
        '朝の光が静かな部屋を照らし、新しい一日が始まります。',
        '川沿いの道を歩きながら、穏やかな景色を楽しみます。',
        'この短い文章で、選んだ声の読み上げ速度を測ります。',
        '物語を読むと、身近な世界にも新しい発見があります。',
    ),
    'ko':(
        '아침 햇살이 조용한 방을 비추며 새로운 하루가 시작됩니다.',
        '강가의 길을 걸으며 우리는 평화로운 풍경을 즐깁니다.',
        '선택한 목소리의 속도를 측정하기 위해 짧은 글을 읽습니다.',
        '좋은 이야기는 익숙한 세상을 새로운 시선으로 보게 합니다.',
    ),
    'zh':(
        '清晨的阳光照进安静的房间，新的一天开始了。',
        '我们沿着河边的小路散步，欣赏平静的风景。',
        '这段简短的文字用于测量所选声音的朗读速度。',
        '一个好故事可以让我们发现身边世界的不同面貌。',
    ),
    'fr':(
        'La lumière du matin éclaire la pièce et une nouvelle journée commence.',
        'Nous marchons au bord de la rivière pour profiter du paysage paisible.',
        'Ce court passage permet de mesurer la vitesse de la voix choisie.',
        'Une belle histoire nous aide à regarder le monde avec curiosité.',
    ),
    'de':(
        'Das Morgenlicht erfüllt den ruhigen Raum und ein neuer Tag beginnt.',
        'Wir gehen am Fluss entlang und genießen die friedliche Landschaft.',
        'Mit diesem kurzen Text messen wir die Geschwindigkeit der gewählten Stimme.',
        'Eine gute Geschichte lässt uns vertraute Orte mit neuen Augen sehen.',
    ),
    'es':(
        'La luz de la mañana ilumina la habitación y comienza un nuevo día.',
        'Caminamos junto al río para disfrutar de un paisaje tranquilo.',
        'Este breve texto sirve para medir la velocidad de la voz elegida.',
        'Una buena historia nos ayuda a descubrir el mundo con otros ojos.',
    ),
    'it':(
        'La luce del mattino illumina la stanza e comincia una nuova giornata.',
        'Camminiamo lungo il fiume per ammirare il paesaggio tranquillo.',
        'Questo breve testo misura la velocità della voce che hai scelto.',
        'Una bella storia ci aiuta a guardare il mondo con occhi nuovi.',
    ),
    'pt':(
        'A luz da manhã ilumina o quarto e um novo dia começa.',
        'Caminhamos ao lado do rio para apreciar uma paisagem tranquila.',
        'Este pequeno texto mede a velocidade da voz que você escolheu.',
        'Uma boa história nos ajuda a olhar o mundo de uma maneira diferente.',
    ),
    'ru':(
        'Утренний свет наполняет тихую комнату, и начинается новый день.',
        'Мы идём вдоль реки и любуемся спокойным пейзажем.',
        'Этот короткий текст помогает измерить скорость выбранного голоса.',
        'Хорошая история позволяет по-новому взглянуть на знакомый мир.',
    ),
    'th':(
        'แสงแดดยามเช้าส่องเข้ามาในห้องที่เงียบสงบและวันใหม่ก็เริ่มต้นขึ้น',
        'เราเดินเล่นริมแม่น้ำและชมทิวทัศน์ที่สวยงามอย่างสบายใจ',
        'ข้อความสั้นนี้ใช้วัดความเร็วในการสร้างเสียงที่คุณเลือก',
        'เรื่องราวที่ดีช่วยให้เรามองเห็นสิ่งรอบตัวจากมุมมองใหม่',
    ),
}
BENCHMARK_LANGUAGES=('vi','en-US','en-GB',*tuple(language for language in NATIVE_SAMPLES if language!='en'))


def sample_text(workers,language='vi'):
    # Multiple waves keep a many-core machine busy after every model is loaded.
    count=max(12,min(96,int(workers)*3))
    if language=='vi':
        return '\n'.join(SAMPLES[i%len(SAMPLES)]+f' Đây là đoạn đo số {i+1}.' for i in range(count))
    samples=_native_samples(language)
    return '\n'.join(samples[i%len(samples)] for i in range(count))


def _native_samples(language):
    if language not in BENCHMARK_LANGUAGES:
        raise ValueError('Chưa có văn bản đo tốc độ cho ngôn ngữ đã chọn.')
    return SAMPLES if language=='vi' else NATIVE_SAMPLES[language.split('-')[0]]


def benchmark_sample_text(language='vi',workers=1,engine='vieneu_nano'):
    """Keep international trials bounded while feeding every selected worker."""
    samples=_native_samples(language)
    if engine!='voxcpm':
        return sample_text(workers,language)
    count=max(4,min(16,max(1,int(workers))*2))
    return '\n'.join(samples[i%len(samples)] for i in range(count))


def read_saved_presets(data,defaults,engine='vieneu_nano',resident=None):
    # CPU calibration currently measures the two ONNX engines. International
    # inference uses a separate model/memory budget and must not reuse it.
    if engine not in {'vieneu_nano','vieneu'}:return defaults
    try:
        saved=json.loads((Path(data)/'calibration.json').read_text(encoding='utf-8'))
        if saved.get('logical_cores') != os.cpu_count():return defaults
        for key,record in saved.get('profiles',{}).items():
            if ':' in key:
                saved_engine,mode=key.split(':',1)
                if saved_engine!=engine:continue
            else:
                if engine!='vieneu_nano':continue
                mode=key
            if mode not in defaults:continue
            chosen=record['selected']['settings']
            if record['nano_steps'] != defaults[mode]['nano_steps']:continue
            workers,threads=chosen['nano_parallel'],chosen['nano_threads']
            # Available RAM already excludes resident models. Reuse a verified
            # loaded team instead of budgeting its memory for a second time.
            loaded=bool(resident and resident.get('engine')==engine and resident.get('workers',0)>=workers
                        and resident.get('threads')==threads and
                        (resident.get('precision')==record.get('precision') if engine=='vieneu'
                         else resident.get('nano_steps')==record['nano_steps']))
            if isinstance(workers,int) and isinstance(threads,int) and 1<=workers<=32 and (workers<=defaults[mode]['nano_parallel'] or loaded) and 1<=threads<=8:
                defaults[mode].update(nano_parallel=workers,nano_threads=threads)
    except (OSError,ValueError,KeyError,TypeError):
        pass
    return defaults


def cleanup_measurements(data,ident):
    """Remove only this calibration's private trials, also after a forced stop."""
    if not re.fullmatch(r'[0-9a-f]{32}',ident):return
    data=Path(data)
    pattern=re.compile(re.escape(ident)+r'-measure-[0-9a-f]{32}')
    for path in (data/'parts').glob(ident+'-measure-*'):
        if pattern.fullmatch(path.name):shutil.rmtree(path,ignore_errors=True)
    for path in (data/'audio').glob(ident+'-measure-*'):
        if pattern.fullmatch(path.stem):path.unlink(missing_ok=True)


def calibrate(job,render,close_pool,data=None):
    data=Path(data or os.environ['VOICE_STUDIO_DATA_DIR'])
    work=data/'parts'/job['id'];work.mkdir(parents=True,exist_ok=True)
    cleanup_measurements(data,job['id'])
    engine=job.get('engine','vieneu_nano')
    presets=rendering_presets(engine)
    mode=job.get('render_mode','fast')
    base=presets[mode]
    candidates=calibration_candidates(base)
    records=[];owned=[];best=None
    started=time.perf_counter()
    success=False
    close_pool()
    def cancelled():
        if (work/'cancel.flag').exists():raise InterruptedError('Đã dừng đo cấu hình; các bản thu khác được giữ nguyên.')
    def run(settings,phase,progress):
        cancelled()
        ident=job['id']+'-measure-'+uuid.uuid4().hex
        owned.append(ident)
        write_progress(work/'progress.json',{'progress':progress,'phase':f'Đang đo {settings["nano_parallel"]} tác vụ × {settings["nano_threads"]} luồng · {phase}'})
        measured={**job,**settings,'id':ident,'calibration':False,'format':'wav','input_format':'txt','paragraph_pause':0}
        before=time.perf_counter();render(measured);elapsed=time.perf_counter()-before
        cancelled()
        result=json.loads((data/'parts'/ident/'result.json').read_text(encoding='utf-8'))
        if result.get('duration_limited') or result.get('completed')!=result.get('total'):
            raise ValueError('Mẫu đo chưa hoàn tất; không lưu tốc độ từ bản thu thiếu lời.')
        report=speed_report(result['audio_seconds'],elapsed,result.get('spoken_audio_seconds'))
        if not report:raise ValueError('Mẫu đo chưa có lời đọc hợp lệ.')
        return ident,result,report
    try:
        for index,settings in enumerate(candidates):
            cold_id,_,cold=run(settings,'nạp model',round(90*(2*index)/(2*len(candidates))))
            ident,result,warm=run(settings,'model đã nạp',round(90*(2*index+1)/(2*len(candidates))))
            record={'settings':settings,'cold':cold,'warm':warm}
            records.append(record)
            if best is None or warm['realtime_multiplier']>best['record']['warm']['realtime_multiplier']:
                best={'record':record,'id':ident,'result':result}
        selected=best['record']
        # Leave the selected team loaded for the next real job, including when
        # a smaller team measured faster than the last candidate.
        if selected['settings']!=candidates[-1]:
            run(selected['settings'],'chuẩn bị cấu hình đã chọn',95)
        cancelled()
        for extension in ('wav','srt'):
            shutil.copyfile(data/'audio'/f'{best["id"]}.{extension}',data/'audio'/f'{job["id"]}.{extension}')
        report={'selected':selected,'candidates':records,'nano_steps':job['nano_steps'],'engine':engine,
                'precision':('int8' if job.get('quality')=='fast' else 'fp32') if engine=='vieneu' else None,
                'logical_cores':os.cpu_count(),'estimate_only':True,'target_30x_met_on_sample':selected['warm']['target_30x_met_on_sample'],
                'total_calibration_seconds':round(time.perf_counter()-started,3)}
        saved={'logical_cores':os.cpu_count(),'profiles':{}}
        try:
            previous=json.loads((data/'calibration.json').read_text(encoding='utf-8'))
            if previous.get('logical_cores')==os.cpu_count():saved=previous
        except (OSError,ValueError):pass
        saved.setdefault('profiles',{})[engine+':'+mode]=report
        write_json_atomic(data/'calibration.json',saved)
        final={**best['result'],**selected['settings'],'processing_seconds':report['total_calibration_seconds'],'calibration_report':report,'progress':100}
        write_json_atomic(work/'result.json',final)
        write_progress(work/'progress.json',{'progress':100,'phase':'Đã đo và lưu cấu hình phù hợp máy này'})
        success=True
    finally:
        if not success:close_pool()
        for ident in owned:
            shutil.rmtree(data/'parts'/ident,ignore_errors=True)
            for extension in ('wav','srt','mp3'):(data/'audio'/f'{ident}.{extension}').unlink(missing_ok=True)

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


def read_saved_presets(data,defaults,engine='vieneu_nano',resident=None,
                       resource_profile='maximum',execution_model='process',limits=None,precision=None,
                       use_auto_choice=False):
    # CPU calibration currently measures the two ONNX engines. International
    # inference uses a separate model/memory budget and must not reuse it.
    if engine not in {'vieneu_nano','vieneu'}:return defaults
    if resource_profile not in {'maximum','smooth','light'} or execution_model not in {'process','shared'}:
        return defaults
    try:
        saved=json.loads((Path(data)/'calibration.json').read_text(encoding='utf-8'))
        if saved.get('logical_cores') != os.cpu_count():return defaults
        profiles=saved.get('profiles',{})
        if not isinstance(profiles,dict):return defaults
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return defaults
    # A later explicit calibration of another precision can replace a legacy
    # four-part profile. Keep the exact team of the automatic, precision-scoped
    # winner available, subject to the same CPU/RAM checks below.
    profiles=dict(profiles)
    choices=saved.get('execution_choices',{})
    if use_auto_choice and isinstance(choices,dict) and (engine!='vieneu' or precision in {'fp32','int8'}):
        selected_precision=precision or 'fp32'
        for mode in defaults:
            choice=choices.get(f'{engine}:{resource_profile}:{mode}:{selected_precision}')
            if isinstance(choice,dict) and choice.get('model_memory')==execution_model:
                profiles[f'{engine}:{resource_profile}:{execution_model}:{mode}:{selected_precision}']={
                    'nano_steps':choice.get('nano_steps'),'resource_profile':resource_profile,
                    'model_memory':execution_model,'precision':selected_precision,
                    'selected':{'settings':choice.get('settings')}}
    # Reserve the CPU capacity represented by this profile, even if a resident
    # legacy team has enough memory to justify a larger model count.
    default_worker_limits={mode:value['nano_parallel'] for mode,value in defaults.items()}
    cpu_budget=max((value['nano_parallel']*value['nano_threads'] for value in defaults.values()),default=1)
    if limits is not None:
        try:
            cpu_budget=limits['cpu_budget']
            max_workers=limits['max_workers']
            max_threads=limits['max_threads']
            if any(type(value) is not int or value<1 for value in (cpu_budget,max_workers,max_threads)):
                return defaults
        except (KeyError,TypeError):return defaults
    # Scoped records supersede old keys, irrespective of JSON insertion order.
    for key,record in sorted(profiles.items(),key=lambda item:str(item[0]).count(':')):
        try:
            parts=key.split(':')
            if len(parts)==5:
                saved_engine,profile,memory,mode,saved_precision=parts
                if (saved_engine!=engine or profile!=resource_profile or memory!=execution_model
                        or saved_precision!=(precision or 'fp32')):continue
            elif len(parts)==4:
                saved_engine,profile,memory,mode=parts
                if saved_engine!=engine or profile!=resource_profile or memory!=execution_model:continue
            elif len(parts)==3:
                saved_engine,profile,mode=parts
                if saved_engine!=engine or profile!=resource_profile:continue
            elif len(parts)==2:
                saved_engine,mode=parts
                if saved_engine!=engine or resource_profile!='maximum' or execution_model!='process':continue
            elif len(parts)==1:
                if engine!='vieneu_nano' or resource_profile!='maximum' or execution_model!='process':continue
                mode=parts[0]
            else:continue
            if mode not in defaults or record.get('resource_profile',resource_profile)!=resource_profile:continue
            if record.get('model_memory','process')!=execution_model:continue
            if engine=='vieneu' and precision is not None and record.get('precision')!=precision:continue
            chosen=record['selected']['settings']
            if record['nano_steps']!=defaults[mode]['nano_steps']:continue
            workers,threads=chosen['nano_parallel'],chosen['nano_threads']
            if (type(workers) is not int or type(threads) is not int or not 1<=workers<=32
                    or not 1<=threads<=8 or workers*threads>cpu_budget):continue
            if limits is not None and (workers>max_workers or threads>max_threads):continue
            # The shared runtime's warm allocation is credited by hardware.py.
            # Only legacy maximum/process records retain the old credit path.
            loaded=bool(execution_model=='process' and resource_profile=='maximum'
                        and resident and resident.get('engine')==engine
                        and resident.get('model_memory','process')=='process'
                        and resident.get('workers',0)>=workers and resident.get('threads')==threads
                        and (resident.get('precision')==record.get('precision') if engine=='vieneu'
                             else resident.get('nano_steps')==record['nano_steps']))
            if workers<=default_worker_limits[mode] or loaded or limits is not None:
                defaults[mode].update(nano_parallel=workers,nano_threads=threads)
        except (AttributeError,KeyError,TypeError,ValueError):
            continue
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
    resource_profile=job.get('resource_profile','maximum')
    mode=job.get('render_mode','fast')
    precision='int8' if engine=='vieneu' and job.get('quality')=='fast' else 'fp32'
    compare=job.get('cpu_execution')=='auto' and engine in {'vieneu_nano','vieneu'}
    executions=('shared','process') if compare else (job.get('model_memory','process'),)
    candidates=[]
    for memory in executions:
        presets=rendering_presets(engine,resource_profile=resource_profile,precision=precision,
                                  execution_model=memory)
        candidates.extend((memory,settings) for settings in calibration_candidates(presets[mode]))
    trial_text=job.get('text','')
    if compare:
        language=job.get('language','vi')
        samples=(
            'Hôm nay trời nắng đẹp và có gió nhẹ.',
            'Một câu chuyện hay mang đến nhiều cảm xúc.',
            'Chúng ta cùng bước đi trên con đường nhỏ.',
            'Giọng đọc rõ ràng giúp người nghe dễ hiểu.',
        ) if language=='vi' else _native_samples(language)
        count=max(8,min(64,max(settings['nano_parallel'] for _,settings in candidates)*2))
        trial_text='\n'.join(samples[index%len(samples)] for index in range(count))
    records=[];owned=[];best=None
    best_by_execution={}
    started=time.perf_counter()
    success=False
    close_pool()
    def cancelled():
        if (work/'cancel.flag').exists():raise InterruptedError('Đã dừng đo cấu hình; các bản thu khác được giữ nguyên.')
    def run(memory,settings,phase,progress):
        cancelled()
        ident=job['id']+'-measure-'+uuid.uuid4().hex
        owned.append(ident)
        label='dùng chung mô hình' if memory=='shared' else 'tiến trình riêng'
        write_progress(work/'progress.json',{'progress':progress,'phase':f'Đang đo {label} · {settings["nano_parallel"]} tác vụ × {settings["nano_threads"]} luồng · {phase}'})
        measured={**job,**settings,'model_memory':memory,'text':trial_text,'id':ident,'calibration':False,'format':'wav','input_format':'txt','paragraph_pause':0}
        before=time.perf_counter();render(measured);elapsed=time.perf_counter()-before
        cancelled()
        result=json.loads((data/'parts'/ident/'result.json').read_text(encoding='utf-8'))
        if result.get('duration_limited') or result.get('completed')!=result.get('total'):
            raise ValueError('Mẫu đo chưa hoàn tất; không lưu tốc độ từ bản thu thiếu lời.')
        report=speed_report(result['audio_seconds'],elapsed,result.get('spoken_audio_seconds'))
        if not report:raise ValueError('Mẫu đo chưa có lời đọc hợp lệ.')
        return ident,result,report
    try:
        for index,(memory,settings) in enumerate(candidates):
            cold_id,_,cold=run(memory,settings,'nạp model',round(90*(2*index)/(2*len(candidates))))
            ident,result,warm=run(memory,settings,'model đã nạp',round(90*(2*index+1)/(2*len(candidates))))
            record={'settings':settings,'model_memory':memory,'cold':cold,'warm':warm}
            records.append(record)
            previous=best_by_execution.get(memory)
            if previous is None or warm['realtime_multiplier']>previous['record']['warm']['realtime_multiplier']:
                best_by_execution[memory]={'record':record,'id':ident,'result':result}
        if compare:
            shared=best_by_execution['shared'];process=best_by_execution['process']
            # A small noisy gain does not justify loading a copy of every
            # weight in each process. Both candidates use the same voice,
            # precision, quality steps and text throughout the comparison.
            best=process if process['record']['warm']['realtime_multiplier']>shared['record']['warm']['realtime_multiplier']*1.05 else shared
        else:
            best=best_by_execution[executions[0]]
        selected=best['record']
        # Leave the selected team loaded for the next real job, including when
        # a smaller team measured faster than the last candidate.
        if (selected['model_memory'],selected['settings'])!=candidates[-1]:
            run(selected['model_memory'],selected['settings'],'chuẩn bị cấu hình đã chọn',95)
        cancelled()
        for extension in ('wav','srt'):
            shutil.copyfile(data/'audio'/f'{best["id"]}.{extension}',data/'audio'/f'{job["id"]}.{extension}')
        report={'selected':selected,'candidates':records,'nano_steps':job['nano_steps'],'engine':engine,
                'precision':precision if engine=='vieneu' else None,
                'resource_profile':resource_profile,
                'model_memory':selected['model_memory'],
                'logical_cores':os.cpu_count(),'estimate_only':True,'target_30x_met_on_sample':selected['warm']['target_30x_met_on_sample'],
                'total_calibration_seconds':round(time.perf_counter()-started,3)}
        saved={'logical_cores':os.cpu_count(),'profiles':{}}
        try:
            previous=json.loads((data/'calibration.json').read_text(encoding='utf-8'))
            if (previous.get('logical_cores')==os.cpu_count()
                    and isinstance(previous.get('profiles',{}),dict)):saved=previous
        except (OSError,ValueError,AttributeError):pass
        for memory,chosen in best_by_execution.items():
            scoped={**report,'selected':chosen['record'],'candidates':[record for record in records if record['model_memory']==memory],
                    'model_memory':memory,'target_30x_met_on_sample':chosen['record']['warm']['target_30x_met_on_sample']}
            saved.setdefault('profiles',{})[engine+':'+resource_profile+':'+memory+':'+mode]=scoped
        if compare:
            comparison={memory:chosen['record']['warm'] for memory,chosen in best_by_execution.items()}
            report['execution_comparison']=comparison
            choices=saved.get('execution_choices')
            if not isinstance(choices,dict):choices={};saved['execution_choices']=choices
            choices[f'{engine}:{resource_profile}:{mode}:{precision}']={
                'model_memory':selected['model_memory'],'settings':selected['settings'],
                'nano_steps':job['nano_steps'],'measurements':comparison}
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

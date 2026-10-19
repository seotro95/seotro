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


def sample_text(workers):
    # Multiple waves keep a many-core machine busy after every model is loaded.
    count=max(12,min(96,int(workers)*3))
    return '\n'.join(SAMPLES[i%len(SAMPLES)]+f' Đây là đoạn đo số {i+1}.' for i in range(count))


def read_saved_presets(data,defaults,engine='vieneu_nano',resident=None):
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

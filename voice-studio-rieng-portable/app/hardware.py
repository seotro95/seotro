def supports_int8():
    try:
        from numpy._core._multiarray_umath import __cpu_features__
        return bool(__cpu_features__.get('AVX512VNNI') or __cpu_features__.get('AVXVNNI'))
    except (ImportError, AttributeError):
        return False


def system_info(include_cuda_probe=True):
    import json
    import os
    import platform
    import shutil
    import subprocess
    import sys
    cpu = platform.processor() or platform.machine()
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
        except OSError:
            pass
    elif sys.platform.startswith('linux'):
        try:
            from pathlib import Path
            cpu = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
        except (OSError, StopIteration):
            pass
    try:
        import psutil
        ram = round(psutil.virtual_memory().total / 1024**3, 1)
        physical = psutil.cpu_count(logical=False)
    except ImportError:
        ram = None
        physical = None
    gpus = []
    if shutil.which('nvidia-smi'):
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                gpus = result.stdout.strip().splitlines()[:8]
        except (OSError, subprocess.TimeoutExpired):
            pass
    cuda = None
    if include_cuda_probe:
        try:
            result = subprocess.run([sys.executable, '-c', 'import json,torch; print(json.dumps({"cuda":torch.cuda.is_available()}))'], capture_output=True, text=True, timeout=20, check=False)
            if result.returncode == 0:
                cuda = json.loads(result.stdout.strip().splitlines()[-1])['cuda']
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            pass
    return {'cpu': cpu, 'logical_cores': os.cpu_count(), 'physical_cores': physical, 'ram_gb': ram, 'nvidia_gpus': gpus, 'pytorch_cuda_available': cuda, 'int8_vnni': supports_int8(), 'note': 'Các giọng Nano/Turbo trong gói này chạy CPU; có card NVIDIA không tự làm Nano dùng GPU. Đo mẫu để biết tốc độ thực tế trên máy đang chạy tool.'}



RESOURCE_PROFILES=('maximum','smooth','light')


def _resource_profile(value):
    if value not in RESOURCE_PROFILES:
        raise ValueError('Chọn cấu hình tài nguyên maximum, smooth hoặc light.')
    return value


def _cpu_budget(physical,resource_profile):
    if resource_profile=='light':return min(2,physical)
    reserve=(2 if physical>=24 else 1 if physical>=8 else 0) if resource_profile=='smooth' else 0
    return max(1,physical-reserve)


def _resident_credit(engine,resident,precision,execution_model='shared'):
    """Credit only a compatible resident allocation that the API verified alive."""
    if not isinstance(resident,dict) or resident.get('engine')!=engine:return 0
    workers,threads=resident.get('workers'),resident.get('threads')
    maximum=8 if engine=='voxcpm' else 32
    if type(workers) is not int or not 1<=workers<=maximum:return 0
    if type(threads) is not int or not 1<=threads<=8:return 0
    if engine=='voxcpm':
        if resident.get('precision')!=precision:return 0
        return workers*(8 if precision=='int8' else 16)*1024**3
    if resident.get('model_memory','process')!=execution_model:return 0
    if engine=='vieneu_nano':
        # Nano execution reports historically omit precision: its CPU model
        # has no user-selectable INT8 variant. Do not count a mismatched mode.
        if precision!='fp32' or resident.get('precision','fp32')!='fp32':return 0
        if execution_model=='shared':return int((1+.25*workers)*1024**3)
        return int(1.25*workers*1024**3)
    if engine=='vieneu' and resident.get('precision')==precision:
        if execution_model=='shared':return int((3+.5*workers)*1024**3)
        return workers*(1 if precision=='int8' else 3)*1024**3
    return 0


def _machine_resources(engine,resident=None,precision='fp32',execution_model='shared'):
    import os
    import math
    from pathlib import Path
    logical=os.cpu_count() or 1
    cores=logical
    try:
        cores=min(cores,len(os.sched_getaffinity(0)))
    except (AttributeError,OSError):
        pass
    # psutil is also available on Windows, where sched_getaffinity is absent.
    try:
        import psutil
    except ImportError:
        pass
    else:
        try:
            affinity=psutil.Process().cpu_affinity()
            if affinity:cores=min(cores,len(affinity))
        except (AttributeError,OSError,psutil.Error):
            pass
    affinity_cores=cores
    quota=Path('/sys/fs/cgroup/cpu.max')
    if quota.is_file():
        try:
            maximum,period=quota.read_text().split()
            if maximum!='max':cores=min(cores,max(1,int(maximum)//int(period)))
        except (OSError,ValueError,ZeroDivisionError):
            pass
    try:
        import psutil
        memory=psutil.virtual_memory()
        available=memory.available
        total=getattr(memory,'total',available)
        credit=_resident_credit(engine,resident,precision,execution_model)
        available=min(total,available+credit)
        cap=Path('/sys/fs/cgroup/memory.max')
        used=Path('/sys/fs/cgroup/memory.current')
        if cap.is_file() and used.is_file() and cap.read_text().strip()!='max':
            ceiling=int(cap.read_text())
            available=min(available,ceiling,max(0,ceiling-int(used.read_text()))+credit)
        ram_gb=available/1024**3
    except (ImportError,OSError,ValueError):
        ram_gb=0
    try:
        import psutil
        total_physical=psutil.cpu_count(logical=False) or logical
        # A restricted logical affinity must not be counted as that many
        # physical cores on a Hyper-Threaded machine. Without a per-socket
        # topology API, proportionally cap the affinity's physical capacity.
        # CPU quotas are applied afterwards; four scheduled cores remain four
        # even when the host exposes hundreds of logical CPUs.
        physical=min(cores,total_physical,max(1,math.ceil(affinity_cores*total_physical/logical)))
    except ImportError:
        physical=cores
    return cores,physical,ram_gb


def rendering_presets(engine='vieneu_nano',resident=None,resource_profile='smooth',precision='fp32',execution_model='shared'):
    """Default to a reserved CPU budget; maximum preserves the old policy."""
    return resource_presets(*_machine_resources(engine,resident,precision,execution_model),engine,
                            resource_profile=resource_profile,precision=precision,execution_model=execution_model)


def rendering_limits(engine='vieneu_nano',resident=None,resource_profile='smooth',precision='fp32',execution_model='shared'):
    limits=resource_limits(*_machine_resources(engine,resident,precision,execution_model),engine,
                           resource_profile=resource_profile,precision=precision,execution_model=execution_model)
    # A compatible live backend needs no cold model conversion. Its reservation
    # may be smaller than the startup threshold (notably for compact INT8).
    if engine=='voxcpm' and _resident_credit(engine,resident,precision,execution_model)>0:
        limits['memory_sufficient']=True
    return limits


def native_voxcpm_cpu_limits(resource_profile='smooth'):
    """Budget independent native Q8 CPU models, without legacy FP32 credit.

    Each worker owns a mutable native session and its reference/KV caches.
    Reserve six GiB for each cold model/workspace and four GiB outside the
    worker team. This is a conservative admission budget, not measured peak
    memory or a promise of linear scaling across sockets.
    """
    import math

    _resource_profile(resource_profile)
    logical, physical, available = _machine_resources('voxcpm_native', None, 'fp32', 'process')
    physical = max(1, min(int(logical), int(physical)))
    cpu = _cpu_budget(physical, resource_profile)
    if isinstance(available, bool) or not isinstance(available, (int, float)) or not math.isfinite(available):
        available = 0
    memory_workers = max(0, int((max(0, available) - 4) // 6))
    workers = max(1, min(8, cpu, memory_workers))
    if resource_profile == 'light':
        workers = 1
    return {'cpu_budget': cpu, 'max_workers': workers,
            'max_threads': min(2 if resource_profile == 'light' else 8, cpu),
            'memory_sufficient': available >= 10,
            'available_memory_gb': max(0, available),
            'per_worker_memory_budget_gb': 6, 'memory_reserve_gb': 4,
            'minimum_available_gb': 10}


def native_voxcpm_cpu_presets(resource_profile='smooth'):
    """Prefer four threads per native model while retaining synthesis quality."""
    limits = native_voxcpm_cpu_limits(resource_profile)
    cpu = limits['cpu_budget']
    workers = min(limits['max_workers'], max(1, cpu // 4))
    threads = min(4, limits['max_threads'], max(1, cpu // workers))
    def settings(steps, backend):
        return {'nano_parallel': workers, 'nano_threads': threads,
                'voxcpm_steps': steps, 'audio_fit_backend': backend}
    return {'fast': settings(4, 'wsola'),
            'balanced': settings(8, 'ffmpeg'),
            'quality': settings(10, 'ffmpeg')}


def choose_execution_model(engine,resource_profile='smooth',cpu_execution='auto',resident=None,precision='fp32',
                           data=None,render_mode='fast'):
    """Use the measured ONNX winner, retaining shared weights until measured.

    A large core count alone does not prove independent Python processes are
    faster. Explicit selections remain available; automatic selection requires
    a completed comparison on this machine and a team that still fits its
    current CPU/RAM budget. Non-ONNX engines keep their isolated backend.
    """
    _resource_profile(resource_profile)
    if not isinstance(cpu_execution,str) or cpu_execution not in {'auto','process','shared'}:
        raise ValueError('Chọn cơ chế CPU auto, process hoặc shared.')
    if not isinstance(precision,str) or precision not in {'fp32','int8'}:
        raise ValueError('Định dạng model không hợp lệ.')
    if engine not in {'vieneu_nano','vieneu'}:return 'process'
    if cpu_execution!='auto':return cpu_execution
    if data is None or render_mode not in {'fast','balanced','quality'}:return 'shared'
    try:
        import json
        import math
        import os
        from pathlib import Path
        saved=json.loads((Path(data)/'calibration.json').read_text(encoding='utf-8'))
        if saved.get('logical_cores')!=os.cpu_count():return 'shared'
        record=saved['execution_choices'][f'{engine}:{resource_profile}:{render_mode}:{precision}']
        memory=record['model_memory']
        if memory not in {'shared','process'}:return 'shared'
        measured=record['measurements']
        speeds={name:measured[name]['realtime_multiplier'] for name in ('shared','process')}
        if any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)
               or value<=0 for value in speeds.values()):return 'shared'
        expected='process' if speeds['process']>speeds['shared']*1.05 else 'shared'
        if memory!=expected:return 'shared'
        team=record['settings']
        workers,threads=team['nano_parallel'],team['nano_threads']
        limits=rendering_limits(engine,resident=resident,resource_profile=resource_profile,
                                precision=precision,execution_model=memory)
        if (type(workers) is not int or type(threads) is not int or not 1<=workers<=limits['max_workers']
                or not 1<=threads<=limits['max_threads'] or workers*threads>limits['cpu_budget']):return 'shared'
        presets=rendering_presets(engine,resident=resident,resource_profile=resource_profile,
                                  precision=precision,execution_model=memory)
        if record['nano_steps']!=presets[render_mode]['nano_steps']:return 'shared'
        return memory
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return 'shared'


def resource_limits(logical,physical,available_gb,engine='vieneu_nano',resource_profile='maximum',precision='fp32',execution_model='process'):
    """Hard worker/thread ceilings, separate from each quality-mode preset."""
    _resource_profile(resource_profile)
    if precision not in {'fp32','int8'}:raise ValueError('Định dạng model không hợp lệ.')
    if execution_model not in {'process','shared'}:raise ValueError('Cấu hình bộ nhớ model không hợp lệ.')
    physical=max(1,min(logical,physical))
    cpu=_cpu_budget(physical,resource_profile)
    if engine=='voxcpm':
        # INT8 reduces warm RAM, but conversion temporarily holds FP32 weights.
        # Budget cold startup, including simultaneous model conversions.
        per_model=20 if precision=='int8' else 16
        memory=max(1,int(max(0,available_gb-4)/per_model)) if available_gb else 1
        workers=max(1,min(8,max(1,cpu//2),memory))
    elif engine=='vieneu_nano' and execution_model=='shared':
        # Shared ORT sessions/constants, independent per-sequence workspaces.
        memory=max(1,int(max(0,available_gb-2.5)/.25)) if available_gb else 1
        workers=max(1,min(32,cpu,memory))
    elif engine=='vieneu' and execution_model=='shared':
        memory=max(1,int(max(0,available_gb-4.5)/.5)) if available_gb else 1
        workers=max(1,min(32,cpu,memory))
    else:
        per_model=1.25 if engine=='vieneu_nano' else 3
        memory=max(1,int(max(0,available_gb-1.5)/per_model)) if available_gb else 1
        workers=max(1,min(32,cpu,memory))
    if resource_profile=='light':workers=1
    return {'max_workers':workers,'max_threads':min(2 if resource_profile=='light' else 8,cpu),
            'cpu_budget':cpu,
            'memory_sufficient':available_gb>=(24 if precision=='int8' else 20) if engine=='voxcpm' else True}


def _uniform_team(maximum,cpu):
    # Select a team with the greatest useful uniform CPU budget. Prefer more
    # independent sequences when two teams use the same number of CPU cores.
    return max(range(1,maximum+1),key=lambda workers:(workers*min(8,cpu//workers),workers))


def resource_presets(logical,physical,available_gb,engine='vieneu_nano',resource_profile='maximum',precision='fp32',execution_model='process'):
    """Use physical CPU/RAM capacity while keeping model quality independent."""
    limits=resource_limits(logical,physical,available_gb,engine,resource_profile,precision,execution_model)
    cpu,maximum=limits['cpu_budget'],limits['max_workers']
    if engine=='voxcpm':
        fast=maximum
        if resource_profile=='smooth' or precision=='int8':fast=_uniform_team(maximum,cpu)
        # The quality selector controls diffusion steps, not how much of the
        # independent CPU/RAM profile may be used. Reducing both previously
        # left a many-core machine mostly idle at the highest quality: with
        # 28 physical cores, smooth quality used only one 8-thread model.
        # All step counts can run the same safely budgeted independent cues.
        def settings(workers,steps,backend):
            return {'voxcpm_steps':steps,'nano_parallel':workers,
                    'nano_threads':min(limits['max_threads'],max(1,cpu//workers)),
                    'audio_fit_backend':backend}
        return {'fast':settings(fast,4,'wsola'),
                'balanced':settings(fast,8,'ffmpeg'),
                'quality':settings(fast,10,'ffmpeg')}
    balanced=min(maximum,16,max(1,cpu//2))
    quality=min(maximum,8,max(1,cpu//4))
    def settings(workers,steps,threads,backend):
        return {'nano_steps':steps,'nano_parallel':workers,
                'nano_threads':min(limits['max_threads'],threads,max(1,cpu//workers)),
                'audio_fit_backend':backend}
    return {'fast':settings(maximum,4,2,'wsola'),
            'balanced':settings(balanced,8,2,'ffmpeg'),
            'quality':settings(quality,16,4,'ffmpeg')}


def bounded_settings(selected,allowed):
    """Clamp explicit tuning to the actual RAM, physical-CPU and profile limits."""
    def integer(value,name):
        if type(value) is not int or value<1:raise ValueError('Cấu hình tài nguyên không hợp lệ: '+name)
        return value
    maximum=integer(allowed.get('max_workers',allowed.get('nano_parallel')),'workers')
    thread_limit=integer(allowed.get('max_threads',8),'threads')
    budget=integer(allowed.get('cpu_budget',maximum*allowed.get('nano_threads',1)),'CPU')
    workers=min(maximum,integer(selected.get('nano_parallel',maximum),'workers'))
    threads=min(thread_limit,max(1,budget//workers),integer(selected.get('nano_threads',thread_limit),'threads'))
    return {**selected,'nano_parallel':workers,'nano_threads':threads}


def calibration_candidates(preset,engine='vieneu_nano'):
    """Compare fewer/larger ORT teams with more single-thread model workers."""
    maximum=preset['nano_parallel']
    cores=max(1,maximum*preset['nano_threads'])
    candidates=[{'nano_parallel':max(1,maximum//2),'nano_threads':min(2,max(1,cores//max(1,maximum//2)))},
                {'nano_parallel':max(1,maximum*3//4),'nano_threads':1},
                {'nano_parallel':maximum,'nano_threads':preset['nano_threads']}]
    if engine=='vieneu' and maximum>=12:
        # A large shared decoder team can compete for memory bandwidth or
        # Python scheduling. Measure smaller Turbo teams rather than assuming
        # that every available model worker improves actual throughput.
        candidates=[{'nano_parallel':workers,'nano_threads':min(threads,max(1,cores//workers))}
                    for workers,threads in ((4,4),(8,2))]+candidates
    result=[]
    for candidate in candidates:
        if candidate not in result:result.append(candidate)
    return result

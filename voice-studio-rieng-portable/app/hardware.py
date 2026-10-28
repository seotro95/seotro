def supports_int8():
    try:
        from numpy._core._multiarray_umath import __cpu_features__
        return bool(__cpu_features__.get('AVX512VNNI') or __cpu_features__.get('AVXVNNI'))
    except (ImportError, AttributeError):
        return False


def system_info():
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
    try:
        result = subprocess.run([sys.executable, '-c', 'import json,torch; print(json.dumps({"cuda":torch.cuda.is_available()}))'], capture_output=True, text=True, timeout=20, check=False)
        if result.returncode == 0:
            cuda = json.loads(result.stdout.strip().splitlines()[-1])['cuda']
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        pass
    return {'cpu': cpu, 'logical_cores': os.cpu_count(), 'physical_cores': physical, 'ram_gb': ram, 'nvidia_gpus': gpus, 'pytorch_cuda_available': cuda, 'int8_vnni': supports_int8(), 'note': 'Các giọng Nano/Turbo trong gói này chạy CPU; có card NVIDIA không tự làm Nano dùng GPU. Đo mẫu để biết tốc độ thực tế trên máy đang chạy tool.'}


def rendering_presets(engine='vieneu_nano',resident=None):
    """Conservative CPU/RAM budgets; GPU presence is not a Nano accelerator."""
    import os
    from pathlib import Path
    cores=os.cpu_count() or 1
    try:
        cores=min(cores,len(os.sched_getaffinity(0)))
    except (AttributeError,OSError):
        pass
    quota=Path('/sys/fs/cgroup/cpu.max')
    if quota.is_file():
        try:
            maximum,period=quota.read_text().split()
            if maximum!='max':cores=min(cores,max(1,int(maximum)//int(period)))
        except (OSError,ValueError):
            pass
    try:
        import psutil
        memory=psutil.virtual_memory()
        available=memory.available
        total=getattr(memory,'total',available)
        # A verified resident team already owns its model allocations. Credit
        # that reservation once so the next request can reuse the same team.
        credit=0
        if (engine=='voxcpm' and isinstance(resident,dict)
                and resident.get('engine')=='voxcpm' and resident.get('precision')=='fp32'
                and type(resident.get('workers')) is int and 1<=resident['workers']<=8
                and type(resident.get('threads')) is int and 1<=resident['threads']<=8):
            credit=resident['workers']*16*1024**3
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
        physical=min(cores,psutil.cpu_count(logical=False) or cores)
    except ImportError:
        physical=cores
    return resource_presets(cores,physical,ram_gb,engine)


def resource_presets(logical,physical,available_gb,engine='vieneu_nano'):
    """Use physical CPU capacity; Hyper-Threading is not another model budget."""
    physical=max(1,min(logical,physical))
    if engine=='voxcpm':
        # Each isolated FP32 VoxCPM2 process has its own model allocation.
        # Leave room for Windows/the studio and for transient model loading;
        # reusing the much smaller Nano budget can exhaust a 128 GiB machine.
        memory_workers=max(1,int(max(0,available_gb-4)/16)) if available_gb else 1
        cpu_workers=max(1,physical//2)
        fast=max(1,min(8,cpu_workers,memory_workers))
        balanced=max(1,fast//2)
        quality=max(1,fast//4)
        def settings(workers,steps,backend):
            return {'voxcpm_steps':steps,'nano_parallel':workers,
                    'nano_threads':max(1,min(8,physical//workers)),
                    'audio_fit_backend':backend}
        return {'fast':settings(fast,4,'wsola'),
                'balanced':settings(balanced,8,'ffmpeg'),
                'quality':settings(quality,10,'ffmpeg')}
    per_worker_gb=3 if engine=='vieneu' else 1.25
    memory_workers=max(1,int(max(0,available_gb-1.5)/per_worker_gb)) if available_gb else 1
    fast=max(1,min(32,physical,memory_workers))
    balanced=max(1,min(16,max(1,physical//2),memory_workers))
    quality=max(1,min(8,max(1,physical//4),memory_workers))
    return {
        'fast':{'nano_steps':4,'nano_parallel':fast,'nano_threads':max(1,min(2,physical//fast)),'audio_fit_backend':'wsola'},
        'balanced':{'nano_steps':8,'nano_parallel':balanced,'nano_threads':max(1,min(2,physical//balanced)),'audio_fit_backend':'ffmpeg'},
        'quality':{'nano_steps':16,'nano_parallel':quality,'nano_threads':max(1,min(4,physical//quality)),'audio_fit_backend':'ffmpeg'},
    }


def calibration_candidates(preset):
    """Compare fewer/larger ORT teams with more single-thread model workers."""
    maximum=preset['nano_parallel']
    cores=max(1,maximum*preset['nano_threads'])
    candidates=[{'nano_parallel':max(1,maximum//2),'nano_threads':min(2,max(1,cores//max(1,maximum//2)))},
                {'nano_parallel':max(1,maximum*3//4),'nano_threads':1},
                {'nano_parallel':maximum,'nano_threads':preset['nano_threads']}]
    result=[]
    for candidate in candidates:
        if candidate not in result:result.append(candidate)
    return result

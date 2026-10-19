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
    except ImportError:
        ram = None
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
    return {'cpu': cpu, 'logical_cores': os.cpu_count(), 'ram_gb': ram, 'nvidia_gpus': gpus, 'pytorch_cuda_available': cuda, 'int8_vnni': supports_int8(), 'note': 'Các giọng Nano/Turbo trong gói này chạy CPU; có card NVIDIA không tự làm Nano dùng GPU. Đo mẫu để biết tốc độ thực tế trên máy đang chạy tool.'}


def rendering_presets():
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
        available=psutil.virtual_memory().available
        cap=Path('/sys/fs/cgroup/memory.max')
        used=Path('/sys/fs/cgroup/memory.current')
        if cap.is_file() and used.is_file() and cap.read_text().strip()!='max':
            available=min(available,max(0,int(cap.read_text())-int(used.read_text())))
        ram_gb=available/1024**3
    except (ImportError,OSError,ValueError):
        ram_gb=0
    # Model sessions plus Python/audio libraries need headroom, especially on Windows.
    memory_workers=max(1,int(max(0,ram_gb-1.5)/1.25)) if ram_gb else 1
    fast_workers=max(1,min(8,cores,memory_workers))
    balanced_workers=max(1,min(2,max(1,cores//2),memory_workers))
    return {
        'fast':{'nano_steps':4,'nano_parallel':fast_workers,'nano_threads':max(1,min(2,cores//fast_workers)), 'audio_fit_backend':'wsola'},
        'balanced':{'nano_steps':8,'nano_parallel':balanced_workers,'nano_threads':max(1,min(2,cores//balanced_workers)), 'audio_fit_backend':'ffmpeg'},
        'quality':{'nano_steps':16,'nano_parallel':1,'nano_threads':max(1,min(4,cores)), 'audio_fit_backend':'ffmpeg'},
    }

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
    return {'cpu': cpu, 'logical_cores': os.cpu_count(), 'ram_gb': ram, 'nvidia_gpus': gpus, 'pytorch_cuda_available': cuda, 'int8_vnni': supports_int8(), 'note': 'Nano hiện chạy CPU. Qwen chỉ dùng GPU nếu PyTorch CUDA khả dụng. Tốc độ thực tế cần đo bằng mẫu âm thanh.'}

import ctypes
import io
import subprocess
from types import SimpleNamespace

import pytest

import gpu_info


def test_parse_nvidia_name_memory_and_driver():
    assert gpu_info.parse_nvidia_output("NVIDIA GeForce GTX 1060 6GB, 6144 MiB, 560.94\n") == [
        gpu_info.NvidiaGpu("NVIDIA GeForce GTX 1060 6GB", 6144, "560.94")
    ]


def test_parse_multiple_devices_and_csv_names():
    assert gpu_info.parse_nvidia_output('"NVIDIA, Test", 8192, 535.154.05\nGPU 2, 4096 MiB, 560.94\n') == [
        gpu_info.NvidiaGpu("NVIDIA, Test", 8192, "535.154.05"),
        gpu_info.NvidiaGpu("GPU 2", 4096, "560.94"),
    ]


@pytest.mark.parametrize("output", [
    "", "GPU, 6144 MiB", "GPU, 6144 MiB, 560.94, extra",
    "GPU, N/A, 560.94", "GPU, -1 MiB, 560.94", "GPU, 6144 MiB, unknown",
    '"broken, 6144 MiB, 560.94', '"GPU\nname", 6144 MiB, 560.94',
    "GPU\x1b, 6144 MiB, 560.94", "a" * (gpu_info.MAX_OUTPUT_BYTES + 1),
])
def test_invalid_nvidia_output_is_rejected(output):
    with pytest.raises(ValueError):
        gpu_info.parse_nvidia_output(output)


class FakeProcess:
    def __init__(self, output=b"GPU, 6144 MiB, 560.94\n", *, timeout=False, returncode=0):
        self.stdout = io.BytesIO(output)
        self.timeout = timeout
        self.returncode = returncode
        self.wait_timeouts = []
        self.killed = False

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        if self.timeout and len(self.wait_timeouts) == 1:
            raise subprocess.TimeoutExpired(gpu_info.NVIDIA_COMMAND, timeout)
        return self.returncode

    def kill(self):
        self.killed = True


def test_nvidia_command_has_fixed_arguments_and_timeout(monkeypatch):
    process = FakeProcess()
    calls = []

    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return process

    monkeypatch.setattr(gpu_info.subprocess, "Popen", launch)
    gpus, message = gpu_info.query_nvidia_gpus()
    assert gpus == [gpu_info.NvidiaGpu("GPU", 6144, "560.94")]
    assert message == ""
    assert calls == [(list(gpu_info.NVIDIA_COMMAND), {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "shell": False,
    })]
    assert process.wait_timeouts == [5]


@pytest.mark.parametrize("output,returncode", [
    (b"bad CSV", 0), (b"GPU, 6144 MiB, 560.94\n", 1), (b"\xff", 0),
])
def test_nvidia_failures_do_not_report_fake_hardware(monkeypatch, output, returncode):
    monkeypatch.setattr(gpu_info.subprocess, "Popen", lambda *a, **kw: FakeProcess(output, returncode=returncode))
    gpus, message = gpu_info.query_nvidia_gpus()
    assert gpus == []
    assert message


def test_nvidia_timeout_kills_query(monkeypatch):
    process = FakeProcess(timeout=True)
    monkeypatch.setattr(gpu_info.subprocess, "Popen", lambda *a, **kw: process)
    gpus, message = gpu_info.query_nvidia_gpus()
    assert gpus == []
    assert "5 giay" in message
    assert process.killed
    assert process.wait_timeouts == [5, 1]


def test_nvidia_output_limit_kills_query(monkeypatch):
    process = FakeProcess(b"a" * (gpu_info.MAX_OUTPUT_BYTES + 100_000))
    monkeypatch.setattr(gpu_info.subprocess, "Popen", lambda *a, **kw: process)
    gpus, message = gpu_info.query_nvidia_gpus()
    assert gpus == []
    assert "64 KiB" in message
    assert process.killed


def test_missing_nvidia_command_is_optional(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(gpu_info.subprocess, "Popen", missing)
    assert gpu_info.query_nvidia_gpus() == ([], "Khong tim thay nvidia-smi.")


def test_windows_api_structure_and_enumeration_with_stub(monkeypatch):
    class FakeEnum:
        def __call__(self, device_name, index, pointer, flags):
            assert device_name is None and flags == 0
            device = ctypes.cast(pointer, ctypes.POINTER(gpu_info._DisplayDevice)).contents
            assert device.cb == ctypes.sizeof(gpu_info._DisplayDevice)
            if index == 0:
                device.DeviceString = "NVIDIA GeForce GTX 1060 6GB"
                return 1
            return 0

    enum = FakeEnum()
    monkeypatch.setattr(gpu_info.platform, "system", lambda: "Windows")
    monkeypatch.setattr(gpu_info.ctypes, "windll", SimpleNamespace(user32=SimpleNamespace(EnumDisplayDevicesW=enum)), raising=False)
    assert gpu_info.read_windows_adapters() == ["NVIDIA GeForce GTX 1060 6GB"]
    assert enum.restype is ctypes.c_int
    assert len(enum.argtypes) == 4


def test_windows_enumeration_is_bounded_and_deduplicated():
    indices = []

    def enum(device_name, index, pointer, flags):
        indices.append(index)
        ctypes.cast(pointer, ctypes.POINTER(gpu_info._DisplayDevice)).contents.DeviceString = "Same GPU"
        return 1

    assert gpu_info._enumerate_display_devices(enum) == ["Same GPU"]
    assert indices == list(range(32))


def test_non_windows_does_not_attempt_windows_api(monkeypatch):
    monkeypatch.setattr(gpu_info.platform, "system", lambda: "Linux")
    assert gpu_info.read_windows_adapters() == []


def test_no_hardware_gives_honest_dxdiag_fallback(monkeypatch, capsys):
    monkeypatch.setattr(gpu_info, "read_windows_adapters", lambda: [])
    monkeypatch.setattr(gpu_info, "query_nvidia_gpus", lambda: ([], "Khong tim thay nvidia-smi."))
    assert gpu_info.main() == 0
    output = capsys.readouterr().out
    assert "dxdiag" in output and "Display/Hien thi" in output
    assert "GTX" not in output
    assert output.isascii()


def test_hardware_names_are_printed_as_plain_ascii(monkeypatch, capsys):
    monkeypatch.setattr(gpu_info, "read_windows_adapters", lambda: ["GPU\x1b\n\u00e9"])
    monkeypatch.setattr(gpu_info, "query_nvidia_gpus", lambda: ([gpu_info.NvidiaGpu("GTX 1060", 6144, "560.94")], ""))
    assert gpu_info.main() == 0
    output = capsys.readouterr().out
    assert "GPU: GPU???" in output
    assert "6144 MiB, driver 560.94" in output
    assert output.isascii() and "\x1b" not in output

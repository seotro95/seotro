"""Read GPU information without installing software or changing drivers.

This optional diagnostic uses the Windows display API and an existing
``nvidia-smi`` command. It does not establish that a GPU can run the TTS model.
"""

from __future__ import annotations

import csv
import ctypes
import io
import platform
import re
import subprocess
import threading
from dataclasses import dataclass


MAX_OUTPUT_BYTES = 64 * 1024
QUERY_TIMEOUT_SECONDS = 5
NVIDIA_COMMAND = (
    "nvidia-smi",
    "--query-gpu=name,memory.total,driver_version",
    "--format=csv,noheader",
)


@dataclass(frozen=True)
class NvidiaGpu:
    name: str
    memory_mib: int
    driver: str


class _DisplayDevice(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_uint32),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", ctypes.c_uint32),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


def _enumerate_display_devices(enum_display_devices) -> list[str]:
    """Enumerate a bounded number of adapters using EnumDisplayDevicesW."""
    names = []
    for index in range(32):
        device = _DisplayDevice()
        device.cb = ctypes.sizeof(device)
        if not enum_display_devices(None, index, ctypes.byref(device), 0):
            break
        name = device.DeviceString.strip() or device.DeviceName.strip()
        if name and name not in names:
            names.append(name)
    return names


def read_windows_adapters() -> list[str]:
    if platform.system() != "Windows":
        return []
    try:
        enum_display_devices = ctypes.windll.user32.EnumDisplayDevicesW
        enum_display_devices.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.POINTER(_DisplayDevice),
            ctypes.c_uint32,
        ]
        enum_display_devices.restype = ctypes.c_int
        return _enumerate_display_devices(enum_display_devices)
    except (AttributeError, OSError):
        return []


def parse_nvidia_output(output: str) -> list[NvidiaGpu]:
    if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("NVIDIA output exceeds the diagnostic limit")
    gpus = []
    try:
        for row in csv.reader(io.StringIO(output), strict=True):
            if not row or all(not field.strip() for field in row):
                continue
            if len(row) != 3:
                raise ValueError("Expected three NVIDIA fields")
            name, memory, driver = (field.strip() for field in row)
            if not name or len(name) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in name):
                raise ValueError("Invalid NVIDIA name")
            memory_match = re.fullmatch(r"([0-9]{1,9})(?:\s+MiB)?", memory)
            if not memory_match or not re.fullmatch(r"[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}", driver):
                raise ValueError("Invalid NVIDIA memory or driver")
            gpus.append(NvidiaGpu(name, int(memory_match.group(1)), driver))
    except csv.Error as error:
        raise ValueError("Invalid NVIDIA CSV") from error
    if not gpus:
        raise ValueError("No NVIDIA GPU data")
    return gpus


def query_nvidia_gpus() -> tuple[list[NvidiaGpu], str]:
    """Run a fixed read-only query, retaining at most 64 KiB for five seconds."""
    try:
        process = subprocess.Popen(
            list(NVIDIA_COMMAND),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    except FileNotFoundError:
        return [], "Khong tim thay nvidia-smi."
    except OSError:
        return [], "Khong chay duoc lenh doc NVIDIA."

    output = bytearray()
    overflow = threading.Event()
    read_error = threading.Event()

    def read_output() -> None:
        try:
            assert process.stdout is not None
            while True:
                # The final probe detects excess output without retaining it.
                chunk = process.stdout.read(min(4096, MAX_OUTPUT_BYTES - len(output) + 1))
                if not chunk:
                    break
                remaining = MAX_OUTPUT_BYTES - len(output)
                output.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    process.kill()
                    break
        except (OSError, ValueError):
            read_error.set()

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=QUERY_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        try:
            returncode = process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            returncode = -1
    reader.join(timeout=1)
    if not reader.is_alive() and process.stdout is not None:
        process.stdout.close()
    if timed_out:
        return [], "NVIDIA khong phan hoi sau 5 giay."
    if overflow.is_set():
        return [], "Du lieu NVIDIA vuot gioi han 64 KiB."
    if returncode or read_error.is_set() or reader.is_alive():
        return [], "Khong doc duoc thong tin NVIDIA."
    try:
        return parse_nvidia_output(bytes(output).decode("utf-8", errors="strict")), ""
    except (UnicodeError, ValueError):
        return [], "Thong tin NVIDIA tra ve khong hop le."


def _ascii(value: str) -> str:
    return "".join(character if 32 <= ord(character) <= 126 else "?" for character in value)


def main() -> int:
    print("HMONG STUDIO - THONG TIN GPU TREN MAY NAY")
    print("Chi doc thong tin, khong cai hay thay doi driver.")
    adapters = read_windows_adapters()
    for name in adapters:
        print("GPU: " + _ascii(name))
    nvidia_gpus, message = query_nvidia_gpus()
    for gpu in nvidia_gpus:
        print(f"NVIDIA: {_ascii(gpu.name)}, {gpu.memory_mib} MiB, driver {gpu.driver}")
    if message:
        print(message)
    if not adapters and not nvidia_gpus:
        print("Khong doc duoc ten GPU. Tren Windows: mo dxdiag, chon Display/Hien thi.")
    print("Can ten card va VRAM de chon cach tang toc phu hop.")
    print("DirectX 12 chi la phien ban phan mem, khong phai ten GPU.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

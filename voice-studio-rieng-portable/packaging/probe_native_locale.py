"""Measure the pinned native byte-whitespace algorithm against Windows UCRT.

This probe downloads no model, performs no synthesis and changes no application
files. A tiny MSVC /MD DLL reproduces normalize_wrapper_text byte for byte and
checks that Python locale changes reach the same dynamic UCRT instance.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SAMPLES = {
    'ko': '선택한 목소리의 속도를 측정하기 위해 짧은 글을 읽습니다.',
    'zh': '你好',
}

CPP = r'''#include <cctype>
#include <clocale>
#include <cstddef>
extern "C" __declspec(dllexport) int probe_isspace(int value) {
    return std::isspace(static_cast<unsigned char>(value));
}
extern "C" __declspec(dllexport) const char* probe_ctype_locale() {
    return std::setlocale(LC_CTYPE, nullptr);
}
extern "C" __declspec(dllexport) std::size_t probe_normalize(
    const unsigned char* text, std::size_t length, unsigned char* out,
    std::size_t capacity) {
    std::size_t used = 0;
    bool in_space = false;
    for (std::size_t i = 0; i < length; ++i) {
        const unsigned char ch = text[i];
        if (std::isspace(ch)) {
            if (!in_space) {
                if (used >= capacity) return capacity + 1;
                out[used++] = ' ';
                in_space = true;
            }
            continue;
        }
        if (used >= capacity) return capacity + 1;
        out[used++] = ch;
        in_space = false;
    }
    return used;
}
'''


def normalize_bytes(payload, isspace):
    """Exact byte loop in pinned VoxCPM2 generator.cpp, not Unicode splitting."""
    output = bytearray()
    in_space = False
    for value in payload:
        if isspace(value):
            if not in_space:
                output.append(32)
                in_space = True
            continue
        output.append(value)
        in_space = False
    return bytes(output)


def compile_probe(directory, required):
    compiler = shutil.which('cl.exe')
    if compiler is None:
        if required:
            raise RuntimeError('MSVC cl.exe is required for the shared-UCRT probe')
        return None
    source, library = directory / 'locale_probe.cpp', directory / 'locale_probe.dll'
    source.write_text(CPP, encoding='ascii')
    result = subprocess.run(
        [compiler, '/nologo', '/LD', '/MD', '/EHsc', '/std:c++17', str(source),
         '/link', '/OUT:' + str(library)], cwd=directory, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    if result.returncode or not library.is_file():
        raise RuntimeError('MSVC /MD probe compilation failed: ' + result.stdout[-8000:])
    dll = ctypes.CDLL(str(library))
    dll.probe_isspace.argtypes = [ctypes.c_int]
    dll.probe_isspace.restype = ctypes.c_int
    dll.probe_ctype_locale.argtypes = []
    dll.probe_ctype_locale.restype = ctypes.c_char_p
    dll.probe_normalize.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                    ctypes.c_void_p, ctypes.c_size_t]
    dll.probe_normalize.restype = ctypes.c_size_t
    return dll


def sample_report(text, isspace, compiled):
    source = text.encode('utf-8')
    output = normalize_bytes(source, isspace)
    if compiled is not None:
        incoming = ctypes.create_string_buffer(source)
        outgoing = ctypes.create_string_buffer(len(source) + 1)
        length = compiled.probe_normalize(incoming, len(source), outgoing, len(source) + 1)
        if length > len(source) or outgoing.raw[:length] != output:
            raise AssertionError('Compiled std::isspace normalization differs from the Python byte loop')
    try:
        decoded, valid = output.decode('utf-8'), True
    except UnicodeDecodeError:
        decoded, valid = output.decode('utf-8', 'replace'), False
    return {'input_text': text, 'input_utf8_hex': source.hex(),
            'input_codepoints': [f'U+{ord(c):04X}' for c in text],
            'output_utf8_hex': output.hex(), 'output_text': decoded,
            'output_codepoints': [f'U+{ord(c):04X}' for c in decoded],
            'valid_utf8': valid, 'utf8_bytes_preserved': output == source,
            'compiled_algorithm_matches': compiled is not None}


def run_probe(require_compiled=False):
    if os.name != 'nt' or sys.platform != 'win32':
        raise RuntimeError('Run this UCRT probe on actual Windows')
    original_all = locale.setlocale(locale.LC_ALL)
    original_ctype = locale.setlocale(locale.LC_CTYPE)
    ucrt = ctypes.CDLL('ucrtbase.dll')
    ucrt.isspace.argtypes, ucrt.isspace.restype = [ctypes.c_int], ctypes.c_int
    rows = []
    compiled = None
    directory = Path(tempfile.mkdtemp(prefix='native-ucrt-probe-'))
    try:
        compiled = compile_probe(directory, require_compiled)
        for label, requested in (('initial', None), ('default', ''), ('C', 'C'),
                                 ('cp1258', '.1258'), ('cp1252', '.1252'), ('utf8', '.UTF8')):
            try:
                if requested is not None:
                    locale.setlocale(locale.LC_CTYPE, requested)
                effective = locale.setlocale(locale.LC_CTYPE)
            except locale.Error as error:
                rows.append({'requested': label, 'available': False, 'error': str(error)})
                continue
            classifications = [bool(ucrt.isspace(value)) for value in range(256)]
            if compiled is not None:
                if any(bool(compiled.probe_isspace(value)) != classifications[value]
                       for value in range(256)):
                    raise AssertionError('MSVC /MD DLL and ctypes UCRT use different LC_CTYPE tables')
                native_locale = compiled.probe_ctype_locale().decode('ascii', 'replace')
                if native_locale != effective:
                    raise AssertionError(f'Python and MSVC /MD DLL locales differ: {effective!r} versus {native_locale!r}')
            else:
                native_locale = None
            rows.append({'requested': label, 'available': True, 'effective_lc_ctype': effective,
                         'msvc_md_effective_lc_ctype': native_locale,
                         'space_bytes_hex': [f'{n:02X}' for n, space in enumerate(classifications) if space],
                         'isspace_A0': classifications[0xA0], 'isspace_85': classifications[0x85],
                         'shared_ucrt_256_byte_table_matches': compiled is not None,
                         'samples': {language: sample_report(text, ucrt.isspace, compiled)
                                     for language, text in SAMPLES.items()}})
    finally:
        locale.setlocale(locale.LC_ALL, original_all)
        restored = (locale.setlocale(locale.LC_ALL) == original_all
                    and locale.setlocale(locale.LC_CTYPE) == original_ctype)
        # A loaded Windows DLL cannot be unlinked. Keep its tiny source/DLL in
        # the OS temporary directory until this short probe process exits.
        if compiled is None:
            shutil.rmtree(directory)
    c_row = next(row for row in rows if row['requested'] == 'C' and row['available'])
    if c_row['space_bytes_hex'] != ['09', '0A', '0B', '0C', '0D', '20']:
        raise AssertionError('The C locale classified a non-ASCII byte as whitespace')
    if not all(sample['utf8_bytes_preserved'] and sample['valid_utf8']
               for sample in c_row['samples'].values()):
        raise AssertionError('C locale did not preserve Korean/Chinese UTF-8')
    corrupted = [row['requested'] for row in rows if row['available'] and row['isspace_A0']
                 and any(not sample['utf8_bytes_preserved'] for sample in row['samples'].values())]
    if not corrupted:
        raise AssertionError('Could not reproduce byte-A0 UTF-8 corruption in a Windows non-C locale')
    if not restored:
        raise AssertionError('The original LC_CTYPE was not restored')
    return {'format': 'voice-studio-windows-ucrt-utf8-probe-v1', 'platform': sys.platform,
            'source_commit': os.environ.get('GITHUB_SHA'), 'original_lc_ctype': original_ctype,
            'original_all_locale_restored': restored, 'compiled_msvc_dynamic_ucrt': compiled is not None,
            'c_locale_preserves_korean_and_chinese_utf8': True,
            'non_c_byte_A0_corruption_reproduced': corrupted, 'locales': rows,
            'model_downloaded': False, 'model_inference_tested': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--require-compiled', action='store_true')
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError('Choose a new report path')
    report = run_probe(args.require_compiled)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    compact = json.dumps(report, ensure_ascii=False, separators=(',', ':'))
    print(compact, flush=True)
    escaped = compact.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=Windows UCRT UTF8 locale probe::' + escaped, flush=True)


if __name__ == '__main__':
    main()

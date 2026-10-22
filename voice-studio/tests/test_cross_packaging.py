"""Checks for cross-built dependency closure and archive path handling."""
import importlib.util
from pathlib import Path
import zipfile

import pytest

spec = importlib.util.spec_from_file_location('cross_windows_builder', Path(__file__).resolve().parents[1] / 'packaging' / 'build_cross_windows.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.mark.parametrize('name', ['../secret', '/absolute/path', 'C:/Windows/file', 'folder\\file'])
def test_foreign_archive_paths_cannot_escape(name):
    with pytest.raises(ValueError):
        builder.safe_parts(name)


def test_windows_marker_dependencies_are_required_even_on_linux(tmp_path):
    wheel = tmp_path / 'package.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('package-1.0.dist-info/METADATA', 'Name: package\nVersion: 1.0\nRequires-Dist: colorama; platform_system == "Windows"\nRequires-Dist: irrelevant; sys_platform == "linux"\n')
    assert builder.missing_windows_requirements([wheel]) == ['colorama']


def test_wheel_data_libraries_use_runtime_site_packages(tmp_path):
    wheel = tmp_path / 'package.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('package-1.0.data/platlib/native.pyd', b'fake-native')
        archive.writestr('package-1.0.data/data/assets/license.txt', 'license')
        archive.writestr('package/__init__.py', '')
    runtime = tmp_path / 'runtime'
    builder.install_wheel(wheel, runtime)
    assert (runtime / 'Lib/site-packages/native.pyd').read_bytes() == b'fake-native'
    assert (runtime / 'assets/license.txt').read_text() == 'license'

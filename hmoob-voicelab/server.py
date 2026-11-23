"""Loopback-only, standard-library HTTP API for Hmoob VoiceLab."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit
import zipfile

from jobs import JobManager
from longform import MAX_CHARACTERS, MAX_JSON_BYTES
from runtime_lock import DataLock
from voices import Voices
from version import APP_VERSION

BASE = Path(__file__).resolve().parent


def make_server(data, host='127.0.0.1', port=8123, engine=None, engine_status=None):
    if host not in ('127.0.0.1', 'localhost'):
        raise ValueError('Tool chỉ mở trên máy hiện tại (127.0.0.1).')
    if engine is None:
        from engine import SpeechEngine, availability
        engine, engine_status = SpeechEngine(), availability
    data_lock = DataLock(data)
    try:
        voices = Voices(data)
        manager = JobManager(data, voices, engine)
    except Exception:
        data_lock.close()
        raise

    class Handler(BaseHTTPRequestHandler):
        server_version = 'HmoobVoiceLab/' + APP_VERSION

        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, fmt, *args):
            # Requests only; never print submitted transcripts or model credentials.
            super().log_message(fmt, *args)

        def _json(self, value, status=200):
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(raw)

        def _guard(self):
            if self.headers.get('Host', '').split(':')[0] not in ('127.0.0.1', 'localhost'):
                raise PermissionError('Địa chỉ máy chủ không hợp lệ.')
            origin = self.headers.get('Origin')
            if origin and origin != f'http://{self.headers.get("Host")}':
                raise PermissionError('Yêu cầu phải đến từ giao diện của tool.')

        def _body(self):
            if self.headers.get('Content-Type', '').split(';')[0].lower() != 'application/json':
                raise ValueError('Yêu cầu cần Content-Type application/json.')
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                raise ValueError('Độ dài yêu cầu không hợp lệ.') from None
            if not 0 < length <= MAX_JSON_BYTES:
                raise ValueError('Yêu cầu quá lớn hoặc rỗng; tối đa 1.000.000 ký tự văn bản.')
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('Nội dung yêu cầu chưa tải đầy đủ.')
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ValueError('JSON không hợp lệ.') from None
            if not isinstance(value, dict):
                raise ValueError('Yêu cầu phải là đối tượng JSON.')
            return value

        def _file(self, path, mime, download=None):
            path = Path(path)
            if not path.is_file():
                raise KeyError('Không tìm thấy tệp.')
            size, start, end = path.stat().st_size, 0, path.stat().st_size - 1
            status = 200
            if self.headers.get('Range'):
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers['Range'])
                if not match or not any(match.groups()):
                    self.send_error(416)
                    return
                first, last = match.groups()
                if first:
                    start = int(first)
                    end = min(end, int(last)) if last else end
                else:
                    start = max(0, size - int(last))
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{size}')
                    self.end_headers()
                    return
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(max(0, end - start + 1)))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'")
            if status == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            if download:
                self.send_header('Content-Disposition', f'attachment; filename="{download}"')
            self.end_headers()
            if self.command == 'HEAD':
                return
            with path.open('rb') as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    block = source.read(min(128 * 1024, remaining))
                    if not block:
                        return
                    self.wfile.write(block)
                    remaining -= len(block)

        def _archive(self, ident):
            job = manager.get(ident)
            if job['status'] != 'done':
                raise ValueError('Chờ hoàn tất để tải tất cả; có thể tải riêng chương đã xong.')
            folder = manager.folder(ident)
            required = sum((folder / 'parts' / part['name']).stat().st_size for part in job['parts'])
            if shutil.disk_usage(folder).free < required + 64 * 1024**2:
                raise ValueError('Không đủ chỗ tạo ZIP. Tải từng chương WAV để không cần thêm dung lượng.')
            with tempfile.TemporaryDirectory(prefix='download-', dir=folder) as temporary:
                archive = Path(temporary) / 'voice.zip'
                with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as output:
                    output.write(folder / 'text.txt', 'script.txt')
                    output.writestr('manifest.json', json.dumps(job, ensure_ascii=False, indent=2))
                    for part in job['parts']:
                        output.write(folder / 'parts' / part['name'], part['name'])
                self._file(archive, 'application/zip', 'hmoob-voice.zip')

        def _route(self):
            self._guard()
            parts = urlsplit(self.path).path.strip('/').split('/')
            if self.command in ('GET', 'HEAD'):
                if parts == ['']:
                    return self._file(BASE / 'web' / 'index.html', 'text/html; charset=utf-8')
                if parts[0] == 'web' and len(parts) == 2 and parts[1] in ('app.js', 'style.css', 'index.html'):
                    mime = {'app.js': 'text/javascript', 'style.css': 'text/css', 'index.html': 'text/html'}[parts[1]]
                    return self._file(BASE / 'web' / parts[1], mime + '; charset=utf-8')
                if parts == ['api', 'status']:
                    return self._json({'max_characters': MAX_CHARACTERS, 'engine': engine_status(),
                                       'ffmpeg': bool(shutil.which('ffmpeg')), 'version': APP_VERSION})
                if parts == ['api', 'voices']:
                    return self._json({'voices': voices.all()})
                if len(parts) == 4 and parts[:2] == ['api', 'voices'] and parts[3] == 'sample':
                    return self._file(voices.sample(parts[2]), 'audio/mpeg')
                if parts == ['api', 'jobs']:
                    return self._json({'jobs': manager.list()})
                if len(parts) >= 3 and parts[:2] == ['api', 'jobs']:
                    ident = parts[2]
                    job = manager.get(ident)
                    if len(parts) == 3:
                        return self._json({'job': job})
                    if len(parts) == 4 and parts[3] == 'text':
                        return self._file(manager.folder(ident) / 'text.txt', 'text/plain; charset=utf-8', 'script.txt')
                    if len(parts) == 4 and parts[3] == 'archive':
                        return self._archive(ident)
                    if len(parts) == 5 and parts[3] == 'parts' and any(p['name'] == parts[4] for p in job['parts']):
                        return self._file(manager.folder(ident) / 'parts' / parts[4], 'audio/wav')
            elif self.command == 'POST':
                payload = self._body()
                if len(parts) == 4 and parts[:2] == ['api', 'voices'] and parts[3] == 'reference':
                    return self._json({'voice': voices.save(parts[2], payload)})
                if parts == ['api', 'jobs']:
                    # Validate even when the model is missing, so the editor gets
                    # a precise boundary error rather than a misleading 503.
                    from jobs import validate_options
                    validate_options(payload)
                    state = engine_status()
                    if not state['ready']:
                        return self._json({'error': state['reason']}, 503)
                    return self._json({'job': manager.create(payload)}, 201)
                if len(parts) == 4 and parts[:2] == ['api', 'jobs']:
                    if parts[3] == 'cancel':
                        return self._json({'job': manager.cancel(parts[2])})
                    if parts[3] == 'resume':
                        state = engine_status()
                        if not state['ready']:
                            return self._json({'error': state['reason']}, 503)
                        return self._json({'job': manager.resume(parts[2])})
            raise KeyError('Không tìm thấy đường dẫn.')

        def _handle(self):
            try:
                self._route()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except PermissionError as exc:
                self._json({'error': str(exc)}, 403)
            except KeyError:
                self._json({'error': 'Không tìm thấy tác vụ hoặc tệp.'}, 404)
            except (ValueError, TypeError) as exc:
                self._json({'error': str(exc)}, 422)
            except Exception:
                self._json({'error': 'Lỗi máy chủ. Kiểm tra dung lượng đĩa, quyền ghi và tệp cấu hình.'}, 500)

        do_GET = do_HEAD = do_POST = _handle

    class VoiceServer(ThreadingHTTPServer):
        def server_close(self):
            super().server_close()
            manager.close()
            data_lock.close()

    try:
        server = VoiceServer((host, port), Handler)
    except Exception:
        data_lock.close()
        raise
    server.daemon_threads = True
    server.manager = manager
    manager.start()
    return server

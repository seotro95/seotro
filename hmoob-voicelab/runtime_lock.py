"""A process-lifetime lock prevents two servers modifying the same jobs."""
from pathlib import Path
import os


class DataLock:
    def __init__(self, data):
        Path(data).mkdir(parents=True, exist_ok=True)
        self.handle = (Path(data) / '.instance.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if self.handle.seek(0, 2) == 0:
                    self.handle.write(b'0')
                    self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise ValueError('Một phiên Hmoob VoiceLab khác đang dùng thư mục dữ liệu này. Đóng phiên đó trước.') from None

    def close(self):
        if self.handle.closed:
            return
        if os.name == 'nt':
            import msvcrt
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()

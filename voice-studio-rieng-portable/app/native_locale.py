"""Keep UTF-8 text intact in the pinned native library's byte classifiers.

MSVC's byte-wise isspace can treat an UTF-8 continuation byte as whitespace
under a Windows ANSI locale. NativeSession runs in its isolated stdio child;
use the C character locale there and normalize actual Unicode whitespace in
Python. Neither operation transliterates, drops or replaces spoken letters.
"""
from contextlib import contextmanager
import locale


@contextmanager
def native_character_locale():
    """Scope LC_CTYPE to one isolated native session, then restore it."""
    previous = locale.setlocale(locale.LC_CTYPE)
    try:
        locale.setlocale(locale.LC_CTYPE, 'C')
        yield
    finally:
        locale.setlocale(locale.LC_CTYPE, previous)


def normalize_native_text(text):
    if not isinstance(text, str) or '\x00' in text:
        raise ValueError('Văn bản native chứa ký tự không hợp lệ.')
    try:
        text.encode('utf-8', errors='strict')
    except UnicodeEncodeError:
        raise ValueError('Văn bản có ký tự Unicode không hợp lệ; hãy dán lại nội dung.') from None
    return ' '.join(text.split())

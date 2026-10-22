"""Keep VieNeu reference preprocessing inside the configured studio data folder."""
import os
import tempfile
from pathlib import Path

from vieneu.v3turbo import V3TurboVieNeuTTS


class LocalVieneu(V3TurboVieNeuTTS):
    @staticmethod
    def _preclean_reference_audio(ref_audio, *, top_db=30, out_path=None):
        if out_path is not None:
            return V3TurboVieNeuTTS._preclean_reference_audio(ref_audio, top_db=top_db, out_path=out_path)
        root = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(Path(__file__).resolve().parent / '.data'))) / 'tmp'
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, path = tempfile.mkstemp(prefix='reference-', suffix='.wav', dir=root)
        os.close(descriptor)
        try:
            cleaned = V3TurboVieNeuTTS._preclean_reference_audio(ref_audio, top_db=top_db, out_path=path)
            if Path(cleaned).resolve() != Path(path).resolve():
                Path(path).unlink(missing_ok=True)
            return cleaned
        except Exception:
            Path(path).unlink(missing_ok=True)
            raise

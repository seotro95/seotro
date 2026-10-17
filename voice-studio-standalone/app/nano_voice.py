"""Enroll a Nano reference once while keeping temporary audio in studio data."""
from pathlib import Path


def load_nano_reference(model, reference):
    from local_vieneu import LocalVieneu
    reference = Path(reference)
    clean = LocalVieneu._preclean_reference_audio(reference)
    try:
        speaker, style = model.engine.prepare_reference(str(clean), denoise=False)
        return {'speaker_emb': speaker, 'style': style}
    finally:
        if clean and Path(clean).resolve() != reference.resolve():
            Path(clean).unlink(missing_ok=True)

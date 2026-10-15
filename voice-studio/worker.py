"""One inference per process: models are released when the process exits."""
import json
import os
import subprocess
import sys
from pathlib import Path

DATA = Path(os.environ['VOICE_STUDIO_DATA_DIR'])
LANGUAGES = {'en-US': 'English', 'en-GB': 'English', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese', 'fr': 'French', 'de': 'German', 'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian'}


def render(job):
    import soundfile as sf
    output = DATA / 'audio' / (job['id'] + '.raw.wav')
    if job['engine'] == 'vieneu':
        from local_vieneu import LocalVieneu
        model = LocalVieneu(backend='onnx', threads=int(os.environ.get('OMP_NUM_THREADS', '4')))
        if job.get('speaker'):
            samples = model.infer(job['text'], voice=job['speaker'])
        else:
            samples = model.infer(job['text'], ref_audio=str(DATA / 'voices' / (job['voice_id'] + '.wav')), denoise=False)
        model.save(samples, str(output))
    else:
        import torch
        from qwen_tts import Qwen3TTSModel
        from huggingface_hub import snapshot_download
        torch.set_num_threads(int(os.environ.get('OMP_NUM_THREADS', '4')))
        gpu = torch.cuda.is_available()
        suffix = 'Base' if job['engine'] == 'qwen_clone' else 'CustomVoice'
        model_path = snapshot_download(f'Qwen/Qwen3-TTS-12Hz-0.6B-{suffix}', local_files_only=True)
        model = Qwen3TTSModel.from_pretrained(model_path, device_map='cuda:0' if gpu else 'cpu', dtype=torch.bfloat16 if gpu else torch.float32, attn_implementation='sdpa')
        if job['engine'] == 'qwen_clone':
            voice = json.loads((DATA / 'voices' / (job['voice_id'] + '.json')).read_text(encoding='utf-8'))
            reference_text = voice.get('transcript', '').strip()
            samples, rate = model.generate_voice_clone(text=job['text'], language=LANGUAGES[job['language']], ref_audio=str(DATA / 'voices' / (job['voice_id'] + '.wav')), ref_text=reference_text or None, x_vector_only_mode=not bool(reference_text), max_new_tokens=2048)
        else:
            samples, rate = model.generate_custom_voice(text=job['text'], language=LANGUAGES[job['language']], speaker=job['speaker'], max_new_tokens=2048)
        sf.write(str(output), samples[0], rate)
    destination = DATA / 'audio' / f"{job['id']}.{job['format']}"
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(output), '-af', f"atempo={job['speed']}", '-y']
    if job['format'] == 'mp3':
        command += ['-codec:a', 'libmp3lame', '-b:a', '192k']
    subprocess.run(command + [str(destination)], check=True, timeout=120)
    output.unlink(missing_ok=True)


if __name__ == '__main__':
    render(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))

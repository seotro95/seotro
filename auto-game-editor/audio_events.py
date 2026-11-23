"""Nhận diện lời nói, tiếng cười và tiếng khóc từ âm thanh trên máy."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import urllib.request
from zipfile import ZipFile

MODEL = Path(__file__).resolve().parent / "editor-assets" / "yamnet.tflite"
URL = ("https://storage.googleapis.com/download.tensorflow.org/models/tflite/task_library/"
       "audio_classification/android/lite-model_yamnet_classification_tflite_1.tflite")
SHA256 = "10c95ea3eb9a7bb4cb8bddf6feb023250381008177ac162ce169694d05c317de"
RATE = 16000
HOP = RATE // 2


def install_model():
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    if MODEL.is_file() and hashlib.sha256(MODEL.read_bytes()).hexdigest() == SHA256:
        return
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = response.read(5 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("Mô hình tải về không khớp mã SHA-256.")
    with tempfile.TemporaryDirectory(dir=MODEL.parent) as directory:
        temporary = Path(directory) / MODEL.name
        temporary.write_bytes(data)
        temporary.replace(MODEL)


class AudioEvents:
    def __init__(self):
        import numpy as np
        from ai_edge_litert.interpreter import Interpreter

        if not MODEL.is_file():
            raise FileNotFoundError("Cần chạy Cai-dat.cmd để tải mô hình âm thanh.")
        self.np = np
        self.model = Interpreter(model_path=str(MODEL), num_threads=1)
        self.model.allocate_tensors()
        input_details = self.model.get_input_details()[0]
        self.samples = int(input_details["shape"][0])
        self.input = input_details["index"]
        self.output = self.model.get_output_details()[0]["index"]
        with ZipFile(MODEL) as archive:
            labels = archive.read("yamnet_label_list.txt").decode().splitlines()
        self.speech = self.indices(labels, ("Speech", "Conversation", "Narration, monologue",
                                            "Whispering", "Child speech, kid speaking"))
        self.laugh = self.indices(labels, ("Laughter", "Giggle", "Snicker", "Belly laugh",
                                           "Chuckle, chortle"))
        self.cry = self.indices(labels, ("Crying, sobbing", "Whimper", "Wail, moan"))

    @staticmethod
    def indices(labels, names):
        return [labels.index(name) for name in names]

    def read(self, source, audio_index, start, length):
        command = ["ffmpeg", "-v", "error", "-nostdin", "-ss", str(start), "-i", str(source),
                   "-t", str(length), "-map", f"0:{audio_index}", "-vn", "-ac", "1",
                   "-ar", str(RATE), "-c:a", "pcm_f32le", "-f", "f32le", "-"]
        speech = []
        stickers = []
        with tempfile.TemporaryFile() as errors, subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=errors
        ) as process:
            try:
                window = process.stdout.read(self.samples * 4)
                for i in range(length * 2):
                    if not window:
                        break
                    if len(window) < self.samples * 4:
                        window = window.ljust(self.samples * 4, b"\0")
                    wave = self.np.frombuffer(window, dtype="<f4").astype(self.np.float32, copy=False)
                    time = i / 2
                    if self.np.max(self.np.abs(wave)) >= .004:
                        self.model.set_tensor(self.input, wave)
                        self.model.invoke()
                        scores = self.model.get_tensor(self.output)[0]
                        if max(scores[self.speech]) >= .50:
                            speech.append(time)
                        laugh, cry = max(scores[self.laugh]), max(scores[self.cry])
                        if max(laugh, cry) >= .36:
                            stickers.append((time, "laugh" if laugh >= cry else "cry", max(laugh, cry)))
                    next_audio = process.stdout.read(HOP * 4)
                    if not next_audio:
                        break
                    window = window[HOP * 4:] + next_audio
                if process.wait():
                    errors.seek(max(0, errors.tell() - 8192))
                    raise subprocess.CalledProcessError(process.returncode, command, stderr=errors.read())
            finally:
                if process.poll() is None:
                    process.kill()
        return speech, stickers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", action="store_true")
    args = parser.parse_args()
    if args.setup:
        install_model()
        AudioEvents()
        print("Sẵn sàng nhận diện lời nói, tiếng cười và tiếng khóc.")
    else:
        parser.print_help()

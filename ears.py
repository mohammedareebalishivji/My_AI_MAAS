import speech_recognition as sr
import numpy as np
import tempfile
import os
import torch

class JarvisEars:
    def __init__(self, model_size="tiny"):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"

        print(f"[Ears] Loading Whisper '{model_size}' on {self.device}...")
        import whisper
        self.model = whisper.load_model(model_size, device=self.device)
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True

        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            print(f"[Ears] Microphone error: {e}")
            self.microphone = None

        print("[Ears] Ready.")

    def listen(self):
        if not self.microphone:
            return None

        with self.microphone as source:
            try:
                audio_data = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

                fd, tmp_path = tempfile.mkstemp(suffix=".wav", dir="/tmp")
                try:
                    with os.fdopen(fd, 'wb') as f:
                        f.write(audio_data.get_wav_data())

                    result = self.model.transcribe(
                        tmp_path,
                        fp16=(self.device == "cuda"),
                        language="en",
                        beam_size=1,
                        best_of=1,
                        condition_on_previous_text=False,
                        compression_ratio_threshold=2.4,
                        no_speech_threshold=0.5,
                    )
                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

                text = result['text'].strip()
                if text and len(text) > 2 and text.lower() not in ["thank you.", "bye.", "you"]:
                    return text
                return None

            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                print(f"[Ears] Transcription error: {e}")
                return None


if __name__ == "__main__":
    ears = JarvisEars()
    while True:
        text = ears.listen()
        if text:
            print(f"You said: {text}")
            if "exit" in text.lower() or "quit" in text.lower():
                break

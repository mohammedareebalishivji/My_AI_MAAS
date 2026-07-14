import os
import tempfile
import torch
try:
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsArgs, XttsAudioConfig
    from TTS.config.shared_configs import BaseDatasetConfig
    torch.serialization.add_safe_globals([XttsConfig, XttsArgs, XttsAudioConfig, BaseDatasetConfig])
except ImportError:
    pass

from TTS.api import TTS

class JarvisVoice:
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2"):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"

        print(f"[Voice] Loading XTTS v2 on {self.device}...")
        self.tts = TTS(model_name).to(self.device)
        self.speaker_name = "Claribel Dervla"

        try:
            if hasattr(self.tts, "speakers") and self.tts.speakers:
                if self.speaker_name not in self.tts.speakers:
                    self.speaker_name = self.tts.speakers[0]
        except:
            pass
        print("[Voice] Ready.")

    def speak(self, text, output_path=None):
        text = text.replace("*", "").replace("#", "").replace("[TOOL:", "").replace("]", "")
        text = text.strip()
        if not text:
            return

        try:
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix=".wav", dir="/tmp")
                os.close(fd)

            self.tts.tts_to_file(
                text=text[:2000],
                speaker=self.speaker_name,
                language="en",
                file_path=output_path,
            )

            if os.name == 'posix':
                os.system(f"afplay '{output_path}' &")

            try:
                os.unlink(output_path)
            except:
                pass
        except Exception as e:
            print(f"[Voice] TTS error: {e}")


if __name__ == "__main__":
    voice = JarvisVoice()
    voice.speak("Hello. I am online. How can I help you, sir?")

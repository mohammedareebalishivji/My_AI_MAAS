import speech_recognition as sr
import pyaudio

def list_microphones():
    print("Available Microphones:")
    mic_list = sr.Microphone.list_microphone_names()
    for index, name in enumerate(mic_list):
        print(f"Index {index}: {name}")

def test_microphone():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\nDefault microphone found.")
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
            print("Say something (you have 5 seconds)...")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=5)
                print("Audio captured successfully!")
            except sr.WaitTimeoutError:
                print("Listening timed out. No speech detected.")
            except Exception as e:
                print(f"Error during listening: {e}")
    except Exception as e:
        print(f"Could not open microphone: {e}")

if __name__ == "__main__":
    list_microphones()
    test_microphone()

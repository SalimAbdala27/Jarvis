import pyaudio
import numpy as np
import wave
from openwakeword.model import Model
from faster_whisper import WhisperModel

CHUNK = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def record_audio(filename="temp_recording.wav", seconds=5):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
    print("Recording...")
    frames = []
    for _ in range(int(RATE / 1024 * seconds)):
        frames.append(stream.read(1024))
    print("Finished recording.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return filename

def transcribe_audio(filename, whisper_model):
    segments, info = whisper_model.transcribe(filename)
    text = " ".join(segment.text for segment in segments)
    print(f"You said: {text}")
    return text

def main():
    wake_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    whisper_model = WhisperModel("tiny", device="cpu")

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)

    print("Listening for 'Hey Jarvis'...")

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            prediction = wake_model.predict(audio)
            score = prediction["hey_jarvis"]
            if score > 0.5:
                print("Wake word detected!")
                stream.stop_stream()
                wav_file = record_audio()
                transcribe_audio(wav_file, whisper_model)
                stream.start_stream()
                print("Listening for 'Hey Jarvis'...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    main()

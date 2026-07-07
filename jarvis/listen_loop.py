import pyaudio
import numpy as np
import wave
import subprocess
import requests
from openwakeword.model import Model
from faster_whisper import WhisperModel

CHUNK = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
JARVIS_URL = "http://127.0.0.1:8765/api/chat"
EXIT_PHRASES = ("stop", "goodbye jarvis", "that's all", "shut down")

def record_audio(filename="temp_recording.wav", silence_threshold=500, silence_duration=1.5, max_seconds=15):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=1024)
    print("Recording... (speak now, pause when done)")
    frames = []
    silent_chunks = 0
    chunks_per_second = RATE / 1024
    silence_chunk_limit = int(chunks_per_second * silence_duration)
    max_chunks = int(chunks_per_second * max_seconds)

    for _ in range(max_chunks):
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(data)
        audio_chunk = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(audio_chunk).mean()

        if volume < silence_threshold:
            silent_chunks += 1
            if silent_chunks > silence_chunk_limit and len(frames) > silence_chunk_limit:
                break
        else:
            silent_chunks = 0

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
    text = " ".join(segment.text for segment in segments).strip()
    print(f"You said: {text}")
    return text

def ask_jarvis(message):
    try:
        response = requests.post(
            JARVIS_URL,
            headers={"content-type": "application/json"},
            json={"message": message, "session_id": "voice-loop"},
            timeout=90
        )
        response.raise_for_status()
        return response.json().get("answer", "I didn't get a response.")
    except Exception as e:
        return f"Sorry, I couldn't reach my brain: {e}"

def speak(text):
    subprocess.run(['say', text])

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
                text = transcribe_audio(wav_file, whisper_model)

                if text.lower().strip() in EXIT_PHRASES:
                    speak("Goodbye!")
                    print("Exit phrase detected. Shutting down.")
                    break

                if text:
                    reply = ask_jarvis(text)
                    print(f"Jarvis: {reply}")
                    speak(reply)

                stream.start_stream()
                print("Listening for 'Hey Jarvis'...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    main()

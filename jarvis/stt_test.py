import pyaudio
import wave
from faster_whisper import WhisperModel

def record_audio(filename="temp_recording.wav"):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 5

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)

    print("Recording...")
    frames = []
    for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
        frames.append(stream.read(CHUNK))
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

def transcribe_audio(filename):
    model = WhisperModel("tiny", device="cpu")
    segments, info = model.transcribe(filename)
    for segment in segments:
        print(segment.text)

if __name__ == '__main__':
    wav_file = record_audio()
    transcribe_audio(wav_file)

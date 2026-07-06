import pyaudio
import numpy as np
from openwakeword.model import Model

CHUNK = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def main():
    model = Model(wakeword_models=["hey_jarvis"])

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)

    print("Listening for 'Hey Jarvis'...")

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            prediction = model.predict(audio)
            score = prediction["hey_jarvis"]
            if score > 0.5:
                print("Wake word detected!")
                break
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    main()

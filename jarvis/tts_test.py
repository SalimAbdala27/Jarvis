import subprocess

def speak(text):
    subprocess.run(['say', text])

if __name__ == '__main__':
    speak("Hello, I am Jarvis")

import os
import pygame
import sounddevice as sd
from scipy.io.wavfile import write
import speech_recognition as sr
from gtts import gTTS
from groq import Groq
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load API Key
# ---------------------------------------------------------
load_dotenv("new.env")
groq_api = os.getenv("GROQ_API_KEY")

if not groq_api:
    raise ValueError("❌ GROQ_API_KEY not found in new.env")

client = Groq(api_key=groq_api)
secret_word = "apple"


# ---------------------------------------------------------
# Text-To-Speech using gTTS + pygame
# ---------------------------------------------------------
def speak(text):
    print("🤖 Speaking:", text)

    tts = gTTS(text=text, lang="en")
    filename = "voice_output.mp3"
    tts.save(filename)

    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        continue

    pygame.mixer.quit()
    os.remove(filename)


# ---------------------------------------------------------
# Record audio (No missing file errors)
# ---------------------------------------------------------
def record_audio(path="audio/input.wav", duration=4, fs=16000):
    print("🎙️ Recording... Speak now!")
    os.makedirs("audio", exist_ok=True)

    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()

    write(path, fs, audio)  # Save WAV
    print("✔️ Saved:", path)


# ---------------------------------------------------------
# Whisper ASR (Groq)
# ---------------------------------------------------------
def transcribe_audio(path="audio/input.wav"):
    print("🎧 Transcribing...")

    with open(path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=(path, f),
            model="whisper-large-v3"
        )

    text = result.text.lower()
    print("👦 Child said:", text)
    return text


# ---------------------------------------------------------
# LLM Response (Groq)
# ---------------------------------------------------------
def think(user_text):
    prompt = f"""
You are Coco, a fun and friendly kids' game assistant.
The secret word is "{secret_word}".
The child said: "{user_text}"

Rules:
- If they guess correctly, celebrate! and set a new secret word but do not reveal it until they guess it.
- If close, give cute hints.
- If wrong, encourage them.
- Keep answers short (1–2 sentences).
- Never reveal the secret word directly.
- If they say "I give up" or "tell the secret word". Reveal the secret word.

"""

    chat = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return chat.choices[0].message.content


# ---------------------------------------------------------
# Main Game Loop
# ---------------------------------------------------------
speak("Hi! Let's play guess the word! Say your first guess!")

while True:
    try:
        # Record 4 seconds
        record_audio()

        # Convert speech to text
        text = transcribe_audio()

        # Exit if child says bye
        if "stop" in text or "bye" in text:
            speak("Okay, bye bye! That was fun!")
            break

        # LLM response
        reply = think(text)
        print("🤖 Agent:", reply)

        # Speak reply
        speak(reply)

    except Exception as e:
        print("❌ Error:", e)
        speak("Oops! I didn't catch that. Let's try again.")

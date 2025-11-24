import csv
import os
import time
from gtts import gTTS
import google.generativeai as genai

# Gemini API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-1.5-flash"

CSV_PATH = r"C:\Users\Hp\OneDrive\Desktop\extras\mail.csv"
OUTPUT_FOLDER = "audio_output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# --------------------------
# Functions
# --------------------------

def generate_template_with_gemini(name, email):
    """
    Ask Gemini to craft a natural, warm, professional voice message.
    """
    prompt = f"""
    Create a short, friendly, natural-sounding greeting for a voice message.
    The message must start with:

    "Hi {name}, Thank you for registering with us with the {email}."

    After that, add 1–2 additional polite sentences encouraging them 
    about the next steps or welcoming them warmly. 
    Keep the tone conversational and suitable for audio.
    """

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)

    return response.text.strip()


def sanitize_filename(email):
    bad_chars = ['@', '.', ' ', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    safe = email
    for ch in bad_chars:
        safe = safe.replace(ch, "_")
    return safe


def generate_audio(text, email):
    """Convert Gemini-generated text to speech."""
    tts = gTTS(text=text, lang="en")

    safe_email = sanitize_filename(email)
    filename = f"{safe_email}.mp3"
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    tts.save(filepath)
    return filepath


# --------------------------
# Main logic
# --------------------------

def main():
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
        return

    with open(CSV_PATH, encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    total = len(rows)
    completed = 0

    for row in rows:
        name = row.get("Name", "").strip()
        email = row.get("Email", "").strip()

        if not name or not email:
            print("Skipping row with missing values:", row)
            continue

        completed += 1
        print(f"\n[{completed}/{total}] Processing {email}...")

        # Step 1 — Generate message text with Gemini
        try:
            message_text = generate_template_with_gemini(name, email)
            print("Generated text:", message_text)
        except Exception as e:
            print("Gemini API error:", e)
            continue

        # Step 2 — Convert to audio
        try:
            path = generate_audio(message_text, email)
            print("Saved MP3:", path)
        except Exception as e:
            print("TTS error:", e)

        time.sleep(1)  # Reduce API pressure


if __name__ == "__main__":
    main()

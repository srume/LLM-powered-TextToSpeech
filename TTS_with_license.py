import csv
import os
import time
import json
from gtts import gTTS
import google.generativeai as genai
import uuid
import hashlib
from datetime import datetime
import sys

# -------------------------
# LICENSE CONFIG
# -------------------------
LICENSE_FILE = "license.key"

def normalize_mac(mac):
    """Remove colons/dashes and lowercase the MAC"""
    return mac.replace(":", "").replace("-", "").lower()

def get_mac():
    """Get current machine MAC in normalized format"""
    raw_mac = str(hex(uuid.getnode()))[2:]  # e.g., aabbccddeeff
    return raw_mac.lower()

def validate_license():
    if not os.path.exists(LICENSE_FILE):
        print("❌ license.key missing.")
        return False

    try:
        with open(LICENSE_FILE, "r") as f:
            mac_saved = f.readline().strip()
            valid_from = f.readline().strip()
            valid_until = f.readline().strip()
            stored_signature = f.readline().strip()
    except:
        print("❌ Invalid license.key format.")
        return False

    # Normalize stored MAC
    mac_saved_norm = normalize_mac(mac_saved)

    # MAC check
    mac_current = get_mac()
    if mac_current != mac_saved_norm:
        print("❌ License is for another PC.")
        return False

    # Date check
    today = datetime.now().date()
    try:
        valid_from_date = datetime.strptime(valid_from, "%Y-%m-%d").date()
        valid_until_date = datetime.strptime(valid_until, "%Y-%m-%d").date()
    except:
        print("❌ Invalid date format in license.")
        return False

    if today < valid_from_date:
        print("❌ License not active yet. Valid from:", valid_from)
        return False
    if today > valid_until_date:
        print("❌ License expired on:", valid_until)
        return False

    # Signature check
    raw_data = mac_saved_norm + "|" + valid_from + "|" + valid_until
    expected_signature = hashlib.sha256(raw_data.encode()).hexdigest()
    if stored_signature != expected_signature:
        print("❌ License has been tampered with.")
        return False

    print("✔ License valid. Valid from:", valid_from, "to:", valid_until)
    return True

# -------------------------
# EXIT WITH CONTACT MESSAGE
# -------------------------
if not validate_license():
    print("\nThere is a problem with your license. Please contact: flyingstockstechnologies.com")
    print("The program will exit in 20 seconds...")
    time.sleep(20)
    sys.exit()

# ----------------------------------
# Load config file
# ----------------------------------
CONFIG_PATH = "config.json"

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError("config.json missing!")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

USE_AI_TEMPLATE = config.get("use_ai_template", False)
GEMINI_API_KEY = config.get("gemini_api_key", "").strip()
MANUAL_MESSAGE = config.get("manual_message", "").strip()
CSV_PATH = config.get("csv_path", "").strip()

if not CSV_PATH:
    raise ValueError("csv_path missing in config.json!")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

OUTPUT_FOLDER = "audio_output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

GENERATED_TEXT_FOLDER = "generated_messages"
os.makedirs(GENERATED_TEXT_FOLDER, exist_ok=True)


# ----------------------------------
# FUNCTIONS
# ----------------------------------
def generate_ai_text(name, email, topic):
    prompt = f"""
    Create a SHORT voice message under 15 seconds.
    Include the name: {name}
    Topic: {topic}

    Output ONLY the message text, no formatting.
    """

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    message = response.text.strip()

    safe = email.replace("@", "_").replace(".", "_")
    filepath = os.path.join(GENERATED_TEXT_FOLDER, f"{safe}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(message)

    print(f"\nAI message saved to: {filepath}")
    print("Copy this message into config.json → manual_message")
    return message


def generate_manual_text(name, email):
    return MANUAL_MESSAGE.format(name=name, email=email)


def sanitize_filename(email):
    bad = ['@', '.', ' ', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    safe = email
    for c in bad:
        safe = safe.replace(c, "_")
    return safe


def generate_audio(text, email):
    tts = gTTS(text=text, lang="en")
    filename = f"{sanitize_filename(email)}.mp3"
    path = os.path.join(OUTPUT_FOLDER, filename)
    tts.save(path)
    return path


# ----------------------------------
# MAIN
# ----------------------------------
def main():
    choice = input("Generate message using AI or Human written? (AI/Human): ").strip().lower()
    use_ai_now = (choice == "ai")

    topic = ""
    if use_ai_now:
        topic = input("Enter the topic for the short audio message: ").strip()
        if not topic:
            print("Topic missing. Exiting.")
            return

    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        return

    with open(CSV_PATH, encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    total = len(rows)
    done = 0

    for row in rows:
        name = row.get("Name", "").strip()
        email = row.get("Email", "").strip()

        if not name or not email:
            print("Skipping incomplete row:", row)
            continue

        done += 1
        print(f"\n[{done}/{total}] Processing {email}...")

        try:
            if use_ai_now:
                message = generate_ai_text(name, email, topic)
            else:
                message = generate_manual_text(name, email)
        except Exception as e:
            print("Message creation error:", e)
            continue

        print("Message:", message)

        try:
            audio_path = generate_audio(message, email)
            print("Audio saved:", audio_path)
        except Exception as e:
            print("TTS Error:", e)

        time.sleep(1)


if __name__ == "__main__":
    main()

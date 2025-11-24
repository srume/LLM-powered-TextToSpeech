import os
import sys
import json
import uuid
import hashlib
import datetime
import re
import yaml
import webbrowser
import time
from elevenlabs import ElevenLabs


# ============================================================
# Retrieve MAC Address
# ============================================================
def get_mac_address():
    mac_value = uuid.getnode()
    return ':'.join(['{:02X}'.format((mac_value >> i) & 0xff) for i in range(0, 48, 8)][::-1])


# ============================================================
# Validate License File
# ============================================================
def validate_license(license_file_path):
    if not os.path.exists(license_file_path):
        raise ValueError("❌ license.key not found. Please place it next to the .exe.")

    try:
        with open(license_file_path, "r") as file:
            license_data = json.load(file)
    except Exception:
        raise ValueError("❌ license.key is corrupted or unreadable.")

    required_fields = ["mac", "start_date", "end_date", "signature"]
    for required_field in required_fields:
        if required_field not in license_data:
            raise ValueError(f"❌ Missing '{required_field}' in license.key.")

    licensed_mac = license_data["mac"]
    license_start = license_data["start_date"]
    license_end = license_data["end_date"]
    stored_signature = license_data["signature"]

    system_mac = get_mac_address()

    if system_mac != licensed_mac:
        raise ValueError(
            "❌ LICENSE INVALID FOR THIS MACHINE.\n"
            f"Licensed MAC: {licensed_mac}\n"
            f"Device MAC:   {system_mac}"
        )

    today = datetime.date.today()

    try:
        start_date_obj = datetime.date.fromisoformat(license_start)
        end_date_obj = datetime.date.fromisoformat(license_end)
    except ValueError:
        raise ValueError("❌ Invalid date format in license.key. Use YYYY-MM-DD.")

    if not (start_date_obj <= today <= end_date_obj):
        raise ValueError(
            "❌ LICENSE EXPIRED OR NOT ACTIVE.\n"
            f"Valid From: {license_start} | Valid Until: {license_end}"
        )

    signature_source = f"{licensed_mac}{license_start}{license_end}"
    computed_signature = hashlib.sha256(signature_source.encode()).hexdigest()

    if stored_signature != computed_signature:
        raise ValueError("❌ License signature mismatch — file may be tampered.")

    return True


# ============================================================
# Load YAML Configuration File
# ============================================================
def load_configuration(config_file_path):
    if not os.path.exists(config_file_path):
        raise ValueError("❌ config_text_to_speech.yaml not found.")

    try:
        with open(config_file_path, "r") as file:
            return yaml.safe_load(file)
    except Exception:
        raise ValueError("❌ Failed to read config_text_to_speech.yaml — file is corrupted.")


# ============================================================
# MAIN PROGRAM
# ============================================================
def main():

    # Determine root directory of .exe or .py
    if getattr(sys, "frozen", False):
        app_root_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        app_root_path = os.path.dirname(os.path.abspath(__file__))

    config_path = os.path.join(app_root_path, "config_text_to_speech.yaml")
    license_path = os.path.join(app_root_path, "license.key")

    # License validation
    validate_license(license_path)

    # Load configuration
    config_data = load_configuration(config_path)

    api_key = config_data.get("eleven_api_key")
    voice_id = config_data.get("voice_id")
    model_id = config_data.get("model_id")
    input_text = config_data.get("text")

    if not api_key or not voice_id or not model_id or not input_text:
        raise ValueError("❌ Missing required fields in config_text_to_speech.yaml.")

    # Determine filename from email in text
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", input_text)
    if email_match:
        email = email_match.group(0)
        filename_safe = re.sub(r"[^A-Za-z0-9_]", "_", email)
    else:
        filename_safe = "output_audio"

    output_filename = f"{filename_safe}.mp3"
    output_file_path = os.path.join(app_root_path, output_filename)

    # Initialize ElevenLabs Client
    eleven_client = ElevenLabs(api_key=api_key)

    print("🔊 Generating audio... Please wait...")

    # The NEW ElevenLabs SDK returns a generator automatically for convert()
    audio_stream = eleven_client.text_to_speech.convert(
        text=input_text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128"
    )

    # Combine streamed chunks
    audio_bytes = b"".join(chunk for chunk in audio_stream)

    # Save to file
    with open(output_file_path, "wb") as outfile:
        outfile.write(audio_bytes)

    print(f"✅ Audio saved at: {output_file_path}")

    try:
        webbrowser.open(output_file_path)
    except:
        pass

    print("🎉 Done!")


# ============================================================
# GLOBAL ERROR HANDLER (20-second delay)
# ============================================================
if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print()
        print(error)
        print("\nFor support, please contact flyingstockstechnologies.com")
        print("Program will exit in 20 seconds...")
        time.sleep(20)
        sys.exit(1)

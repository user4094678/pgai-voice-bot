"""
Download Twilio call recordings as .mp3 files into calls/audio/.

Usage:
    python3 src/download_recording.py <call_sid> <persona_name>

Run this a few seconds after a call ends — Twilio needs a short moment
to finish processing the recording before it's downloadable.

Or run with no arguments to download recordings for ALL calls made
today that don't already have a saved audio file.
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

AUDIO_DIR = Path(__file__).resolve().parent.parent / "calls" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(ACCOUNT_SID, AUTH_TOKEN)


def download_recording_for_call(call_sid, label=None):
    recordings = client.recordings.list(call_sid=call_sid)

    if not recordings:
        print(f"⚠️  No recording found yet for {call_sid} — try again in a few seconds.")
        return False

    recording = recordings[0]
    filename = f"{label or 'call'}_{call_sid}.mp3"
    filepath = AUDIO_DIR / filename

    media_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
    response = requests.get(media_url, auth=(ACCOUNT_SID, AUTH_TOKEN))

    if response.status_code == 200:
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"✅ Saved: {filepath}")
        return True
    else:
        print(f"❌ Failed to download {call_sid}: HTTP {response.status_code}")
        return False


def download_all_recent(limit=30):
    """Download recordings for all recent calls that don't already
    have a saved audio file."""
    calls = client.calls.list(limit=limit)
    for call in calls:
        already_saved = any(AUDIO_DIR.glob(f"*_{call.sid}.mp3"))
        if already_saved:
            continue
        print(f"Downloading recording for call {call.sid}...")
        download_recording_for_call(call.sid)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        call_sid = sys.argv[1]
        label = sys.argv[2] if len(sys.argv) > 2 else None
        download_recording_for_call(call_sid, label)
    else:
        print("No call SID given — downloading all recent recordings not yet saved...")
        download_all_recent()
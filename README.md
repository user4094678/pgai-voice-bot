# Pretty Good AI — Voice Bot Challenge

An automated voice bot that calls Pretty Good AI's test line, acts as a
simulated patient, and evaluates the quality of their AI agent's
responses — finding bugs, evaluating quality, and stress-testing edge
cases.

## Setup

1. Clone this repo and `cd` into it
2. Create a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your real API keys (Twilio,
   Deepgram, ElevenLabs, Groq):
   ```
   cp .env.example .env
   ```
5. In one terminal, start the server:
   ```
   uvicorn src.server:app --reload --port 8000
   ```
6. In a second terminal, expose it publicly with ngrok, and put the
   printed URL into `PUBLIC_BASE_URL` in your `.env`:
   ```
   ngrok http 8000
   ```
7. In a third terminal, place a call (choose any persona from `src/personas.py`):
   ```
   python3 src/test_call_v2.py scheduling
   ```
8. After the call ends, download its recording:
   ```
   python3 src/download_recording.py <call_sid> <persona_name>
   ```

Transcripts save automatically to `calls/transcripts/` as each call ends.

## Project structure

```
├── src/
│   ├── server.py              # FastAPI server: Twilio webhook + media stream handler
│   ├── personas.py            # patient persona definitions + voice mappings
│   ├── test_call_v2.py        # places an outbound call with a chosen persona
│   └── download_recording.py  # downloads a call's recording from Twilio as mp3
├── calls/
│   ├── audio/                 # recorded call audio (.mp3)
│   └── transcripts/           # call transcripts (.txt)
├── BUGS.md                    # bug report from testing
├── .env.example                # template for required environment variables
└── requirements.txt
```

## Architecture

The bot uses a real-time STT → LLM → TTS pipeline. Twilio opens a live
WebSocket media stream when a call connects, sending the agent's audio
in small chunks; those chunks are forwarded to Deepgram for streaming
transcription. Rather than reacting to every transcribed fragment
(which caused the bot to interrupt mid-sentence early on), the bot
buffers fragments and only responds once Deepgram's `UtteranceEnd` event
signals the agent has actually finished their turn — this, combined with
a lock that ignores new triggers while a response is still being
generated, was the fix for two real bugs found during development
(premature interruptions and overlapping audio). The buffered
transcript is sent to Groq (Llama 3.3 70B), chosen specifically for its
low-latency inference, since natural turn-taking pacing was a graded
priority; the LLM response — generated from a persona-specific system
prompt rather than a fixed script, so the "patient" improvises
realistically instead of running a scripted benchmark — is converted to
speech via ElevenLabs (using `ulaw_8000` output so no audio conversion
is needed) and streamed back into the live call.

## Bug report

See [`BUGS.md`](./BUGS.md) for detailed findings, including a critical
patient-privacy/identity-verification issue, a data-integrity issue
around false appointment claims, and content that leaks from a
different channel (a QR code reference during a voice call).

## Environment variables

See `.env.example` for the full list of required variables — you'll need
API keys for Twilio, Deepgram, ElevenLabs, and Groq.

## What I'd improve with more time

- Reduce the ~1-2 second response gap by streaming the LLM's response
  token-by-token into TTS instead of waiting for the full reply
  (Deepgram's `utterance_end_ms` has a 1000ms platform minimum, so most
  of the remaining latency is generation time, not detection time)
- Queue rather than drop an utterance that arrives while the bot is
  still speaking, instead of ignoring it outright
- Add automated regression checks for the bugs found (e.g., a call that
  always checks whether insurance/hours questions get real answers)
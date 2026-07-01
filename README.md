# Pretty Good AI — Voice Bot Challenge

An automated voice bot that calls Pretty Good AI's test line, acts as a
simulated patient, and evaluates the quality of their AI agent's responses.

## Setup

1. Clone this repo and `cd` into it
2. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your real API keys:
   ```
   cp .env.example .env
   ```
5. Run the bot:
   ```
   python src/main.py
   ```

## Project structure

```
├── src/                  # bot source code
├── calls/
│   ├── audio/            # recorded call audio (.mp3 / .ogg)
│   └── transcripts/      # call transcripts (.txt)
├── .env.example          # template for required environment variables
└── requirements.txt
```

## Architecture

_(fill in once built: 1-2 paragraphs on how the STT → LLM → TTS pipeline
works and why you made the design choices you did)_

## Bug report

See `BUGS.md` _(create this once you've run your test calls)_

## Environment variables

See `.env.example` for the full list of required variables — you'll need
API keys for Twilio, Deepgram, ElevenLabs, and an LLM provider (Anthropic).

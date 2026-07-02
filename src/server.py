import os
import json
import base64
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import PlainTextResponse
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = FastAPI()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").replace("https://", "").replace("http://", "")
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# The "patient" persona — this is what makes your bot act like a caller
# instead of just an empty chatbot. We'll build out more personas in Phase 3.
SYSTEM_PROMPT = """You are Sally Smith, a patient calling a medical clinic's
automated phone system to book an appointment. You have a mild sore throat
and want to be seen sometime this week, ideally in the afternoon.

Speak like a real person on the phone: contractions, short sentences, no
over-explaining. Don't break character or mention you're an AI. Stay focused
on your goal but respond naturally to whatever the agent says. If the agent
makes an error, react like a real patient would. Keep responses SHORT —
one or two sentences max, like real spoken conversation."""


@app.post("/voice")
async def voice(request: Request):
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{PUBLIC_BASE_URL}/media-stream" />
    </Connect>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


async def generate_reply(conversation_history):
    """Ask Groq (Llama) what the patient should say next."""
    response = groq_client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=conversation_history,
        max_tokens=100,
        temperature=0.8,
    )
    return response.choices[0].message.content


async def text_to_speech(text):
    """Turn the patient's reply into audio, in the exact format Twilio
    expects: 8kHz mono mulaw."""
    audio_generator = elevenlabs_client.text_to_speech.convert(
        voice_id=VOICE_ID,
        model_id="eleven_flash_v2_5",  # low-latency model, matters for real-time
        text=text,
        output_format="ulaw_8000",
    )
    audio_bytes = b"".join(audio_generator)
    return audio_bytes


async def send_audio_to_twilio(websocket, stream_sid, audio_bytes):
    """Send audio back into the live call, chunked the way Twilio expects."""
    payload = base64.b64encode(audio_bytes).decode("utf-8")
    media_message = {
        "event": "media",
        "streamSid": stream_sid,
        "media": {"payload": payload},
    }
    await websocket.send_json(media_message)


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("✅ Twilio connected to media stream")

    loop = asyncio.get_event_loop()
    stream_sid = None
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    dg_connection = deepgram.listen.websocket.v("1")

    def on_transcript(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        if len(transcript) == 0 or not result.is_final:
            return

        print(f"🗣️  Agent said: {transcript}")
        conversation_history.append({"role": "user", "content": transcript})

        # Schedule our response — this runs the think+speak steps without
        # blocking the audio-receiving loop above
        asyncio.run_coroutine_threadsafe(
            respond(websocket, stream_sid, conversation_history), loop
        )

    def on_error(self, error, **kwargs):
        print("❌ Deepgram error:", error)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    dg_options = LiveOptions(
        model="nova-2",
        language="en-US",
        encoding="mulaw",
        sample_rate=8000,
        channels=1,
        interim_results=True,
        endpointing=750,
    )

    if not dg_connection.start(dg_options):
        print("❌ Failed to start Deepgram connection")
        return

    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("event")

            if event == "start":
                stream_sid = message["start"]["streamSid"]
                print("📞 Call started:", message["start"]["callSid"])

            elif event == "media":
                payload = message["media"]["payload"]
                audio_bytes = base64.b64decode(payload)
                dg_connection.send(audio_bytes)

            elif event == "stop":
                print("📴 Call ended")
                break

    except Exception as e:
        print("Connection closed:", e)
    finally:
        dg_connection.finish()


async def respond(websocket, stream_sid, conversation_history):
    """The 'think + speak' half of the loop: ask Groq for a reply, turn
    it into audio, send it back into the call."""
    try:
        reply_text = await generate_reply(conversation_history)
        print(f"🤖 Patient says: {reply_text}")
        conversation_history.append({"role": "assistant", "content": reply_text})

        audio_bytes = await text_to_speech(reply_text)
        await send_audio_to_twilio(websocket, stream_sid, audio_bytes)

    except Exception as e:
        print("❌ Error in respond():", e)


@app.get("/")
async def health():
    return {"status": "running"}
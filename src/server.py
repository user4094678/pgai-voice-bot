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
from .personas import get_persona_prompt, get_voice_id, DEFAULT_PERSONA

load_dotenv()

app = FastAPI()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").replace("https://", "").replace("http://", "")
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")


@app.post("/voice")
async def voice(request: Request):
    persona = request.query_params.get("persona", DEFAULT_PERSONA)
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{PUBLIC_BASE_URL}/media-stream">
            <Parameter name="persona" value="{persona}" />
        </Stream>
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


async def text_to_speech(text, voice_id):
    """Turn the patient's reply into audio, in the exact format Twilio
    expects: 8kHz mono mulaw."""
    audio_generator = elevenlabs_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id="eleven_flash_v2_5",
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
    conversation_history = []
    voice_id_for_call = VOICE_ID

    dg_connection = deepgram.listen.websocket.v("1")

    utterance_buffer = []
    is_responding = {"value": False}  # dict so the nested functions can mutate it

    def on_transcript(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        if len(transcript) == 0 or not result.is_final:
            return
        print(f"   …chunk: {transcript}")
        utterance_buffer.append(transcript)

    def on_utterance_end(self, utterance_end, **kwargs):
        if not utterance_buffer:
            return

        if is_responding["value"]:
            # Our bot is still generating or speaking from the LAST turn —
            # ignore this trigger instead of starting a second response
            # that would collide with the one already playing.
            print("⏸️  Ignoring new utterance — still responding to the last one")
            utterance_buffer.clear()
            return

        full_utterance = " ".join(utterance_buffer)
        utterance_buffer.clear()

        print(f"🗣️  Agent said: {full_utterance}")
        conversation_history.append({"role": "user", "content": full_utterance})

        asyncio.run_coroutine_threadsafe(
            respond(websocket, stream_sid, conversation_history, voice_id_for_call, is_responding), loop
        )

    def on_error(self, error, **kwargs):
        print("❌ Deepgram error:", error)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    dg_options = LiveOptions(
        model="nova-2",
        language="en-US",
        encoding="mulaw",
        sample_rate=8000,
        channels=1,
        interim_results=True,
        endpointing=750,
        utterance_end_ms="1000",
        vad_events=True,
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
                custom_params = message["start"].get("customParameters", {})
                persona_key = custom_params.get("persona", DEFAULT_PERSONA)
                system_prompt = get_persona_prompt(persona_key)
                voice_id_for_call = get_voice_id(persona_key, VOICE_ID)
                conversation_history.append({"role": "system", "content": system_prompt})
                print(f"🎭 Persona: {persona_key}  |  🔊 Voice: {voice_id_for_call}")
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


async def respond(websocket, stream_sid, conversation_history, voice_id, is_responding):
    """The 'think + speak' half of the loop: ask Groq for a reply, turn
    it into audio, send it back into the call."""
    is_responding["value"] = True
    try:
        reply_text = await generate_reply(conversation_history)
        print(f"🤖 Patient says: {reply_text}")
        conversation_history.append({"role": "assistant", "content": reply_text})

        audio_bytes = await text_to_speech(reply_text, voice_id)
        await send_audio_to_twilio(websocket, stream_sid, audio_bytes)

    except Exception as e:
        print("❌ Error in respond():", e)
    finally:
        is_responding["value"] = False


@app.get("/")
async def health():
    return {"status": "running"}
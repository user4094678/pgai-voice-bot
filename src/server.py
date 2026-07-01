import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import PlainTextResponse

load_dotenv()

app = FastAPI()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").replace("https://", "").replace("http://", "")

@app.post("/voice")
async def voice(request: Request):
    """Twilio hits this when the call connects. We tell it to open a
    live audio stream to our WebSocket endpoint instead of just playing
    a canned message."""
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{PUBLIC_BASE_URL}/media-stream" />
    </Connect>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """This is where the live, two-way audio will flow. For now we just
    prove the connection works by logging what Twilio sends us."""
    await websocket.accept()
    print("✅ Twilio connected to media stream")

    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("event")

            if event == "start":
                print("📞 Call started:", message["start"]["callSid"])
            elif event == "media":
                pass  # audio chunks will arrive here — we'll process these next
            elif event == "stop":
                print("📴 Call ended")
                break
    except Exception as e:
        print("Connection closed:", e)


@app.get("/")
async def health():
    return {"status": "running"}
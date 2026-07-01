import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

call = client.calls.create(
    to=os.getenv("PGAI_TEST_NUMBER"),
    from_=os.getenv("TWILIO_PHONE_NUMBER"),
    twiml="<Response><Say>This is a test call from my voice bot project.</Say><Pause length='3'/></Response>",
    record=True,
)

print(f"Call started: {call.sid}")
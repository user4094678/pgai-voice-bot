import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# Pick a persona from the command line, e.g.:
#   python3 src/test_call_v2.py reschedule
# Defaults to "scheduling" if you don't pass one.
persona = sys.argv[1] if len(sys.argv) > 1 else "scheduling"

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

call = client.calls.create(
    to=os.getenv("PGAI_TEST_NUMBER"),
    from_=os.getenv("TWILIO_PHONE_NUMBER"),
    url=f"{os.getenv('PUBLIC_BASE_URL')}/voice?persona={persona}",
    record=True,
)

print(f"Call started: {call.sid}  (persona: {persona})")
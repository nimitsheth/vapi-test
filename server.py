from fastapi import FastAPI, Request
import logging
from supabase import create_client, Client
from cuid import cuid
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from twilio.rest import Client as TwilioClient
import os

# ------------------------------
# App setup
# ------------------------------
app = FastAPI()

# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ------------------------------
# Supabase configuration
# ------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------
# OSM Geocoder
# ------------------------------
geolocator = Nominatim(user_agent="emergency_webhook")

def get_lat_lon(location: str):
    try:
        geo = geolocator.geocode(location, timeout=10)
        if geo:
            return geo.latitude, geo.longitude
        else:
            return None, None
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None, None

# ------------------------------
# Twilio SMS setup
# ------------------------------
twilio_client = TwilioClient(os.getenv("TWILIO_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
twilio_from = os.getenv("TWILIO_PHONE_NUMBER")

def send_sms(to_number: str, message: str):
    try:
        twilio_client.messages.create(
            body=message,
            from_=twilio_from,
            to=to_number
        )
        logging.info(f"✅ SMS sent to {to_number}")
    except Exception as e:
        logging.error(f"❌ Failed to send SMS to {to_number}: {e}")

# ------------------------------
# Store last webhook for debug
# ------------------------------
last_webhook_data = None

# ------------------------------
# Webhook endpoint
# ------------------------------
@app.post("/webhook")
async def handle_webhook(data: dict):
    global last_webhook_data
    last_webhook_data = data

    event_type = data.get("message", {}).get("type")

    if event_type == "end-of-call-report":
        logging.info(f"[Call Ended] Full payload received")

        # Extract structured data
        structured = data.get("message", {}).get("analysis", {}).get("structuredData", {})

        emergency_type = structured.get("emergency_type", "Unknown Emergency")
        caller_state = structured.get("caller_state", "")
        additional_notes = structured.get("additional_notes", "")
        location = structured.get("location", "Unknown Location")
        urgency_level = structured.get("urgency_level", "medium")
        caller_number = structured.get("caller_number")  # Make sure this is provided by VAPI

        description = f"{caller_state} {additional_notes}".strip()

        # Get latitude and longitude via OSM
        latitude, longitude = get_lat_lon(location)

        # IST timestamp
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).isoformat()

        # Prepare record
        record = {
            "id": cuid(),
            "title": emergency_type,
            "description": description,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "severity": urgency_level or "medium",
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "created_by": None,
            "assigned_to": None
        }

        # Insert into Supabase
        try:
            response = supabase.table("emergencies").insert(record).execute()
            if response.error is None:
                logging.info(f"✅ Emergency successfully inserted: {response.data}")

                # Send SMS to caller
                if caller_number:
                    sms_message = "Emergency services have been dispatched. Help is on the way."
                    send_sms(caller_number, sms_message)
            else:
                logging.error(f"❌ Failed to insert emergency. Error: {response.error}")
        except Exception as e:
            logging.error(f"🚨 Exception inserting emergency into Supabase: {e}")

        return {"status": "ok", "inserted_record": record}

    else:
        logging.info(f"[Other Event] Received event type: {event_type}")
        return {"status": "ignored"}

# ------------------------------
# GET endpoint for debug / testing
# ------------------------------
@app.get("/webhook")
async def show_last_webhook():
    if last_webhook_data:
        return last_webhook_data
    else:
        return {"message": "No webhook received yet."}

@app.get("/")
async def root():
    return {"status": "Webhook server is live"}

# ------------------------------
# Run server
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

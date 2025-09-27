from fastapi import FastAPI, Request
import logging
from supabase import create_client, Client
from cuid import cuid
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import os

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

        description = f"{caller_state} {additional_notes}".strip()

        # ------------------------------
        # Get latitude and longitude via OSM
        # ------------------------------
        latitude, longitude = get_lat_lon(location)

        # ------------------------------
        # IST timestamp
        # ------------------------------
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).isoformat()

        # ------------------------------
        # Prepare record
        # ------------------------------
        record = {
            "id": cuid(),
            "title": emergency_type,
            "description": description,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "type": emergency_type.lower() if emergency_type else "general",  # map to type field
            "severity": urgency_level or "medium",
            "status": "open",
            "auto_assigned": False,
            "assigned_responder": None,
            "eta_minutes": None,
            "estimated_arrival": None,
            "created_at": now,
            "updated_at": now,
            "created_by": None,
            "assigned_to": None
        }

        # ------------------------------
        # Insert into Supabase
        # ------------------------------
        try:
            response = supabase.table("emergencies").insert(record).execute()
            if response.error is None:
                logging.info(f"✅ Emergency successfully inserted: {response.data}")
            else:
                logging.error(f"❌ Failed to insert emergency. Error: {response.error}")
        except Exception as e:
            logging.error(f"🚨 Exception inserting emergency into Supabase: {e}")

        return {"status": "ok", "inserted_record": record}

    else:
        logging.info(f"[Other Event] Received event type: {event_type}")
        return {"status": "ignored"}

# ------------------------------
# GET endpoint for testing / debug
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

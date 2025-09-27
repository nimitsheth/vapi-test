from fastapi import FastAPI, Request
import logging
from supabase import create_client, Client
from cuid import cuid
from datetime import datetime, timezone

import os

app = FastAPI()

# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ------------------------------
# Supabase configuration
# ------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")      # e.g., "https://xyzcompany.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")      # Your anon or service_role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------
# Store last webhook for debug display
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

        emergency_id = cuid()
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": cuid(),
            "title": emergency_type,
            "description": description,
            "location": location,
            "latitude": None,
            "longitude": None,
            "severity": urgency_level or "medium",
            "status": "open",
            "created_at": now,      # Prisma @map("created_at")
            "updated_at": now,      # Prisma @map("updated_at")
            "created_by": None,
            "assigned_to": None
        }


        # ------------------------------
        # Insert record into Supabase
        # ------------------------------
        try:
            response = supabase.table("emergencies").insert(record).execute()
            if response.status_code in (200, 201):
                logging.info(f"Emergency successfully inserted into Supabase: {record}")
            else:
                logging.error(f"Failed to insert into Supabase. Status: {response.status_code}, {response.data}")
        except Exception as e:
            logging.error(f"Error inserting emergency into Supabase: {e}")

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

# ------------------------------
# Run the server
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

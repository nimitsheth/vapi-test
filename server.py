from fastapi import FastAPI, Request
import logging

# Initialize FastAPI
app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

@app.post("/webhook")
async def handle_webhook(data: dict):
    """
    Handles incoming webhook events from VAPI.
    Logs 'speech-update' and 'call-ended' events.
    """

    event_type = data.get("type")

    if event_type == "speech-update":
        transcript = data.get("transcript")
        logging.info(f"[Speech Update] User said: {transcript}")

    elif event_type == "call-ended":
        duration = data.get("call", {}).get("duration")
        logging.info(f"[Call Ended] Duration: {duration}s")

    else:
        logging.info(f"[Other Event] Received event type: {event_type}")

    # Always respond 200 OK to VAPI
    return {"status": "ok"}


# Optional: health check route
@app.get("/")
async def root():
    return {"status": "Webhook server is live"}

from fastapi import FastAPI
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
    Supports 'end-of-call-report' events.
    """

    event_type = data.get("message", {}).get("type")

    if event_type == "end-of-call-report":
        ended_reason = data["message"].get("endedReason")
        call_duration = data["message"].get("call", {}).get("duration")
        transcript = data["message"].get("artifact", {}).get("transcript")
        messages = data["message"].get("artifact", {}).get("messages", [])

        logging.info(f"[Call Ended] Reason: {ended_reason}, Duration: {call_duration}s")
        logging.info(f"[Transcript] {transcript}")

        # Log each message in the conversation
        for msg in messages:
            role = msg.get("role")
            message_text = msg.get("message")
            logging.info(f"[Message] {role}: {message_text}")

    else:
        logging.info(f"[Other Event] Received event type: {event_type}")

    return {"status": "ok"}


# Optional: health check route
@app.get("/")
async def root():
    return {"status": "Webhook server is live"}

from fastapi import FastAPI, Request
from sentence_transformers import SentenceTransformer
import pandas as pd
import faiss
import numpy as np
import logging

app = FastAPI()

# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ------------------------------
# Load department data & initialize FAISS
# ------------------------------
df = pd.read_csv("departments.csv")
encoder = SentenceTransformer("all-mpnet-base-v2")

# Encode department texts
logging.info("Encoding department descriptions...")
vectors = encoder.encode(df.text, convert_to_numpy=True)
index = faiss.IndexFlatL2(vectors.shape[1])
index.add(vectors)
logging.info("FAISS index created with {} entries.".format(len(df)))

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
        ended_reason = data["message"].get("endedReason")
        summary = data["message"].get("analysis", {}).get("summary", "")
        call_duration = data["message"].get("call", {}).get("duration")

        logging.info(f"[Call Ended] Reason: {ended_reason}, Duration: {call_duration}s")
        logging.info(f"[Summary] {summary}")

        # ------------------------------
        # Classification / Matching
        # ------------------------------
        matches = []
        if summary:
            query_vector = encoder.encode(summary).reshape(1, -1)
            k = 1  # top 2 matching departments
            distances, indices = index.search(query_vector, k=k)

            matches = df.loc[indices[0]].to_dict(orient="records")
            logging.info("[Classification Matches]")
            for match in matches:
                logging.info(f"Department: {match['departmentName']}, Contact: {match['Contact']}")

        return {"status": "ok", "matches": matches}

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

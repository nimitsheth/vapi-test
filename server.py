from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(data: dict):
    event_type = data.get("type")
    
    if event_type == "speech-update":
        print(f"User said: {data.get('transcript')}")
    elif event_type == "call-ended":
        print(f"Call ended. Duration: {data.get('call', {}).get('duration')}s")
        
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)

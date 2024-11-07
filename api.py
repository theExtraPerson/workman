from fastapi import FastAPI, Request
from bot import app as bot_app

app = FastAPI()

# Define the webhook endpoint
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = bot_app.update_queue.put(json_data)
    return {"status": "ok"}

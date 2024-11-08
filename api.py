from fastapi import FastAPI, Request, APIRouter, HTTPException
from bot import app as bot_app
from pydantic import BaseModel

app = FastAPI()
router = APIRouter()

class ServiceCreate(BaseModel):
    service_name = str
    description: str
    price: float

# Define the webhook endpoint
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = bot_app.update_queue.put(json_data)
    return {"status": "ok"}

@router.post("/services/", response_model=ServiceCreate)
async def create_service(service: ServiceCreate):
    try:
        return create_service(
            service.service_name,
            service.description,
            service.price
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
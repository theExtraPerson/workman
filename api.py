from fastapi import FastAPI, Request, APIRouter, HTTPException
from bot import app as bot_app
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()
router = APIRouter()

class ServiceCreate(BaseModel):
    service_name: str
    description: str
    price: float

# Define the webhook endpoint
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = bot_app.update_queue.put(json_data)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Workman, if it's technical, we takin' care"}

@router.post("/services/", response_model=ServiceCreate)
async def create_service(service: ServiceCreate):
    try:
        created_service = create_service(
            service.service_name,
            service.description,
            service.price
        )
        return created_service
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to get all services
@router.get("/services/", response_model=List[ServiceCreate])
async def get_all_services():
    try:
        services = get_all_services()
        return services
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint to get a specific service by ID
@router.get("/services/{service_id}", response_model=ServiceCreate)
async def get_service(service_id: int):
    try:
        service = get_service(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return service
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Helper functions for database operations (implement these according to your DB setup)
def create_service(service_name: str, description: str, price: float) -> ServiceCreate:
    # Implement logic to save the service in the database
    pass

def get_all_services() -> List[ServiceCreate]:
    # Implement logic to retrieve all services from the database
    pass

def get_service(service_id: int) -> Optional[ServiceCreate]:
    # Implement logic to retrieve a single service by its ID
    pass

app.include_router(router)
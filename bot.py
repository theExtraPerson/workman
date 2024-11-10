# Main bot logic and message handling

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os
from database.models import Order, Service
from database.db_setup import init_db, SessionLocal
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from fastapi import FastAPI, Request, APIRouter, HTTPException
from contextlib import asynccontextmanager

from services.service_handler import get_services_by_location

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")


# Initiate FastAPI and telegram bot
app = FastAPI()
bot = Bot(TELEGRAM_BOT_TOKEN) 
bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  

# initialise database
init_db()
db = SessionLocal()

class ServiceCreate(BaseModel):
    service_name: str
    description: str
    price: float
    image_path: str
    location: str

# Bot command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Please use /services to see available services:"
    )

async def list_services_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # user_location = get_user_location(update.effective_user.id)

    services = get_services_by_location(
        city=Service.city,
        country=Service.country
    )
    for service in services:
        keyboard = [[InlineKeyboardButton("Order Now", callback_data=f"order_{service.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(
            photo=open(service.image_path, 'rb'),
            caption=f"{service.name}\n{service.description}\nPrice: ${service.price}",
            reply_markup=reply_markup
        )

async def handle_order_callback(update: Update, context):
    query = update.callback_query
    service_id = int(query.data.split("_")[1])
    user_id = query.from_user.id
    
    # Create a new order
    new_order = Order(
        service_id=service_id,
        user_id=user_id,
        status="pending"
    )

    db.add(new_order)
    db.commit()

    await query.answer("WorkMan is takin' care")
    await query.edit_message_text(
        "wait for a response from the {service_name}."
    )

# async def set_webhook() -> None:
#     await app.set_webhook(url=WEBHOOK_URL + "/api/webhook")

# Register bot handlers
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("services", list_services_command))
bot_app.add_handler(CallbackQueryHandler(handle_order_callback, pattern="^order_."))

# API endpoints
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming updates from Telegram"""
    update = Update.de_json(await request.json(), bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

@app.post("/services/", response_model=ServiceCreate)
async def create_service(service: ServiceCreate):
    """Create new service"""
    try:
        new_service = Service(
            service_name=service.name,
            description=service.description,
            price=service.price,
            image_path=service.image_path,
            location=service.location
        )
        db.add(new_service)
        db.commit()
        db.refresh(new_service)
        return new_service
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/services/", response_model=ServiceCreate)
async def get_services():
    """Get all services"""
    try:
        return db.query(Service).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/services/{service_id}", response_model=ServiceCreate)
async def get_service(service_id: int):
    """Get a specific service by ID"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Set webhook on startup"""
    await bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("webhook has been set")

    yield

    """Close database connection on shutdown"""
    db.close()

app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
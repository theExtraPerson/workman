# Main bot logic and message handling

from telegram import (
   InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot,
   ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
   )
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
    )
import os
from database.models import Order, Service
from database.db_setup import init_db, SessionLocal
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from fastapi import FastAPI, Request, APIRouter, HTTPException
from contextlib import asynccontextmanager
import logging
from services.service_handler import get_services_by_location

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
(
    DESCRIBE_SERVICE,
    GET_LOCATION,
    SELECT_SERVICE,
    CONFIRM_ORDER
) = range(4)

# Load envs
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
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start coverstion with user"""
    keyboard = [[KeyboardButton("Start Service Request 🛠")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to WorkMan! 👋\n"
        "We takin' care of your technical service needs.\n"
        "Press the button below to start.",
        reply_markup=reply_markup
    )
    return DESCRIBE_SERVICE

async def handle_service_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle service description from user"""
    if update.message.text == "Start Service Request 🛠":
        await update.message.reply_text(
           "Please describe the service you need in detail.\n"
           "For example: 'I need a plumber to fix a leaking tap'",
           reply_markup=ReplyKeyboardRemove()
        )
        return DESCRIBE_SERVICE
    
    context.user_data['service_subscription'] = update.message.text
    
    # Request Location
    location_keyboard = [[
        KeyboardButton("Share Location 📍", request_location=True),
        KeyboardButton("Enter Location Manually ✍️")
    ]]
    reply_markup = ReplyKeyboardMarkup(location_keyboard, resize_keyboard=True)

    await update.message.reply_markup(
        "Please share location to find services near you.",
        reply_markup=reply_markup
    )
    return GET_LOCATION

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    """Handle user's location"""
    if update.message.location:
        context.user_data['latitude'] = update.message.location.latitude
        context.user_data['longitude'] = update.message.location.longitude
        location_type = "cordinates"
    else:
        context.user_data['manual_location'] = update.message.text
        location_type = "manual"

    services = get_services_by_location(
        city=Service.city,
        country=Service.country
    )
    
    if not services:
        await update.message.reply_text(
           "Sorry, no services available in your area, at the moment.",
           reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Create service selection keyboard
    service_keyboard = [[service.service_name] for service in services] 
    reply_markup = ReplyKeyboardMarkup(service_keyboard, resize_keyboard=True)   
    await update.message.reply_text(
        "please select a service from the available options:",
        reply_markup=reply_markup
    )
    return SELECT_SERVICE

async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle service selection"""
    selected_service = update.mesage.text
    context.user_data['selected_service'] = selected_service

    comfirm_keyboard = [['Confirm ✅', 'Cancel ❌']],
    reply_markup=ReplyKeyboardMarkup(comfirm_keyboard, resize=True)

    service = db.query(Service).filter(Service.service_name == selected_service).first()

    await update.message.repy_text(
        f"You ordered for : {selected_service}\n"
        f"You'll be charged Ugx {service.price} for the service.\n"
        f"Description: {service.description}\n\n"
        f"Would you like to comfirm this order?",
        reply_markup=reply_markup
    )   
    return CONFIRM_ORDER
    

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle order comfirmation"""
    query = update.callback_query
    if update.message.text == 'Confirm ✅':
        service_id = int(query.data.split("_")[1])
        user_id = update.effective_user.id
        service = service = db.query(Service).filter(Service.id == service_id).first()
        

        try:
            new_order = Order(
                service_id=service_id,
                user_id=user_id,
                status="pending"
            )
            db.add(new_order)
            db.commit
            
            await update.message.reply_text(
                "Order placed. A WorkMan is takin' care.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            await update.message.reply_text(
                "Oops, there was an error processing your order, Please try again.",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await update.message.reply_text(
            "Order cancelled. feel free to start with /start.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.End

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation."""
    await update.message.reply_text(
        "Conversation cancelled. Send /start to begin again.",
        reply_markup=ReplyKeyboardRemove
    )
    return ConversationHandler.END

# Set up conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start_command)],
    states={
        DESCRIBE_SERVICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service_description)
        ],
        GET_LOCATION: [
            MessageHandler(filters.LOCATION, handle_location),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location)
        ],
        SELECT_SERVICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service_selection)
        ],
        CONFIRM_ORDER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation)
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)


# Register bot handlers
bot_app.add_handler(conv_handler)

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
            service_id=service.service_id,
            service_name=service.service_name,
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
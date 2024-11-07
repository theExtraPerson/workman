# Main bot logic and message handling

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL
from services.service_handler import generate_service_image
from database.models import Order, Service
from database.db_setup import init_db, SessionLocal

WEBHOOK_URL = "WEBHOOK_URL"

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    

# initialise database
init_db()
session = SessionLocal()

async def start(update: Update, context):
    await update.message.reply_text(
        "Please /services to see available services:"
    )

async def list_services(update: Update, context):
    services = session.query(Service).all()
    for service in services:
        keyboard = [[InlineKeyboardButton("Order Now", callback_data=f"order_{service.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(
            photo=open(service.image_path, 'rb'),
            caption=f"{service.name}\n{service.description}\nPrice: ${service.price}",
            reply_markup=reply_markup
        )

async def handle_order(update: Update, context):
    query = update.callback_query
    service_id = int(query.data.split("_")[1])
    user_id = query.from_user.id
    
    # Create a new order
    new_order = Order(
        service_id=service_id,
        user_id=user_id,
        status="pending"
    )

    session.add(new_order)
    session.commit()

    await query.answer("Your Order has been placed")
    await query.edit_message_text(
        "Your order has been placed. Please wait for a response from the service provider."
    )

async def set_webhook():
    await app.set_webhook(url=WEBHOOK_URL + "/api/webhook")


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("services", list_services))
    app.add_handler(CallbackQueryHandler(handle_order, pattern="^order_."))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(set_webhook())
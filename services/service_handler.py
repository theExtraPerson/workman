from __future__ import annotations
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional, Protocol
# from database.models import Service
# from database.db_setup import get_db
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime
import sqlite3
from dataclasses import dataclass
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import logging
import asyncio
import aiohttp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# States for conversation handler
SERVICE_NAME, SERVICE_DESCRIPTION, SERVICE_PRICE, SERVICE_IMAGE = range(4)

@dataclass
class ServiceLocation:
    city: str
    country: str
    is_available: bool = True

class Service(BaseModel):
    provider_id: int
    service_name: str
    description: str
    price: float
    image_path: Optional[str]
    is_active: bool
    location: ServiceLocation
    created_at: datetime

    class Config:
        arbitrary_types_allowed = True

# Repository Interface
class ServiceRepository(Protocol):
    def add(self, service: Service) -> Service:
        pass
    
    def get_by_location(self, city: str, country: str) -> List[Service]:
        pass
    
    def update_availability(self, service_id: int, location: ServiceLocation) -> Service:
        pass
    
    def check_availability(self, service_id: int, city: str, country: str) -> bool:
        pass
  
class SQLiteServiceRepository(ServiceRepository):
    def __init__(self, db_name: str = "services.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
               CREATE TABLE IF NOT EXISTS services (
                    provider_id INTEGER,
                    service_name TEXT,
                    description TEXT,
                    price REAL,
                    image_url TEXT,
                    is_active BOOLEAN,
                    location_city TEXT,
                    location_country TEXT,
                    created_at TIMESTAMP,
                    PRIMARY KEY (provider_id, service_name)
                )
            """)
            conn.commit()

    def add(self, service: Service) -> Service:
        """Add a new service to the database."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO services (provider_id, service_name, description, price, image_url, is_active, location_city, location_country)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (service.provider_id, service.service_name, service.description, service.price,
                  service.image_path, service.is_active, service.location.city, service.location.country))
            conn.commit()
            return service  # Return the added service

# Custom Exceptions
class ServiceOperationError(Exception):
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error

class ImageGenerationError(Exception):
    pass

# Image Generation Strategy Interface
class ImageGenerationStrategy(ABC):
    @abstractmethod
    def generate(self, service: Service) -> str:
        pass

# Concrete Image Generator
class PILImageGenerator(ImageGenerationStrategy):
    IMAGE_DIR = Path("images/service_images")

    def __init__(self, font_path: str = "arial.ttf", font_size: int = 20):
        self.font_path = font_path
        self.font_size = font_size
        self.ensure_image_directory()

    @classmethod
    def ensure_image_directory(cls):
        cls.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    def get_font(self) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(self.font_path, self.font_size)
        except Exception as e:
            logging.warning(f"Failed to load custom font: {e}")
            return ImageFont.load_default()

    def generate(self, service: Service) -> str:
        try:
            img = Image.new('RGB', (800, 500), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            font = self.get_font()

            # Draw service information
            self._draw_service_info(draw, service, font)
            
            image_path = self.IMAGE_DIR / f"{service.service_name}_{service.location.city}.png"
            img.save(image_path)
            return str(image_path)

        except Exception as e:
            raise ImageGenerationError(f"Failed to generate service image: {str(e)}") from e

    def _draw_service_info(self, draw: ImageDraw, service: Service, font: ImageFont):
        draw.text((50, 50), f"Service: {service.service_name}", fill="black", font=font)
        draw.text((50, 150), f"Description: {service.description}", fill="black", font=font)
        draw.text((50, 250), f"Price: Ugx{service.price:2f}", fill="black", font=font)
        draw.text((50, 350), f"Location: {service.location.city}, {service.location.country}", 
                 fill="black", font=font)
        
        status_color = "green" if service.is_active and service.location.is_available else "red"
        status_text = "Available" if service.is_active and service.location.is_available else "Not Available"
        draw.text((50, 450), f"Status: {status_text}", fill=status_color, font=font)

# Service Manager (Facade Pattern)
class ServiceManager:
    def __init__(self, 
                 repository: ServiceRepository,
                 image_generator: ImageGenerationStrategy):
        self.repository = repository
        self.image_generator = image_generator

    def add_service(self, service: Service) -> Service:
        try:
            service.image_path = self.image_generator.generate(service)
            return self.repository.add(service)
        except Exception as e:
            raise ServiceOperationError("Failed to add service", e) from e

    def get_services_by_location(self, city: str, country: str) -> List[Service]:
        try:
            return self.repository.get_by_location(city, country)
        except Exception as e:
            raise ServiceOperationError("Failed to fetch services", e) from e

    def update_service_availability(self, 
                                 service_id: int,
                                 location: ServiceLocation) -> Service:
        try:
            return self.repository.update_availability(service_id, location)
        except Exception as e:
            raise ServiceOperationError("Failed to update service availability", e) from e

    def check_service_availability(self, 
                                service_id: int,
                                city: str,
                                country: str) -> bool:
        try:
            return self.repository.check_availability(service_id, city, country)
        except Exception as e:
            raise ServiceOperationError("Failed to check service availability", e) from e


# Telegram Bot Handler (Separated Concern)
class ServiceBotHandler:
    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        self.SERVICE_NAME, self.SERVICE_DESCRIPTION, self.SERVICE_PRICE, self.SERVICE_IMAGE = range(4)

    async def start_add_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Please enter the name of your service:")
        return self.SERVICE_NAME

    async def handle_service_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle input for the service name."""
        context.user_data['service_name'] = update.message.text
        await update.message.reply_text("Please provide a description for your service:")
        return self.SERVICE_DESCRIPTION

    async def handle_service_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle input for the service description."""
        context.user_data['service_description'] = update.message.text
        await update.message.reply_text("Please enter the price for your service:")
        return self.SERVICE_PRICE

    async def handle_service_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle input for the service price."""
        try:
            price = float(update.message.text)
            context.user_data['service_price'] = price
            await update.message.reply_text("Please upload an image for your service (or type 'skip'):")
            return self.SERVICE_IMAGE
        except ValueError:
            await update.message.reply_text("Invalid price. Please enter a numeric value:")
            return self.SERVICE_PRICE

    async def handle_service_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle input for the service image."""
        if update.message.text.lower() == 'skip':
            image_path = None  # No image provided
        else:
            # Assuming you have logic to handle image uploads
            image_path = update.message.photo[-1].file_id  # Example of getting photo file_id

        # Create a new Service instance and save it
        new_service = Service(
            provider_id=1,  # Replace with actual provider ID
            service_name=context.user_data['service_name'],
            description=context.user_data['service_description'],
            price=context.user_data['service_price'],
            image_path=image_path,
            is_active=True,
            location=ServiceLocation(city="Example City", country="Example Country"),
            created_at=datetime.now()
        )

        try:
            self.service_manager.add_service(new_service)
            await update.message.reply_text("Service registered successfully!")
        except Exception as e:
            await update.message.reply_text(f"Failed to register service: {str(e)}")

        return ConversationHandler.END
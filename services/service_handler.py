# Functions for creating, fetching and managing services

from PIL import Image, ImageDraw, ImageFont
import os

from database.models import Service
from database.db_setup import SessionLocal
#from services.service_handler import generate_service_image

def generate_service_image(service_name, description, price):
    img = Image.new('RGB', (800, 400), color = (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font  = ImageFont.load_default()
    draw.text((50, 50), f"Service: {service_name}", fill="(0, 0, 0)", font=font)
    draw.text((50, 150), f"Description: {description}", fill="(0, 0, 0)", font=font)
    draw.text((50, 250), f"Price: {price}", fill="(0, 0, 0)", font=font)

    image_path = f"images/service_images/{service_name}.png"
    img.save(image_path)
    return image_path

def add_service(service_name, description, price):
    session = SessionLocal()
    new_service = Service(service_name=service_name, description=description, price=price, image_path=generate_service_image(service_name, description, price))
    session.add(new_service)
    session.commit()
    session.close()
    return new_service
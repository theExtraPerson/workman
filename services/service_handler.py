# Functions for creating, fetching and managing services

from PIL import Image, ImageDraw, ImageFont
import os

from database.models import Service
from database.db_setup import get_db
from pathlib import Path


class ServiceImageGenerator:
    IMAGE_DIR =Path("images/service_images")

    @classmethod
    def ensure_image_directory(cls):
        cls.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_service_image(service_name: str, description: str, price: float) -> str:
        try:
            ServiceImageGenerator.ensure_image_directory()


            img = Image.new('RGB', (800, 400), color = (255, 255, 255))
            draw = ImageDraw.Draw(img)

            font  = ImageFont.load_default()
            draw.text((50, 50), f"Service: {service_name}", fill="(0, 0, 0)", font=font)
            draw.text((50, 150), f"Description: {description}", fill="(0, 0, 0)", font=font)
            draw.text((50, 250), f"Price: {price}", fill="(0, 0, 0)", font=font)

            image_path = f"images/service_images/{service_name}.png"
            img.save(image_path)
            return str(image_path)
    
        except Exception as e:
            raise RuntimeError(f"Failed to generate service image: {str(e)}")

def add_service(service_name: str, description: str, price: float) -> str:
    try:
        image_path = ServiceImageGenerator.generate_service_image(
            service_name, description, price
        )

        with get_db as db:
            new_service = Service(
                service_name = service_name,
                description = description,
                price = price,
                image_path = image_path
            )
            db.add(new_service)
            db.commit()
            db.refresh(new_service)
            return new_service
    except Exception as e:
        raise RuntimeError(f"Failed to add service: {str(e)}")
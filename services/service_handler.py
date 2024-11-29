from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional
from database.models import Service
from database.db_setup import get_db
from pathlib import Path
from pydantic import BaseModel

class ServiceLocation(BaseModel):
    city: str
    country: str
    is_available: bool = True

class ServiceImageGenerator:
    IMAGE_DIR = Path("images/service_images")

    @classmethod
    def ensure_image_directory(cls):
        cls.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_service_image(
        service_id: str,
        service_name: str,
        description: str,
        price: float,
        location: ServiceLocation,
        is_active: bool = True
    ) -> str:
        try:
            ServiceImageGenerator.ensure_image_directory()

            # Create a larger image to accommodate location information
            img = Image.new('RGB', (800, 500), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Use a better font if available
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except  Exception:
                font = ImageFont.load_default()

            # Draw service information with location
            draw.text((50, 50), f"Service: {service_name}", fill="black", font=font)
            draw.text((50, 150), f"Description: {description}", fill="black", font=font)
            draw.text((50, 250), f"Price: Ugx{price:2f}", fill="black", font=font)
            draw.text((50, 350), f"Location: {location.city}, {location.country}", fill="black", font=font)
            
            # Add availability status
            status_color = "green" if is_active and location.is_available else "red"
            status_text = "Available" if is_active and location.is_available else "Not Available"
            draw.text((50, 450), f"Status: {status_text}", fill=status_color, font=font)

            image_path = f"images/service_images/{service_name}_{location.city}.png"
            img.save(image_path)
            return str(image_path)

        except Exception as e:
            raise RuntimeError(f"Failed to generate service image: {str(e)}") from e

def add_service(
    service_id: str,    
    service_name: str,
    description: str,
    price: float,
    location: ServiceLocation,
    is_active: bool = True
) -> Service:
    """
    Add a new service with location information
    """
    try:
        image_path = ServiceImageGenerator.generate_service_image(
            service_id=service_id,
            service_name=service_name,
            description=description,
            price=price,
            location=location,
            is_active=is_active
        )

        with get_db() as db:
            new_service = Service(
                service_id=service_id,
                service_name=service_name,
                description=description,
                price=price,
                image_path=image_path,
                city=location.city,
                country=location.country,
                is_active=is_active,
                is_available_in_location=location.is_available
            )
            db.add(new_service)
            db.commit()
            db.refresh(new_service)
            return new_service
    except Exception as e:
        raise RuntimeError(f"Failed to add service: {str(e)}") from e

def get_services_by_location(city: str, country: str) -> List[Service]:
    """
    Get all available services for a specific location
    """
    try:
        with get_db() as db:
            return (
                db.query(Service)
                .filter(
                    Service.city == city,
                    Service.country == country,
                    Service.is_active == True,
                    Service.is_available_in_location == True,
                )
                .all()
            )
    except Exception as e:
        raise RuntimeError(f"Failed to fetch services: {str(e)}") from e

def update_service_availability(
    service_id: int,
    location: ServiceLocation
) -> Service:
    """
    Update service availability for a specific location
    """
    try:
        with get_db() as db:
            service = db.query(Service).filter(Service.id == service_id).first()
            if not service:
                raise ValueError(f"Service with ID {service_id} not found")

            service.city = location.city
            service.country = location.country
            service.is_available_in_location = location.is_available

            # Regenerate image with updated location information
            service.image_path = ServiceImageGenerator.generate_service_image(
                service_id=service.service_id,
                service_name=service.service_namename,
                description=service.description,
                price=service.price,
                location=location,
                is_active=service.is_active
            )

            db.commit()
            db.refresh(service)
            return service
    except Exception as e:
        raise RuntimeError(f"Failed to update service availability: {str(e)}") from e

def check_service_availability(service_id: int, city: str, country: str) -> bool:
    """
    Check if a service is available in a specific location
    """
    try:
        with get_db() as db:
            service = db.query(Service).filter(
                Service.id == service_id,
                Service.city == city,
                Service.country == country,
                Service.is_active == True,
                Service.is_available_in_location == True
            ).first()
            return bool(service)
    except Exception as e:
        raise RuntimeError(f"Oops, this service is unavailabile: {str(e)}") from e
# SQLAlchemy Models for database

from SQLAlchemy import Column, Integer, String, Text, Float
from database.db_setup import Base

class Service(Base):
    __tablename__ = 'services'
    service_id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    image_path = Column(String(100), nullable=False)
    location = Column(String(50), nullable=False)
    is_active = Column(Integer, nullable=False)

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    status = Column(String, default='pending', nullable=False)
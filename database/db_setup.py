# Database initialisation and configuration

from SQLAlchemy import create_engine
from SQLAlchemy.ext.declarative import declarative_base
from SQLAlchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

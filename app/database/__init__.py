from app.database.models import Base
from app.database.session import engine, SessionLocal

# Create all tables
Base.metadata.create_all(bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    Base.metadata.create_all(bind=engine) 
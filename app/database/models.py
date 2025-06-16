from sqlalchemy import Column, Integer, String, Date, JSON, ForeignKey, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import date

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)
    experience_years = Column(Float)
    training_days_per_week = Column(Integer)
    experience_level = Column(String)  # beginner, intermediate, advanced, elite
    
    # Personal Bests (in seconds)
    pb_5k = Column(Integer, nullable=True)
    pb_10k = Column(Integer, nullable=True)
    pb_half_marathon = Column(Integer, nullable=True)
    pb_marathon = Column(Integer, nullable=True)
    
    # Preferences
    preferred_run_time = Column(String)  # morning/afternoon/evening
    long_run_day = Column(String)  # day of week
    max_weekly_mileage = Column(Float, nullable=True)
    
    # Goals
    target_race_date = Column(Date, nullable=True)
    target_race_distance = Column(String, nullable=True)
    target_race_time = Column(Integer, nullable=True)  # in seconds
    
    is_active = Column(Boolean, default=True)
    created_at = Column(Date, default=date.today)
    
    # Profile information
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)  # in kg
    height = Column(Float, nullable=True)  # in cm
    fitness_level = Column(String, nullable=True)  # beginner, intermediate, advanced
    training_frequency = Column(Integer, nullable=True)  # sessions per week

    # Relationships
    training_plans = relationship("TrainingPlan", back_populates="user")

class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    start_date = Column(Date)
    duration_weeks = Column(Integer)
    weekly_structure = Column(JSON)
    verification = Column(JSON)

    # Relationships
    user = relationship("User", back_populates="training_plans") 
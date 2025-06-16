from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date
from enum import Enum

class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    date_of_birth: date
    gender: str
    experience_years: float
    training_days_per_week: int = Field(ge=1, le=7)
    experience_level: ExperienceLevel
    
    # Personal Bests (in seconds)
    pb_5k: Optional[int] = None
    pb_10k: Optional[int] = None
    pb_half_marathon: Optional[int] = None
    pb_marathon: Optional[int] = None
    
    # Preferences
    preferred_run_time: str  # morning/afternoon/evening
    long_run_day: str  # day of week
    max_weekly_mileage: Optional[float] = None
    
    # Goals
    target_race_date: Optional[date] = None
    target_race_distance: Optional[str] = None
    target_race_time: Optional[int] = None  # in seconds
    
    is_active: bool = True
    created_at: date = Field(default_factory=date.today)
    
    # Profile information
    age: Optional[int] = None
    weight: Optional[float] = None  # in kg
    height: Optional[float] = None  # in cm
    fitness_level: Optional[str] = None  # beginner, intermediate, advanced
    training_frequency: Optional[int] = None  # sessions per week 
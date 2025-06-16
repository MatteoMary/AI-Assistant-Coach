from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime, date
from enum import Enum

class SleepQuality(str, Enum):
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"

class Metrics(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: datetime = Field(default_factory=datetime.utcnow)
    
    # Performance metrics
    resting_heart_rate: Optional[int] = None  # bpm
    weight: Optional[float] = None  # kg
    sleep_hours: Optional[float] = None
    fatigue_level: Optional[int] = None  # 1-10 scale
    mood: Optional[str] = None
    stress_level: Optional[int] = None  # 1-10 scale
    
    # Workout metrics
    workout_duration: Optional[int] = None  # minutes
    calories_burned: Optional[int] = None
    average_heart_rate: Optional[int] = None  # bpm
    max_heart_rate: Optional[int] = None  # bpm
    
    # Recovery metrics
    soreness_level: Optional[int] = None  # 1-10 scale
    recovery_score: Optional[int] = None  # 1-100 scale
    
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# DailyMetrics model removed to simplify the application 
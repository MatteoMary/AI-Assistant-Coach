from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum

class WorkoutType(str, Enum):
    EASY_RUN = "easy_run"
    LONG_RUN = "long_run"
    TEMPO = "tempo"
    INTERVALS = "intervals"
    HILLS = "hills"
    RECOVERY = "recovery"
    RACE = "race"
    CROSS_TRAINING = "cross_training"
    REST = "rest"

class WorkoutStatus(str, Enum):
    PLANNED = "planned"
    COMPLETED = "completed"
    MODIFIED = "modified"
    SKIPPED = "skipped"

class Training(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: date
    
    # Workout Details
    type: WorkoutType
    status: WorkoutStatus = Field(default=WorkoutStatus.PLANNED)
    
    # Prescribed Workout
    title: str
    description: str
    distance: Optional[float] = None  # in kilometers
    duration: Optional[int] = None  # in minutes
    target_pace: Optional[str] = None  # format: "MM:SS/km"
    
    # For Interval Workouts
    intervals: Optional[str] = None  # JSON string of interval structure
    
    # Actual Completion Data
    actual_distance: Optional[float] = None
    actual_duration: Optional[int] = None
    actual_pace: Optional[str] = None
    
    # Feedback
    perceived_effort: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None
    
    # Plan Source Tracking
    plan_source: Optional[str] = None  # e.g., "coach_photo", "ai_generated", "manual"
    plan_title: Optional[str] = None  # Title of the plan this workout belongs to
    intensity: Optional[str] = None  # Intensity description (e.g., "Easy pace", "Threshold")
    
    class Config:
        table_args = {"extend_existing": True}

class TrainingPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
    # Plan Details
    name: str
    start_date: date
    end_date: date
    goal_type: str  # e.g., "5K", "Marathon"
    goal_time: Optional[int] = None  # in seconds
    
    # Weekly Structure
    base_mileage: float
    peak_mileage: float
    long_run_day: str
    workout_days: str  # JSON string of days
    
    # Plan Status
    is_active: bool = True
    created_at: date = Field(default_factory=date.today)
    last_modified: date = Field(default_factory=date.today) 
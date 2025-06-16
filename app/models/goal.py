from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum as PyEnum

class GoalType(str, PyEnum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    GENERAL_FITNESS = "general_fitness"

class GoalStatus(str, PyEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
    # Goal details
    type: GoalType
    name: str
    description: str
    target_value: Optional[float] = None  # e.g., target weight, target distance
    target_date: datetime
    
    # Progress tracking
    start_value: Optional[float] = None
    current_value: Optional[float] = None
    status: GoalStatus = Field(default=GoalStatus.ACTIVE)
    progress_percentage: Optional[float] = Field(default=0)  # 0-100
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None 
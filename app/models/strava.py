from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ActivityType(str, Enum):
    RUN = "Run"
    RIDE = "Ride"
    SWIM = "Swim"
    WALK = "Walk"
    HIKE = "Hike"
    WORKOUT = "Workout"

class StravaToken(SQLModel, table=True):
    """Store Strava OAuth tokens for users"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    access_token: str
    refresh_token: str
    expires_at: datetime
    athlete_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StravaActivity(SQLModel, table=True):
    """Store imported Strava activities"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    strava_id: int = Field(unique=True)  # Strava's unique ID for this activity
    
    # Basic Activity Info
    name: str
    type: ActivityType
    start_date: datetime
    
    # Distance & Time
    distance: float  # in meters
    moving_time: int  # in seconds
    elapsed_time: int  # in seconds
    
    # Performance Metrics
    average_speed: Optional[float] = None  # m/s
    max_speed: Optional[float] = None  # m/s
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[int] = None
    
    # Elevation
    total_elevation_gain: Optional[float] = None  # in meters
    
    # Effort
    suffer_score: Optional[int] = None
    calories: Optional[float] = None
    
    # Location
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    
    # Additional Data
    description: Optional[str] = None
    gear_id: Optional[str] = None
    trainer: bool = False
    commute: bool = False
    
    # Import Info
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    
    def distance_km(self) -> float:
        """Convert distance from meters to kilometers"""
        return self.distance / 1000
    
    def pace_per_km(self) -> Optional[str]:
        """Calculate pace in MM:SS/km format for runs"""
        if self.type != ActivityType.RUN or not self.distance or not self.moving_time:
            return None
        
        # Pace in seconds per kilometer
        pace_seconds = (self.moving_time / (self.distance / 1000))
        minutes = int(pace_seconds // 60)
        seconds = int(pace_seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS"""
        hours = self.moving_time // 3600
        minutes = (self.moving_time % 3600) // 60
        seconds = self.moving_time % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}" 
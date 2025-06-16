from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import json

class WorkoutType(str, Enum):
    EASY_RUN = "Easy Run"
    TEMPO_RUN = "Tempo Run"
    INTERVALS = "Intervals"
    FARTLEK = "Fartlek"
    LONG_RUN = "Long Run"
    RECOVERY_RUN = "Recovery Run"
    THRESHOLD_RUN = "Threshold Run"
    TRACK_WORKOUT = "Track Workout"
    HILL_REPEATS = "Hill Repeats"
    RACE = "Race"
    TIME_TRIAL = "Time Trial"
    PROGRESSION_RUN = "Progression Run"

class TerrainType(str, Enum):
    ROAD = "Road"
    TRACK = "Track"
    TRAIL = "Trail"
    TREADMILL = "Treadmill"
    MIXED = "Mixed"

class WeatherCondition(str, Enum):
    PERFECT = "Perfect"
    HOT = "Hot"
    COLD = "Cold"
    WINDY = "Windy"
    RAINY = "Rainy"
    HUMID = "Humid"
    SNOWY = "Snowy"

class WorkoutContext(SQLModel, table=True):
    """Enhanced workout context that users can add to their Strava activities"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    strava_activity_id: int = Field(foreign_key="stravaactivity.strava_id", unique=True)
    
    # Workout Classification
    workout_type: WorkoutType
    terrain: Optional[TerrainType] = None
    
    # Interval Details (JSON stored as string)
    intervals_data: Optional[str] = None  # JSON: [{"distance": "400m", "time": "1:30", "rest": "90s", "hr_avg": 180}]
    
    # Performance Metrics
    avg_hr_work_intervals: Optional[int] = None  # Average HR during work portions only
    max_hr_session: Optional[int] = None
    lactate_measurement: Optional[float] = None  # mmol/L
    rpe_work_intervals: Optional[int] = None  # 1-10 scale for work intervals
    rpe_overall: Optional[int] = None  # 1-10 scale for entire session
    
    # Environmental Factors
    weather: Optional[WeatherCondition] = None
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[int] = None  # Percentage
    
    # Subjective Metrics
    energy_level_pre: Optional[int] = None  # 1-10 scale
    energy_level_post: Optional[int] = None  # 1-10 scale
    motivation: Optional[int] = None  # 1-10 scale
    sleep_quality_previous_night: Optional[int] = None  # 1-10 scale
    
    # Context Notes
    workout_description: Optional[str] = None  # Detailed description
    coaching_notes: Optional[str] = None  # Coach or self-coaching notes
    how_it_felt: Optional[str] = None  # Free text about how the workout felt
    
    # Goals and Targets
    target_pace: Optional[str] = None  # e.g., "4:00/km"
    target_heart_rate: Optional[int] = None
    goal_achieved: Optional[bool] = None
    
    # Recovery and Readiness
    soreness_pre: Optional[int] = None  # 1-10 scale
    soreness_post: Optional[int] = None  # 1-10 scale
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_intervals_data(self) -> List[dict]:
        """Parse intervals data from JSON string"""
        if not self.intervals_data:
            return []
        try:
            return json.loads(self.intervals_data)
        except:
            return []
    
    def set_intervals_data(self, intervals: List[dict]):
        """Store intervals data as JSON string"""
        self.intervals_data = json.dumps(intervals)
    
    def calculate_true_work_pace(self) -> Optional[str]:
        """Calculate actual pace during work intervals"""
        intervals = self.get_intervals_data()
        if not intervals:
            return None
        
        total_work_time = 0
        total_work_distance = 0
        
        for interval in intervals:
            if 'time' in interval and 'distance' in interval:
                # Parse time (format: "1:30" -> 90 seconds)
                time_parts = interval['time'].split(':')
                if len(time_parts) == 2:
                    time_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
                    
                    # Parse distance (format: "400m" -> 0.4 km)
                    distance_str = interval['distance'].lower()
                    if 'm' in distance_str and 'km' not in distance_str:
                        distance_km = float(distance_str.replace('m', '')) / 1000
                    elif 'km' in distance_str:
                        distance_km = float(distance_str.replace('km', ''))
                    else:
                        continue
                    
                    total_work_time += time_seconds
                    total_work_distance += distance_km
        
        if total_work_time > 0 and total_work_distance > 0:
            pace_seconds_per_km = total_work_time / total_work_distance
            minutes = int(pace_seconds_per_km // 60)
            seconds = int(pace_seconds_per_km % 60)
            return f"{minutes}:{seconds:02d}"
        
        return None 
import base64
import json
from typing import Optional, Dict, Any
from openai import OpenAI
from openai import AsyncOpenAI
from datetime import datetime, timedelta

from app.config import settings
from app.services.ml_plan_parser import MLPlanParser
from app.database import get_session
from app.models.training import Training, WorkoutType  # Use SQLModel
from app.models.training import TrainingPlan as SQLModelTrainingPlan  # Use SQLModel
from app.services.plan_storage_service import PlanStorageService
from sqlmodel import Session

class PlanParserService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url="https://api.openai.com/v1"
        ) if settings.OPENAI_API_KEY else None
        self.ml_parser = MLPlanParser()
        self.storage_service = PlanStorageService()

    def _extract_plan_text(self, structured_data: Dict[str, Any]) -> str:
        """Extract a text representation of the plan from the structured data"""
        plan_text = []
        plan_text.append(f"Plan: {structured_data.get('plan_title', 'Untitled Plan')}")
        plan_text.append(f"Start Date: {structured_data.get('start_date', 'Not specified')}")
        plan_text.append(f"Duration: {structured_data.get('duration_weeks', 0)} weeks")
        plan_text.append("\n")
        
        for week in structured_data.get('weekly_structure', []):
            plan_text.append(f"Week {week.get('week_number', 'N/A')}")
            plan_text.append(f"Total Distance: {week.get('total_distance', 0)} miles")
            plan_text.append("\nWorkouts:")
            
            for workout in week.get('workouts', []):
                plan_text.append(f"- {workout.get('day', 'N/A')}: {workout.get('workout_type', 'N/A')}")
                plan_text.append(f"  Distance: {workout.get('distance', 0)} miles")
                plan_text.append(f"  Description: {workout.get('description', 'No description')}")
                plan_text.append("")
            
            plan_text.append("")
        
        return "\n".join(plan_text)

    async def parse_plan_from_image(self, image_data: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Parse a training plan from an image using OpenAI Vision."""
        try:
            # Convert base64 to bytes for storage
            image_bytes = base64.b64decode(image_data)
            
            # Check if we already have this image parsed
            image_hash = self.storage_service._generate_image_hash(image_bytes)
            existing_plan = self.storage_service.get_plan_by_image_hash(user_id, image_hash, db)
            
            if existing_plan:
                print(f"DEBUG: Found existing parsed plan for image hash: {image_hash}")
                # Load existing parsed data
                plan_data = self.storage_service.load_parsed_data(existing_plan)
                # Create training workouts from stored plan
                self.storage_service.create_training_workouts_from_plan(existing_plan, user_id, db)
                
                return {
                    "id": existing_plan.id,
                    "title": existing_plan.plan_title,
                    "parsed_at": existing_plan.parsed_at.isoformat(),
                    "duration_weeks": len(plan_data.get("weekly_structure", [])),
                    "weekly_structure": plan_data.get("weekly_structure", []),
                    "confidence_score": existing_plan.confidence_score,
                    "cached": True
                }
            
            # Parse new image
            print(f"DEBUG: Parsing new image with hash: {image_hash}")
            analysis = await self._analyze_plan_image(image_data)
            
            # Store the parsed plan
            stored_plan = self.storage_service.store_parsed_plan(
                user_id=user_id,
                plan_data=analysis,
                image_data=image_bytes,
                confidence_score=0.9
            )
            
            # Save to database
            db.add(stored_plan)
            db.commit()
            db.refresh(stored_plan)
            
            # Create training workouts
            self.storage_service.create_training_workouts_from_plan(stored_plan, user_id, db)
            
            return {
                "id": stored_plan.id,
                "title": stored_plan.plan_title,
                "parsed_at": stored_plan.parsed_at.isoformat(),
                "duration_weeks": len(analysis.get("weekly_structure", [])),
                "weekly_structure": analysis.get("weekly_structure", []),
                "confidence_score": stored_plan.confidence_score,
                "cached": False
            }
            
        except Exception as e:
            raise Exception(f"Error parsing plan: {str(e)}")

    async def _analyze_plan_image(self, base64_image: str) -> Dict[str, Any]:
        """Analyze a training plan image using OpenAI Vision."""
        try:
            # Create the vision prompt
            vision_prompt = """Analyze this training plan image and extract the structured data. 
            For each workout, calculate the total distance based on the description:
            - For easy runs, use the number before 'm' as the distance in miles, then convert to km (1 mile = 1.60934 km)
              Example: '5m easy' = 5 miles = 8.05 km
            - For intervals, calculate total distance in km:
              * 800m intervals: multiply number of intervals by 0.8
              * 600m intervals: multiply number of intervals by 0.6
              * 400m intervals: multiply number of intervals by 0.4
              * 200m intervals: multiply number of intervals by 0.2
              * Add 6.4 km (4 miles) for warm-up and cool-down to each interval session
            - For hill strides, count them as 100m each
            - For rest days, set distance to 0
            
            Example calculations:
            - "5m easy + 4 x 12 sec strides" = 5 miles = 8.05 km (strides don't add significant distance)
            - "6 x 800 @ 2.30 off 2mins + 4 x 400 @ 65s off 1min" = (6 * 0.8) + (4 * 0.4) + 6.4 = 12.8 km
            - "7 x 600m on grass off 90sec + 4 x 200m @ 32s off 30sec rec" = (7 * 0.6) + (4 * 0.2) + 6.4 = 11.4 km
            
            Return the data in this JSON format:
            {
                "title": "Plan title",
                "duration_weeks": number of weeks,
                "weekly_structure": [
                    {
                        "week_number": week number,
                        "total_distance": total km for the week,
                        "workouts": [
                            {
                                "day": "day name",
                                "workout_type": "type of workout",
                                "distance": calculated total distance in km,
                                "description": "full workout description"
                            }
                        ]
                    }
                ]
            }"""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": vision_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=6000,
                response_format={ "type": "json_object" }
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"Error analyzing image: {str(e)}")

    async def save_parsed_plan(self, plan_data: dict, user_id: int, db: Session) -> SQLModelTrainingPlan:
        """Save the parsed training plan to the database."""
        try:
            print(f"DEBUG: Starting to save plan for user {user_id}")
            print(f"DEBUG: Plan data: {plan_data}")
            
            # Create the training plan
            training_plan = SQLModelTrainingPlan(
                user_id=user_id,
                name=plan_data.get("title", "Untitled Plan"),
                start_date=datetime.utcnow().date(),
                end_date=datetime.utcnow().date() + timedelta(weeks=len(plan_data.get("weekly_structure", []))),
                goal_type="General Training",
                base_mileage=0.0,  # Will calculate from workouts
                peak_mileage=0.0,  # Will calculate from workouts
                long_run_day="Sunday",
                workout_days=json.dumps(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            )
            
            # Add to database and commit
            db.add(training_plan)
            db.commit()
            db.refresh(training_plan)
            print(f"DEBUG: Saved training plan with ID: {training_plan.id}")
            
            # Create individual training entries
            start_date = datetime.utcnow().date()
            created_trainings = []
            
            # Map workout types to our enum
            workout_type_mapping = {
                "Easy Run": WorkoutType.EASY_RUN,
                "Long Run": WorkoutType.LONG_RUN,
                "Tempo": WorkoutType.TEMPO,
                "Intervals": WorkoutType.INTERVALS,
                "Hills": WorkoutType.HILLS,
                "Recovery": WorkoutType.RECOVERY,
                "Rest": WorkoutType.REST
            }
            
            print(f"DEBUG: Processing {len(plan_data.get('weekly_structure', []))} weeks")
            
            for week_data in plan_data.get("weekly_structure", []):
                week_number = week_data.get("week_number", 1)
                week_start = start_date + timedelta(weeks=week_number - 1)
                print(f"DEBUG: Processing week {week_number} with {len(week_data.get('workouts', []))} workouts")
                
                for workout in week_data.get("workouts", []):
                    # Skip rest days
                    if workout.get("workout_type", "").lower() == "rest":
                        print(f"DEBUG: Skipping rest day")
                        continue
                    
                    # Calculate workout date
                    day_name = workout.get("day", "Monday")
                    day_offset = self._get_day_offset(day_name)
                    workout_date = week_start + timedelta(days=day_offset)
                    
                    # Map workout type
                    workout_type = workout_type_mapping.get(
                        workout.get("workout_type", "Easy Run"),
                        WorkoutType.EASY_RUN
                    )
                    
                    print(f"DEBUG: Creating training for {workout_date}: {workout.get('workout_type')} - {workout.get('description')}")
                    
                    # Create training entry
                    training = Training(
                        user_id=user_id,
                        date=workout_date,
                        type=workout_type,
                        title=workout.get("workout_type", "Easy Run"),
                        description=workout.get("description", ""),
                        distance=workout.get("distance"),
                        plan_source="coach_photo",
                        plan_title=plan_data.get("title", "Untitled Plan")
                    )
                    
                    db.add(training)
                    created_trainings.append(training)
            
            print(f"DEBUG: Created {len(created_trainings)} training entries")
            
            # Commit all training entries
            db.commit()
            print(f"DEBUG: Committed all training entries")
            
            # Refresh all trainings to get their IDs
            for training in created_trainings:
                db.refresh(training)
            
            print(f"DEBUG: Successfully saved plan with {len(created_trainings)} workouts")
            return training_plan
            
        except Exception as e:
            print(f"DEBUG: Error saving plan: {str(e)}")
            db.rollback()
            raise Exception(f"Error saving plan: {str(e)}")
    
    def _get_day_offset(self, day_name: str) -> int:
        """Convert day name to offset from Monday"""
        days = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        return days.get(day_name.lower(), 0) 
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI
from sqlmodel import Session, select

from app.config import settings
from app.models.strava import StravaActivity, ActivityType
from app.models.user import User
from app.models.workout_context import WorkoutContext
from app.schemas.chat import ChatMessage


class AICoachService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.system_prompt = f"""You are an expert AI running coach with deep knowledge of training principles, exercise physiology, and performance optimization. 

Your role is to:
- Analyze running data and provide personalized insights
- Give specific, actionable training advice based on actual performance data
- Help athletes understand their training patterns and progress
- Recommend training adjustments based on performance trends
- Provide motivation while maintaining realistic expectations

IMPORTANT DATE INFORMATION:
- TODAY'S DATE: {datetime.now().strftime('%A, %B %d, %Y')}
- When users ask about the current date, always use the date above
- Training plan dates are historical/future dates and should not be confused with today's date
- Plan dates show when workouts are scheduled, not the current date

CRITICAL INSTRUCTIONS:
- ALWAYS reference the user's ACTUAL training plan that is provided in the context
- NEVER generate a new training plan unless specifically asked to create one
- When asked about the user's current plan, refer to the detailed weekly structure provided in the context
- Base all advice on the user's existing plan, not on generic training principles
- If the user asks "what is my plan for this week", use the "CURRENT WEEK" section from their actual plan
- When the user asks "what is my plan for this week according to my [plan name]", look for the "CURRENT WEEK" section and list out each day's workout exactly as shown
- If you see "CURRENT WEEK" in the context, that's the user's actual plan for this week - use it!

Always be:
- Specific and data-driven in your recommendations
- Encouraging but realistic about progress
- Safety-conscious and warn about overtraining
- Focused on long-term development over short-term gains

Use the athlete's actual data and training plan to provide personalized advice."""

    async def analyze_training_data(
        self, 
        session: Session, 
        user_id: int, 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze user's Strava activities and generate insights"""
        
        # Get recent activities
        since_date = datetime.utcnow() - timedelta(days=days_back)
        activities = session.exec(
            select(StravaActivity)
            .where(StravaActivity.user_id == user_id)
            .where(StravaActivity.start_date >= since_date)
            .order_by(StravaActivity.start_date.desc())
        ).all()

        if not activities:
            return {"error": "No activities found in the specified period"}

        # Calculate key metrics
        analysis = self._calculate_training_metrics(activities, session)
        
        # Generate AI insights
        if self.client:
            ai_insights = await self._generate_ai_insights(analysis, activities)
            analysis["ai_insights"] = ai_insights
        
        return analysis

    def _calculate_training_metrics(self, activities: List[StravaActivity], session: Session = None) -> Dict[str, Any]:
        """Calculate training metrics from activities with enhanced context"""
        if not activities:
            return {}

        # Basic stats
        total_activities = len(activities)
        running_activities = [a for a in activities if a.type == ActivityType.RUN]
        
        # Distance and time
        total_distance = sum(a.distance_km() for a in running_activities)
        total_time_hours = sum(a.moving_time for a in running_activities) / 3600
        
        # Pace analysis
        paces = []
        enhanced_activities = []
        
        for activity in running_activities:
            if activity.distance > 1000 and activity.moving_time > 0:  # At least 1km
                pace_seconds = activity.moving_time / (activity.distance / 1000)
                paces.append(pace_seconds)
                
                # Get enhanced context if available
                context = None
                if session:
                    context = session.exec(
                        select(WorkoutContext).where(
                            WorkoutContext.strava_activity_id == activity.strava_id
                        )
                    ).first()
                
                activity_data = {
                    "name": activity.name,
                    "distance_km": activity.distance_km(),
                    "pace": activity.pace_per_km(),
                    "date": activity.start_date.strftime("%Y-%m-%d"),
                    "heart_rate": activity.average_heartrate,
                    "strava_id": activity.strava_id
                }
                
                # Add enhanced context data
                if context:
                    activity_data.update({
                        "workout_type": context.workout_type.value if context.workout_type else None,
                        "true_work_pace": context.calculate_true_work_pace(),
                        "avg_hr_work_intervals": context.avg_hr_work_intervals,
                        "lactate": context.lactate_measurement,
                        "rpe_work": context.rpe_work_intervals,
                        "rpe_overall": context.rpe_overall,
                        "goal_achieved": context.goal_achieved,
                        "how_it_felt": context.how_it_felt,
                        "intervals_count": len(context.get_intervals_data()) if context.intervals_data else 0
                    })
                
                enhanced_activities.append(activity_data)
        
        avg_pace_seconds = sum(paces) / len(paces) if paces else 0
        
        # Heart rate analysis
        hr_activities = [a for a in running_activities if a.average_heartrate]
        avg_hr = sum(a.average_heartrate for a in hr_activities) / len(hr_activities) if hr_activities else None
        
        # Training frequency
        days_span = (activities[0].start_date - activities[-1].start_date).days + 1
        weekly_frequency = (total_activities / days_span) * 7 if days_span > 0 else 0
        
        # Weekly distance
        weekly_distance = (total_distance / days_span) * 7 if days_span > 0 else 0
        
        # Longest run
        longest_run = max((a.distance_km() for a in running_activities), default=0)
        
        # Pace consistency (standard deviation)
        import statistics
        pace_consistency = statistics.stdev(paces) if len(paces) > 1 else 0
        
        # Enhanced analysis with context
        workout_types = {}
        interval_sessions = 0
        avg_lactate = 0
        lactate_count = 0
        
        for activity in enhanced_activities:
            if activity.get("workout_type"):
                workout_type = activity["workout_type"]
                workout_types[workout_type] = workout_types.get(workout_type, 0) + 1
            
            if activity.get("intervals_count", 0) > 0:
                interval_sessions += 1
            
            if activity.get("lactate"):
                avg_lactate += activity["lactate"]
                lactate_count += 1
        
        avg_lactate = round(avg_lactate / lactate_count, 1) if lactate_count > 0 else None
        
        return {
            "period_days": days_span,
            "total_activities": total_activities,
            "running_activities": len(running_activities),
            "total_distance_km": round(total_distance, 2),
            "total_time_hours": round(total_time_hours, 1),
            "weekly_frequency": round(weekly_frequency, 1),
            "weekly_distance_km": round(weekly_distance, 2),
            "average_pace_per_km": self._format_pace(avg_pace_seconds),
            "average_heart_rate": round(avg_hr) if avg_hr else None,
            "longest_run_km": round(longest_run, 2),
            "pace_consistency_seconds": round(pace_consistency, 0),
            "recent_activities": enhanced_activities[:5],  # Last 5 runs with context
            # Enhanced metrics
            "workout_types": workout_types,
            "interval_sessions": interval_sessions,
            "avg_lactate": avg_lactate,
            "context_enhanced": len([a for a in enhanced_activities if a.get("workout_type")]),
        }

    def _format_pace(self, pace_seconds: float) -> str:
        """Format pace in MM:SS format"""
        if pace_seconds <= 0:
            return "N/A"
        minutes = int(pace_seconds // 60)
        seconds = int(pace_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    async def _generate_ai_insights(
        self, 
        metrics: Dict[str, Any], 
        activities: List[StravaActivity]
    ) -> str:
        """Generate AI-powered insights from training data"""
        
        if not self.client:
            return "AI insights require OpenAI API key configuration."

        # Prepare enhanced data for AI analysis
        enhanced_summary = ""
        if metrics.get('context_enhanced', 0) > 0:
            enhanced_summary = f"""
Enhanced Training Context:
- Workout types breakdown: {json.dumps(metrics.get('workout_types', {}), indent=2)}
- Interval sessions: {metrics.get('interval_sessions', 0)}
- Average lactate (when measured): {metrics.get('avg_lactate')} mmol/L
- Enhanced activities: {metrics.get('context_enhanced', 0)}/{metrics['running_activities']} with context
"""

        data_summary = f"""
Training Analysis ({metrics['period_days']} days):
- Total runs: {metrics['running_activities']}
- Weekly frequency: {metrics['weekly_frequency']} runs/week
- Weekly distance: {metrics['weekly_distance_km']} km/week
- Average pace: {metrics['average_pace_per_km']}/km
- Average heart rate: {metrics['average_heart_rate']} bpm
- Longest run: {metrics['longest_run_km']} km
- Pace consistency: {metrics['pace_consistency_seconds']} seconds variation

{enhanced_summary}

Recent activities with context:
{json.dumps(metrics['recent_activities'], indent=2)}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"""Analyze this runner's training data and provide specific insights:

{data_summary}

Please provide:
1. Overall assessment of training consistency and volume
2. Pace analysis and performance trends
3. Specific recommendations for improvement
4. Any concerns about training load or recovery
5. Suggestions for upcoming training focus

Keep it concise but actionable."""}
                ],
                max_tokens=800,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Unable to generate AI insights: {str(e)}"

    async def get_coaching_response(
        self,
        user_message: str,
        session: Session,
        user_id: int,
        context: Optional[Dict] = None
    ) -> str:
        """Get personalized coaching response based on user's data"""
        
        if not self.client:
            return "I'm sorry, but AI coaching features require an OpenAI API key to be configured. Please check with your administrator."

        # Get recent training data for context
        training_data = await self.analyze_training_data(session, user_id, days_back=14)
        
        # Get parsed plan context
        plan_context = self._get_parsed_plan_context(user_id, session)
        
        # Build context message
        context_msg = ""
        if "error" not in training_data:
            context_msg = f"""
Recent training context (last 14 days):
- Weekly distance: {training_data.get('weekly_distance_km', 0)} km
- Weekly frequency: {training_data.get('weekly_frequency', 0)} runs
- Average pace: {training_data.get('average_pace_per_km', 'N/A')}
- Recent runs: {len(training_data.get('recent_activities', []))}
"""
        
        if plan_context:
            context_msg += f"\n{plan_context}"

        try:
            messages = [
                {"role": "system", "content": self.system_prompt + "\n\nAlways provide specific, actionable advice based on the athlete's actual training data."},
            ]
            
            if context_msg:
                messages.append({"role": "system", "content": context_msg})
            
            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=600,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"I'm having trouble processing your request right now. Error: {str(e)}"

    async def generate_weekly_insights(
        self,
        session: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """Generate weekly training insights and recommendations"""
        
        # Get last week's data
        analysis = await self.analyze_training_data(session, user_id, days_back=7)
        
        if "error" in analysis:
            return analysis

        # Compare with previous week
        prev_week_analysis = await self.analyze_training_data(session, user_id, days_back=14)
        
        insights = {
            "current_week": analysis,
            "trends": self._calculate_trends(analysis, prev_week_analysis),
            "recommendations": await self._generate_weekly_recommendations(analysis)
        }
        
        return insights

    def _calculate_trends(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Calculate week-over-week trends"""
        if "error" in previous:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate changes
        distance_change = current.get('weekly_distance_km', 0) - previous.get('weekly_distance_km', 0)
        frequency_change = current.get('weekly_frequency', 0) - previous.get('weekly_frequency', 0)
        
        return {
            "distance_change_km": round(distance_change, 2),
            "frequency_change": round(frequency_change, 1),
            "distance_change_percent": round((distance_change / previous.get('weekly_distance_km', 1)) * 100, 1),
        }

    async def _generate_weekly_recommendations(self, analysis: Dict[str, Any]) -> str:
        """Generate weekly training recommendations"""
        
        if not self.client:
            return "Weekly recommendations require AI configuration."

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a running coach providing weekly training recommendations."},
                    {"role": "user", "content": f"""Based on this week's training data, provide 3 specific recommendations for next week:

Weekly stats:
- Distance: {analysis.get('weekly_distance_km')} km
- Frequency: {analysis.get('weekly_frequency')} runs
- Average pace: {analysis.get('average_pace_per_km')}
- Longest run: {analysis.get('longest_run_km')} km

Be specific and actionable."""}
                ],
                max_tokens=400,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Unable to generate recommendations: {str(e)}"

    async def clear_existing_plans(self, user_id: int, session: Session) -> None:
        """Clear existing training plans for a user"""
        try:
            # Delete all workouts with plan_source
            existing_plans = session.exec(
                select(Training)
                .where(
                    Training.user_id == user_id,
                    Training.plan_source.in_(["coach_photo", "ai_generated"])
                )
            ).all()
            
            for plan in existing_plans:
                session.delete(plan)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to clear existing plans: {str(e)}")

    async def generate_training_plan(
        self,
        session: Session,
        user_id: int,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """Generate an AI training plan"""
        
        if not self.client:
            return {"error": "OpenAI API key not configured"}
        
        try:
            # Clear existing plans first
            await self.clear_existing_plans(user_id, session)
            
            # Get user's recent training data for context
            training_data = await self.analyze_training_data(session, user_id, days_back=30)
            
            # Build context for AI plan generation
            context = ""
            if "error" not in training_data:
                context = f"""
User's Recent Training Context:
- Weekly distance: {training_data.get('weekly_distance_km', 0)} km
- Weekly frequency: {training_data.get('weekly_frequency', 0)} runs
- Average pace: {training_data.get('average_pace_per_km', 'N/A')}
- Recent activities: {training_data.get('running_activities', 0)}
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert running coach. Create a {weeks}-week training plan that progressively builds fitness.

Structure the plan as JSON with this format:
{{
  "plan_title": "string",
  "goal": "string", 
  "duration_weeks": {weeks},
  "weekly_structure": [
    {{
      "week_number": 1,
      "workouts": [
        {{
          "day": "Monday",
          "workout_type": "Easy Run|Intervals|Tempo|Long Run|Rest",
          "distance": "5km",
          "description": "detailed workout description",
          "intensity": "Easy pace|Moderate|Hard"
        }}
      ]
    }}
  ]
}}

Include variety: easy runs, tempo runs, intervals, long runs, and rest days.
Make it progressive and appropriate for the user's fitness level."""
                    },
                    {
                        "role": "user", 
                        "content": f"Generate a {weeks}-week training plan.{context}"
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse the AI response
            ai_response = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if ai_response.startswith("```json"):
                ai_response = ai_response.replace("```json", "").replace("```", "").strip()
            
            import json
            plan_data = json.loads(ai_response)
            
            # Save the plan to database
            from app.models.training import Training
            from datetime import datetime, timedelta
            
            created_trainings = []
            start_date = datetime.now().date()
            
            for week_data in plan_data.get("weekly_structure", []):
                week_number = week_data.get("week_number", 1)
                week_start = start_date + timedelta(weeks=week_number - 1)
                
                for workout in week_data.get("workouts", []):
                    if workout.get("workout_type", "").lower() == "rest":
                        continue
                        
                    # Calculate workout date
                    day_name = workout.get("day", "Monday")
                    day_offset = self._get_day_offset(day_name)
                    workout_date = week_start + timedelta(days=day_offset)
                    
                    # Check for existing workout on this date
                    existing_workout = session.exec(
                        select(Training)
                        .where(
                            Training.user_id == user_id,
                            Training.date == workout_date
                        )
                    ).first()
                    
                    if existing_workout:
                        continue  # Skip if workout already exists for this date
                    
                    # Map workout type
                    workout_type_mapping = {
                        "Easy Run": "easy_run",
                        "Long Run": "long_run",
                        "Tempo": "tempo", 
                        "Intervals": "intervals",
                        "Rest": "rest"
                    }
                    mapped_type = workout_type_mapping.get(workout.get("workout_type", "Easy Run"), "easy_run")
                    
                    # Extract distance from description for interval workouts
                    distance = None
                    if mapped_type == "intervals":
                        description = workout.get("description", "")
                        # Look for interval patterns in the description
                        import re
                        # Match patterns like "7x600m", "6 x 800m", "7x600m + 4x200m"
                        interval_pattern = r'(\d+)\s*x\s*(\d+)(?:m|km)'
                        matches = re.findall(interval_pattern, description)
                        if matches:
                            total_distance = 0
                            for reps, dist in matches:
                                reps = int(reps)
                                dist = int(dist)
                                # Convert to km if in meters
                                if 'm' in description.lower():
                                    dist = dist / 1000
                                total_distance += reps * dist
                            distance = round(total_distance, 2)  # Round to 2 decimal places
                            # Store the total distance in the description if not already there
                            if f"{total_distance}km" not in description.lower():
                                workout['description'] = description
                    else:
                        distance = self._parse_distance(workout.get("distance", ""))
                    
                    training = Training(
                        user_id=user_id,
                        date=workout_date,
                        type=mapped_type,
                        title=workout.get("workout_type", "Easy Run"),
                        description=workout.get("description", ""),
                        distance=distance,
                        intensity=workout.get("intensity", "Moderate"),
                        notes="AI generated training plan",
                        plan_source="ai_generated",
                        plan_title=plan_data.get("plan_title", "AI Training Plan")
                    )
                    
                    session.add(training)
                    created_trainings.append({
                        "date": workout_date.isoformat(),
                        "day": day_name,
                        "workout": workout.get("description", ""),
                        "type": workout.get("workout_type", "")
                    })
            
            session.commit()
            
            return {
                "success": True,
                "message": f"Successfully generated AI training plan with {len(created_trainings)} workouts",
                "plan_title": plan_data.get("plan_title", "AI Training Plan"),
                "workouts_created": len(created_trainings),
                "duration_weeks": weeks,
                "created_workouts": created_trainings[:10]
            }
            
        except Exception as e:
            session.rollback()
            return {"error": f"Failed to generate training plan: {str(e)}"}
    
    def _get_day_offset(self, day_name: str) -> int:
        """Convert day name to offset from Monday"""
        days = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        return days.get(day_name.lower(), 0)
    
    def _parse_distance(self, distance_str: str) -> Optional[float]:
        """Parse distance string to kilometers"""
        if not distance_str:
            return None
            
        # Handle interval workouts
        if "x" in distance_str.lower():
            return self._calculate_interval_distance(distance_str)
            
        # Handle regular distance formats
        try:
            # Remove any non-numeric characters except decimal point
            distance_str = ''.join(c for c in distance_str if c.isdigit() or c == '.')
            if distance_str:
                distance = float(distance_str)
                # Convert miles to kilometers if needed
                if "mile" in distance_str.lower():
                    distance *= 1.60934
                return distance
        except:
            pass
        return None

    def _calculate_interval_distance(self, interval_str: str) -> Optional[float]:
        """Calculate total distance for interval workouts"""
        try:
            # Split into main intervals and additional intervals if any
            parts = interval_str.split('+')
            total_distance = 0
            
            for part in parts:
                part = part.strip()
                if 'x' in part:
                    # Parse format like "6 x 800m" or "7 x 600m"
                    reps, distance = part.split('x')
                    reps = int(reps.strip())
                    
                    # Parse distance
                    distance = distance.strip()
                    if 'm' in distance.lower():
                        # Convert meters to kilometers
                        distance_km = float(distance.lower().replace('m', '')) / 1000
                    elif 'km' in distance.lower():
                        distance_km = float(distance.lower().replace('km', ''))
                    else:
                        continue
                        
                    total_distance += reps * distance_km
            
            return total_distance if total_distance > 0 else None
        except:
            return None

    async def get_quick_insights(self, session: Session):
        """Get quick insights from the AI coach."""
        return {
            "insights": [
                "Your training consistency has improved over the last week.",
                "Consider adding more recovery days between intense workouts.",
                "Your pace is trending in the right direction."
            ]
        }
    
    async def chat(self, message: str, session: Session) -> str:
        """Chat with the AI coach."""
        return f"I'm your AI running coach. You said: {message}. How can I help you with your training today?" 

    def _get_parsed_plan_context(self, user_id: int, session: Session) -> str:
        """Get context about user's parsed training plans"""
        try:
            from app.services.plan_storage_service import PlanStorageService
            from datetime import datetime, timedelta
            
            storage_service = PlanStorageService()
            
            # Get user's parsed plans
            plans = storage_service.get_user_plans(user_id, session)
            
            if not plans:
                return ""
            
            # Build context string
            context_parts = [f"User has {len(plans)} saved training plan(s):"]
            
            for i, plan in enumerate(plans[:2]):  # Limit to 2 plans for context
                plan_data = storage_service.load_parsed_data(plan)
                stats = storage_service.get_plan_statistics(plan)
                
                context_parts.append(f"""
Plan {i+1}: {plan.plan_title} (parsed {plan.parsed_at.strftime('%B %Y')})
- Duration: {stats['total_weeks']} weeks
- Total workouts: {stats['total_workouts']}
- Total distance: {stats['total_distance_km']:.1f} km
- Confidence score: {plan.confidence_score}
""")
                
                # Add detailed weekly structure
                weekly_structure = plan_data.get('weekly_structure', [])
                if weekly_structure:
                    context_parts.append(f"Detailed Weekly Structure:")
                    
                    # Calculate current week - but allow for flexibility
                    today = datetime.now().date()
                    plan_start_date = plan.parsed_at.date()
                    
                    # Try to intelligently determine which week to show
                    # First, check if the plan title contains a month name
                    month_names = [
                        "january", "february", "march", "april", "may", "june",
                        "july", "august", "september", "october", "november", "december"
                    ]
                    
                    plan_title_lower = plan.plan_title.lower()
                    current_month_name = today.strftime("%B").lower()
                    
                    # Check if plan title mentions the current month
                    if any(month in plan_title_lower for month in month_names):
                        # Plan mentions a specific month
                        if current_month_name in plan_title_lower:
                            # We're in the month mentioned in the plan
                            # Calculate which week of the month we're in
                            month_start = today.replace(day=1)
                            week_of_month = (today - month_start).days // 7
                            
                            if week_of_month >= len(weekly_structure) - 1:
                                # We're in the last week of the month
                                current_week = len(weekly_structure) - 1
                            else:
                                # We're in an earlier week of the month
                                current_week = week_of_month
                        else:
                            # Plan mentions a different month - show the last week
                            current_week = len(weekly_structure) - 1
                    else:
                        # Plan doesn't mention a specific month - use default calculation
                        weeks_since_start = (today - plan_start_date).days // 7
                        current_week = min(weeks_since_start, len(weekly_structure) - 1)
                    
                    # Show current week and next 2 weeks
                    for week_idx in range(max(0, current_week), min(len(weekly_structure), current_week + 3)):
                        week_data = weekly_structure[week_idx]
                        week_label = "CURRENT WEEK" if week_idx == current_week else f"Week {week_idx + 1}"
                        
                        context_parts.append(f"\n{week_label}:")
                        
                        # Calculate week dates
                        week_start = plan_start_date + timedelta(weeks=week_idx)
                        week_end = week_start + timedelta(days=6)
                        context_parts.append(f"Dates: {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}")
                        
                        # Show all workouts for this week
                        workouts = week_data.get('workouts', [])
                        for workout in workouts:
                            day = workout.get('day', 'N/A')
                            workout_type = workout.get('workout_type', 'N/A')
                            description = workout.get('description', 'No description')
                            distance = workout.get('distance', '')
                            
                            if distance:
                                context_parts.append(f"  {day}: {workout_type} - {description} ({distance})")
                            else:
                                context_parts.append(f"  {day}: {workout_type} - {description}")
                        
                        # Add weekly summary
                        total_distance = sum(float(w.get('distance', 0)) for w in workouts if w.get('distance'))
                        context_parts.append(f"  Weekly total: {total_distance:.1f} km")
            
            if len(plans) > 2:
                context_parts.append(f"\n... and {len(plans) - 2} more plans")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            return f"Error getting plan context: {str(e)}" 
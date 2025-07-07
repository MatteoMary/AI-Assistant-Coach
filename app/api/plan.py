from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import date, timedelta

from app.database import get_session
from app.models.training import Training
from app.schemas.training import TrainingPlanCreate, TrainingPlanResponse
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/plan", tags=["plan"])

@router.get("/", response_model=List[TrainingPlanResponse])
async def get_plans(
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> List[TrainingPlanResponse]:
    """Get all training plans for a user"""
    # Get all workouts that are part of a plan
    query = select(Training).where(
        Training.user_id == user_id,
        Training.plan_source.isnot(None)
    ).order_by(Training.date.desc())
    
    workouts = session.exec(query).all()
    
    # Group workouts by plan
    plans = {}
    for workout in workouts:
        plan_title = workout.plan_title or "Untitled Plan"
        if plan_title not in plans:
            plans[plan_title] = {
                "title": plan_title,
                "start_date": workout.date,
                "end_date": workout.date,
                "workouts": []
            }
        
        plans[plan_title]["workouts"].append(workout)
        if workout.date < plans[plan_title]["start_date"]:
            plans[plan_title]["start_date"] = workout.date
        if workout.date > plans[plan_title]["end_date"]:
            plans[plan_title]["end_date"] = workout.date
    
    return list(plans.values())

@router.post("/", response_model=TrainingPlanResponse)
async def create_plan(
    plan: TrainingPlanCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> TrainingPlanResponse:
    """Create a new training plan"""
    # Create all workouts in the plan
    for workout in plan.workouts:
        db_workout = Training(**workout.dict())
        session.add(db_workout)
    
    session.commit()
    return {"message": "Training plan created successfully"}

@router.delete("/{plan_title}")
async def delete_plan(
    plan_title: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a training plan"""
    # Get all workouts in the plan
    query = select(Training).where(
        Training.user_id == current_user.id,
        Training.plan_title == plan_title
    )
    
    workouts = session.exec(query).all()
    
    # Delete all workouts
    for workout in workouts:
        session.delete(workout)
    
    session.commit()
    return {"message": f"Training plan '{plan_title}' deleted successfully"}

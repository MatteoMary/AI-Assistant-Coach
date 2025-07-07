from sqlmodel import Session, select
from typing import List, Optional
from datetime import date, timedelta

from app.models.training import Training
from app.schemas.training import TrainingCreate, TrainingUpdate

def get_training(session: Session, training_id: int) -> Optional[Training]:
    """Get a training session by ID"""
    return session.get(Training, training_id)

def get_trainings(
    session: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Training]:
    """Get training sessions for a user with optional date filtering"""
    query = select(Training).where(Training.user_id == user_id)
    
    if start_date:
        query = query.where(Training.date >= start_date)
    if end_date:
        query = query.where(Training.date <= end_date)
    
    query = query.offset(skip).limit(limit).order_by(Training.date.desc())
    return list(session.exec(query).all())

def create_training(session: Session, training: TrainingCreate) -> Training:
    """Create a new training session"""
    db_training = Training(**training.dict())
    session.add(db_training)
    session.commit()
    session.refresh(db_training)
    return db_training

def update_training(session: Session, training_id: int, training: TrainingUpdate) -> Optional[Training]:
    """Update a training session"""
    db_training = session.get(Training, training_id)
    if not db_training:
        return None
    
    for key, value in training.dict(exclude_unset=True).items():
        setattr(db_training, key, value)
    
    session.add(db_training)
    session.commit()
    session.refresh(db_training)
    return db_training

def delete_training(session: Session, training_id: int) -> bool:
    """Delete a training session"""
    db_training = session.get(Training, training_id)
    if not db_training:
        return False
    
    session.delete(db_training)
    session.commit()
    return True

def get_training_plan(
    session: Session,
    user_id: int,
    plan_title: str
) -> List[Training]:
    """Get all workouts in a training plan"""
    query = select(Training).where(
        Training.user_id == user_id,
        Training.plan_title == plan_title
    ).order_by(Training.date)
    return list(session.exec(query).all())

def get_recent_trainings(
    session: Session,
    user_id: int,
    days: int = 7
) -> List[Training]:
    """Get recent training sessions for a user"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    query = select(Training).where(
        Training.user_id == user_id,
        Training.date >= start_date,
        Training.date <= end_date
    ).order_by(Training.date.desc())
    
    return list(session.exec(query).all())

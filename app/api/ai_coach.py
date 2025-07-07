from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.database import get_session
from app.models.user import User
from app.models.training import Training
from app.models.metrics import Metrics
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from app.services.chat_service import ChatService
from app.crud import get_recent_trainings, get_recent_metrics
from app.api.auth import get_current_user
from app.services.ai_coach_service import AICoachService

router = APIRouter(prefix="/ai-coach", tags=["ai-coach"])
chat_service = ChatService()
ai_coach_service = AICoachService()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_coach(
    message: ChatMessage,
    session: Session = Depends(get_session)
) -> ChatResponse:
    """Chat with the AI coach."""
    try:
        response = await ai_coach_service.chat(message.content, session)
        return ChatResponse(content=response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/analysis", response_model=Dict[str, Any])
async def get_coach_analysis(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get a comprehensive analysis from the AI coach about your recent training and metrics.
    """
    # Get recent data
    recent_trainings = get_recent_trainings(session, current_user.id, days=14)
    recent_metrics = get_recent_metrics(session, current_user.id, days=14)
    
    if not recent_trainings and not recent_metrics:
        raise HTTPException(
            status_code=404,
            detail="No recent training or metrics data found for analysis"
        )
    
    # Get chat response with analysis request
    response = await chat_service.get_chat_response(
        user=current_user,
        message="Please provide a comprehensive analysis of my recent training and metrics, including: "
                "1. Training load and progression "
                "2. Recovery status "
                "3. Areas for improvement "
                "4. Recommendations for next steps",
        recent_trainings=recent_trainings,
        recent_metrics=recent_metrics
    )
    
    if "error" in response:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting analysis from AI coach: {response['error']}"
        )
    
    return {
        "analysis": response["response"],
        "context_used": response["context_used"]
    }

@router.get("/recommendations", response_model=Dict[str, Any])
async def get_training_recommendations(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get personalized training recommendations from the AI coach.
    """
    # Get recent data
    recent_trainings = get_recent_trainings(session, current_user.id, days=14)
    recent_metrics = get_recent_metrics(session, current_user.id, days=14)
    
    if not recent_trainings and not recent_metrics:
        raise HTTPException(
            status_code=404,
            detail="No recent training or metrics data found for recommendations"
        )
    
    # Get chat response with recommendations request
    response = await chat_service.get_chat_response(
        user=current_user,
        message="Based on my recent training and metrics, please provide: "
                "1. Specific workout recommendations for the next week "
                "2. Training intensity suggestions "
                "3. Recovery strategies "
                "4. Any adjustments to my current training plan",
        recent_trainings=recent_trainings,
        recent_metrics=recent_metrics
    )
    
    if "error" in response:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting recommendations from AI coach: {response['error']}"
        )
    
    return {
        "recommendations": response["response"],
        "context_used": response["context_used"]
    }

@router.get("/quick-insights")
async def get_quick_insights(
    user_id: int = 1,  # Default to user 1 for now
    session: Session = Depends(get_session)
):
    """Get quick insights about the user's training."""
    try:
        insights = await ai_coach_service.get_quick_insights(user_id)
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting quick insights: {str(e)}"
        )

@router.post("/generate-plan")
async def generate_training_plan(
    user_id: int = 1,  # Default to user 1 for now
    weeks: int = 4,
    session: Session = Depends(get_session)
):
    """Generate a personalized training plan."""
    try:
        plan = await ai_coach_service.generate_training_plan(user_id, weeks)
        return plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating training plan: {str(e)}"
        ) 
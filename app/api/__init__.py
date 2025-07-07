from fastapi import APIRouter
from app.api import (
    user,
    metrics,
    training,
    plan,
    chat,
    strava,
    ai_coach,
    workout_context,
    plan_parser,
    auth,
    summary
)

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/users", tags=["auth"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(training.router, prefix="/training", tags=["training"])
api_router.include_router(plan.router, prefix="/plan", tags=["plan"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(ai_coach.router, prefix="/ai-coach", tags=["ai-coach"])
api_router.include_router(workout_context.router, prefix="/workout-context", tags=["workout-context"])
api_router.include_router(plan_parser.router, prefix="/plan-parser", tags=["plan-parser"])
api_router.include_router(strava.router, prefix="/auth/strava", tags=["strava"])
api_router.include_router(summary.router, prefix="/summary", tags=["summary"]) 
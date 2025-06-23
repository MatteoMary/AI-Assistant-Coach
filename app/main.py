from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import user, metrics, training, plan, chat, strava, ai_coach, workout_context, plan_parser, auth
from app.config import settings
from app.database import init_db, recreate_tables

# Import all models to ensure tables are created
from app.models import user as user_models, metrics as metrics_models, training as training_models, strava as strava_models
from app.models.workout_context import WorkoutContext

app = FastAPI(
    title="AI Assistant Coach",
    description="An intelligent coaching platform powered by AI",
    version="1.0.0",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX + "/auth", tags=["auth"])
app.include_router(user.router, prefix=settings.API_V1_PREFIX + "/users", tags=["users"])
app.include_router(metrics.router, prefix=settings.API_V1_PREFIX)
app.include_router(training.router, prefix=settings.API_V1_PREFIX)
app.include_router(plan.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(strava.router, prefix=settings.API_V1_PREFIX + "/auth/strava")
app.include_router(ai_coach.router, prefix=settings.API_V1_PREFIX)
app.include_router(workout_context.router, prefix=settings.API_V1_PREFIX)
app.include_router(plan_parser.router, prefix=settings.API_V1_PREFIX)

@app.on_event("startup")
async def on_startup():
    recreate_tables()

@app.get("/")
async def root():
    return {"message": "Welcome to AI Assistant Coach API"} 
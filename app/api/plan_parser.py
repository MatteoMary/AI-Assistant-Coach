from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, status
from sqlmodel import Session, select
from typing import Dict, Any
import io
import base64
from PIL import Image

from app.database import get_session
from app.services.plan_parser_service import PlanParserService
from app.database.models import User
from app.schemas.plan import TrainingPlanCreate
from app.config import settings
from app.services.ml_plan_parser import MLPlanParser
from app.database.session import SessionLocal
from app.database.models import TrainingPlan
from sqlalchemy.orm import Session
from app.models.training import Training, WorkoutType, ParsedTrainingPlan

router = APIRouter(prefix="/plan-parser", tags=["plan-parser"])

# Initialize plan parser service
plan_parser = PlanParserService()

@router.post("/upload-image")
async def parse_plan_from_image(
    file: UploadFile = File(...),
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Upload an image of a training plan and parse it into structured data"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Check file size (max 10MB)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    try:
        # Read the image data
        image_data = await file.read()
        
        # Determine image format
        image_format = "jpeg"
        if file.content_type:
            if "png" in file.content_type:
                image_format = "png"
            elif "gif" in file.content_type:
                image_format = "gif"
            elif "webp" in file.content_type:
                image_format = "webp"
        
        # Validate that it's actually an image
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    # Re-save as JPEG
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="JPEG", quality=85)
                    image_data = img_buffer.getvalue()
                    image_format = "jpeg"
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Convert binary data to base64 for the parser service
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Parse the plan
        result = await plan_parser.parse_plan_from_image(base64_image, user_id, session)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@router.post("/save-parsed-plan")
async def save_parsed_plan(
    parsed_plan: dict,
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Save a parsed training plan to the training system"""
    
    try:
        result = await plan_parser.save_parsed_plan(parsed_plan, user_id, session)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving plan: {str(e)}")

@router.post("/parse-and-save")
async def parse_and_save_plan(
    plan_data: TrainingPlanCreate,
    session: Session = Depends(get_session)
):
    """Parse and save a training plan."""
    try:
        result = await plan_parser.parse_and_save_plan(plan_data, session)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/upload")
async def upload_plan(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Upload and parse a training plan image."""
    try:
        result = await plan_parser.parse_plan_image(file, session)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/preview-plan")
async def preview_parsed_plan(parsed_plan: dict) -> Dict[str, Any]:
    """Preview what a parsed plan will look like before saving"""
    
    preview = {
        "plan_title": parsed_plan.get("plan_title", "Unknown Plan"),
        "goal": parsed_plan.get("goal", ""),
        "duration_weeks": parsed_plan.get("duration_weeks", 0),
        "start_date": parsed_plan.get("start_date", ""),
        "total_workouts": 0,
        "workout_breakdown": {},
        "sample_week": None
    }
    
    # Analyze the plan structure
    for week_data in parsed_plan.get("weekly_structure", []):
        for workout in week_data.get("workouts", []):
            workout_type = workout.get("workout_type", "Unknown")
            if workout_type.lower() not in ["rest", "rest day"]:
                preview["total_workouts"] += 1
                preview["workout_breakdown"][workout_type] = preview["workout_breakdown"].get(workout_type, 0) + 1
        
        # Use first week as sample
        if not preview["sample_week"] and week_data.get("workouts"):
            preview["sample_week"] = {
                "week_number": week_data.get("week_number", 1),
                "theme": week_data.get("theme", ""),
                "workouts": week_data.get("workouts", [])
            }
    
    return preview 

@router.get("/test")
async def test_plan_parser() -> Dict[str, Any]:
    """Test if the plan parser service is working"""
    
    try:
        # Test if OpenAI client is configured
        if not plan_parser.client:
            return {
                "status": "error",
                "message": "OpenAI API key not configured",
                "openai_configured": False
            }
        
        # Test a simple API call
        test_response = await plan_parser.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Respond with exactly: {'test': 'success'}"}
            ],
            max_tokens=50,
            temperature=0
        )
        
        return {
            "status": "success",
            "message": "Plan parser service is working",
            "openai_configured": True,
            "test_response": test_response.choices[0].message.content
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Plan parser test failed: {str(e)}",
            "openai_configured": plan_parser.client is not None,
            "error_type": type(e).__name__
        } 

@router.post("/parse")
async def parse_plan(
    file: UploadFile = File(...),
    db: Session = Depends(get_session)
):
    """Parse a training plan from an uploaded image."""
    try:
        # Read the file content
        contents = await file.read()
        # Process the image and return the parsed plan
        result = await plan_parser.parse_plan_image(contents)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 

@router.get("/stored-plans")
async def get_stored_plans(
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get all stored training plans for a user"""
    try:
        from app.services.plan_storage_service import PlanStorageService
        storage_service = PlanStorageService()
        plans = storage_service.get_user_plans(user_id, session)
        
        return {
            "plans": [
                {
                    "id": plan.id,
                    "title": plan.plan_title,
                    "parsed_at": plan.parsed_at.isoformat(),
                    "confidence_score": plan.confidence_score,
                    "is_active": plan.is_active
                } for plan in plans
            ],
            "total_plans": len(plans)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plans: {str(e)}")

@router.get("/latest-plan")
async def get_latest_plan(
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get the most recent training plan for a user"""
    try:
        from app.services.plan_storage_service import PlanStorageService
        storage_service = PlanStorageService()
        latest_plan = storage_service.get_latest_plan(user_id, session)
        
        if not latest_plan:
            return {"message": "No training plans found"}
        
        plan_data = storage_service.load_parsed_data(latest_plan)
        
        return {
            "id": latest_plan.id,
            "title": latest_plan.plan_title,
            "parsed_at": latest_plan.parsed_at.isoformat(),
            "confidence_score": latest_plan.confidence_score,
            "plan_data": plan_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest plan: {str(e)}")

@router.delete("/stored-plans/{plan_id}")
async def delete_stored_plan(
    plan_id: int,
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Delete a stored training plan"""
    try:
        from app.services.plan_storage_service import PlanStorageService
        from app.models.training import ParsedTrainingPlan
        
        # Get the plan
        plan = session.get(ParsedTrainingPlan, plan_id)
        if not plan or plan.user_id != user_id:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Mark as inactive instead of deleting
        plan.is_active = False
        session.add(plan)
        session.commit()
        
        return {"message": f"Plan '{plan.plan_title}' deactivated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting plan: {str(e)}")

@router.post("/test-vision")
async def test_vision_api(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Test the OpenAI Vision API with a simple image"""
    try:
        # Read the image data
        image_data = await file.read()
        
        # Convert to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Simple vision test
        response = await plan_parser.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see in this image? Respond with just a brief description."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=100,
            temperature=0
        )
        
        return {
            "status": "success",
            "response": response.choices[0].message.content
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        } 

@router.get("/saved-plans")
async def get_saved_parsed_plans(
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get all saved parsed plans with descriptive labels for quick access"""
    
    try:
        # Get all parsed plans for the user
        plans = plan_parser.storage_service.get_user_plans(user_id, session)
        
        formatted_plans = []
        for plan in plans:
            # Generate label and statistics using helper functions
            label = plan_parser.storage_service.generate_plan_label(plan)
            stats = plan_parser.storage_service.get_plan_statistics(plan)
            
            formatted_plans.append({
                "id": plan.id,
                "label": label,
                "title": plan.plan_title,
                "parsed_date": plan.parsed_at.strftime("%B %Y"),
                "parsed_at": plan.parsed_at.isoformat(),
                "total_weeks": stats["total_weeks"],
                "total_workouts": stats["total_workouts"],
                "total_distance_km": stats["total_distance_km"],
                "confidence_score": plan.confidence_score,
                "image_hash": plan.original_image_hash[:8] + "..."  # Truncated for display
            })
        
        # Sort by most recent first
        formatted_plans.sort(key=lambda x: x["parsed_at"], reverse=True)
        
        return {
            "success": True,
            "total_plans": len(formatted_plans),
            "plans": formatted_plans
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving saved plans: {str(e)}")

@router.get("/saved-plans/{plan_id}")
async def get_saved_parsed_plan_by_id(
    plan_id: int,
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get a specific saved parsed plan by ID with full details"""
    
    try:
        # Get the specific plan
        plan = session.exec(
            select(ParsedTrainingPlan).where(
                ParsedTrainingPlan.id == plan_id,
                ParsedTrainingPlan.user_id == user_id,
                ParsedTrainingPlan.is_active == True
            )
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Load the parsed data
        plan_data = plan_parser.storage_service.load_parsed_data(plan)
        
        # Generate label and statistics using helper functions
        label = plan_parser.storage_service.generate_plan_label(plan)
        stats = plan_parser.storage_service.get_plan_statistics(plan)
        
        return {
            "success": True,
            "plan": {
                "id": plan.id,
                "label": label,
                "title": plan.plan_title,
                "parsed_date": plan.parsed_at.strftime("%B %Y"),
                "parsed_at": plan.parsed_at.isoformat(),
                "total_weeks": stats["total_weeks"],
                "total_workouts": stats["total_workouts"],
                "total_distance_km": stats["total_distance_km"],
                "confidence_score": plan.confidence_score,
                "image_hash": plan.original_image_hash,
                "weekly_structure": plan_data.get("weekly_structure", []),
                "full_parsed_data": plan_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plan: {str(e)}")

@router.delete("/saved-plans/{plan_id}")
async def delete_saved_parsed_plan(
    plan_id: int,
    user_id: int = Query(1, description="User ID for demo purposes"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Delete a saved parsed plan"""
    
    try:
        # Get the specific plan
        plan = session.exec(
            select(ParsedTrainingPlan).where(
                ParsedTrainingPlan.id == plan_id,
                ParsedTrainingPlan.user_id == user_id,
                ParsedTrainingPlan.is_active == True
            )
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Generate label for response
        label = plan_parser.storage_service.generate_plan_label(plan)
        
        # Soft delete by setting is_active to False
        plan.is_active = False
        session.commit()
        
        return {
            "success": True,
            "message": f"Plan '{label}' has been deleted",
            "deleted_plan_id": plan_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting plan: {str(e)}") 
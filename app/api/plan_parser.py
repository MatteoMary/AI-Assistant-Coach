from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from sqlmodel import Session
from typing import Dict, Any
import io
from PIL import Image

from app.database import get_session
from app.services.plan_parser_service import PlanParserService
from app.api.user import get_current_user
from app.database.models import User

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
        
        # Parse the plan
        result = await plan_parser.parse_plan_from_image(image_data, image_format)
        
        # If successful, save the plan
        if "error" not in result:
            await plan_parser.save_parsed_plan(result, user_id, session)
        
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
async def parse_and_save(
    file: UploadFile = File(...),
    db: Session = Depends(get_session)
):
    """Parse a training plan from an uploaded image and save it to the database."""
    try:
        print("\n=== Starting parse-and-save endpoint ===")
        
        # Read the file content
        print("Reading image data")
        contents = await file.read()
        print(f"Image data size: {len(contents)} bytes")
        
        # Determine image format from content type
        content_type = file.content_type
        print(f"Determining image format from content type: {content_type}")
        image_format = content_type.split('/')[-1] if content_type else 'jpeg'
        print(f"Using image format: {image_format}")
        
        # Convert to base64
        import base64
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        print("\n=== Starting plan parsing ===")
        # Parse the plan
        result = await plan_parser.parse_plan_from_image(base64_image, 1, db)  # Using user_id 1 for now
        print("Plan parsing completed")
        
        return result
        
    except Exception as e:
        print(f"Parse error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        test_response = plan_parser.client.chat.completions.create(
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Parse a training plan from an uploaded image."""
    try:
        # Read the file content
        contents = await file.read()
        
        # Convert to base64
        import base64
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # Parse the plan
        result = await plan_parser.parse_plan_from_image(base64_image, current_user.id, db)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
from app.database import get_session
from app.crud.user import create_user
from app.schemas.user import UserCreate, ExperienceLevel
from datetime import date

def create_initial_user():
    session = next(get_session())
    user_data = UserCreate(
        email="matteomary2002@icloud.com",
        password="Matteo12!",
        full_name="Matteo Mary",
        date_of_birth=date(2002, 1, 1),
        gender="Male",
        experience_years=5.0,
        training_days_per_week=4,
        experience_level=ExperienceLevel.INTERMEDIATE,
        preferred_run_time="Morning",
        long_run_day="Sunday",
        age=22,
        weight=70.0,
        height=175.0,
        fitness_level="intermediate",
        training_frequency=4
    )
    try:
        user = create_user(session, user_data)
        print(f"User created successfully: {user.email}")
    except Exception as e:
        print(f"Error creating user: {e}")

if __name__ == "__main__":
    create_initial_user() 
# AI Assistant Coach

An intelligent coaching platform that helps users track their fitness progress and generate personalized training plans using AI.

## Features

- User management and authentication
- Training metrics tracking
- AI-powered training plan generation
- Fatigue monitoring and management
- Interactive dashboard for progress visualization

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
./run.sh
```

## Project Structure

- `app/`: Main FastAPI application
  - `models/`: SQLModel ORM models
  - `schemas/`: Pydantic models for API
  - `crud/`: Database operations
  - `services/`: Business logic
  - `api/`: API endpoints
  - `utils/`: Helper functions
- `dashboard/`: Streamlit dashboard
- `tests/`: Unit and integration tests

## Development

To run tests:
```bash
pytest
```

To run the development server:
```bash
uvicorn app.main:app --reload
```

To run the dashboard:
```bash
streamlit run dashboard/app.py
```
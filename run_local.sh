#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set Python path to include current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Kill existing processes
pkill -f "uvicorn\|streamlit" || true

# Start the FastAPI server in background
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start the Streamlit dashboard
echo "Starting Streamlit dashboard..."
streamlit run app/frontend/main.py --server.port 8501 &
FRONTEND_PID=$!

echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:8501"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    pkill -f "uvicorn\|streamlit" || true
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Wait for user input to keep script running
echo "Press Ctrl+C to stop both services"
wait 
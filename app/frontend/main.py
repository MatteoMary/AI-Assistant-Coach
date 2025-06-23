import streamlit as st
import requests
import plotly.express as px
import pandas as pd
import json
from datetime import datetime, timedelta
from PIL import Image
import base64
from io import BytesIO
import streamlit.components.v1 as components
import time
import os

# Configure the page
st.set_page_config(
    page_title="AI Running Coach",
    page_icon="🏃",
    layout="wide"
)

# API Configuration
API_URL = "http://localhost:8000/api/v1"

def load_css():
    """Load external CSS file"""
    with open('app/frontend/style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_headers():
    """Get headers for authenticated requests"""
    token = st.session_state.get('token')
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def init_session_state():
    """Initialize session state variables."""
    if "token" not in st.session_state:
        st.session_state.token = None
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_data" not in st.session_state:
        st.session_state.user_data = {}
    if "training_plan" not in st.session_state:
        st.session_state.training_plan = None
    if "profile_data" not in st.session_state:
        st.session_state.profile_data = {}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def check_session_cookie():
    """Check for existing session cookie and restore session if valid."""
    try:
        # Make a request to check if we have a valid session
        response = requests.get(
            f"{API_URL}/auth/session",
            timeout=5
        )
        if response.status_code == 200:
            session_data = response.json()
            if session_data.get("token"):
                # Test if the token is still valid
                test_response = requests.get(
                    f"{API_URL}/auth/me",
                    headers={"Authorization": f"Bearer {session_data['token']}"},
                    timeout=5
                )
                if test_response.status_code == 200:
                    st.session_state.token = session_data["token"]
                    st.session_state.user = test_response.json()
                    return True
    except Exception as e:
        st.debug(f"Session check error: {str(e)}")
    return False

def login():
    """Login form and authentication."""
    st.title("🏃 AI Running Coach - Login")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            # Add test credentials button
            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Login")
            with col2:
                if st.form_submit_button("🧪 Test"):
                    st.session_state.login_email = "test@example.com"
                    st.session_state.login_password = "test123"
                    st.rerun()
            
            if submitted:
                try:
                    # Use a session to maintain cookies
                    with requests.Session() as session:
                        response = session.post(
                            f"{API_URL}/auth/token",
                            data={"username": email, "password": password}
                        )
                        if response.status_code == 200:
                            token_data = response.json()
                            st.session_state.token = token_data["access_token"]
                            
                            # Get user data
                            user_response = session.get(
                                f"{API_URL}/auth/me",
                                headers={"Authorization": f"Bearer {token_data['access_token']}"}
                            )
                            if user_response.status_code == 200:
                                st.session_state.user = user_response.json()
                                st.success("Login successful!")
                                st.rerun()
                        else:
                            st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Error during login: {str(e)}")
    
    with tab2:
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="register_email")
            reg_password = st.text_input("Password", type="password", key="register_password")
            reg_name = st.text_input("Name", key="register_name")
            
            submitted = st.form_submit_button("Register")
            
            if submitted:
                try:
                    response = requests.post(
                        f"{API_URL}/auth/register",
                        json={
                            "email": reg_email,
                            "password": reg_password,
                            "name": reg_name
                        }
                    )
                    if response.status_code == 200:
                        st.success("Registration successful! Please log in.")
                        st.rerun()
                    else:
                        error_detail = response.json().get("detail", "Registration failed")
                        st.error(f"Registration failed: {error_detail}")
                except Exception as e:
                    st.error(f"Error during registration: {str(e)}")

def logout():
    """Logout and clear session state."""
    try:
        # Clear server-side session
        requests.post(f"{API_URL}/auth/logout")
    except:
        pass
    
    # Clear local session state
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.user_data = {}
    st.session_state.training_plan = None
    st.session_state.profile_data = {}
    st.session_state.chat_history = []
    
    st.rerun()

def main():
    """Main application entry point."""
    # Load CSS
    load_css()
    
    init_session_state()
    
    # Check for URL parameters for success messages
    params = st.query_params
    
    if "strava_success" in params:
        st.success("🎉 Successfully connected to Strava! Your account is now linked.")
        # Clear the parameter
        st.query_params.clear()
    
    if "strava_error" in params:
        error_msg = params["strava_error"]
        st.error(f"❌ Failed to connect to Strava: {error_msg}")
        # Clear the parameter
        st.query_params.clear()
    
    # FOR TESTING: Set default user data
    if "user" not in st.session_state:
        st.session_state.user = {
            "name": "Test User",
            "email": "test@example.com"
        }
    
    # Main application interface
    st.title("🏃 AI Running Coach")
    
    # User info in sidebar
    user_name = st.session_state.user.get('name', 'User') if st.session_state.user else 'User'
    user_email = st.session_state.user.get('email', 'N/A') if st.session_state.user else 'N/A'
    
    st.sidebar.markdown(f"**Welcome, {user_name}!**")
    st.sidebar.markdown(f"Email: {user_email}")
    
    # COMMENTED OUT FOR TESTING - REMOVE COMMENTS TO RE-ENABLE LOGOUT
    # if st.sidebar.button("🚪 Logout"):
    #     logout()
    #     return
    
    # Navigation buttons
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Navigation**")
    
    if st.sidebar.button("📊 Dashboard"):
        st.session_state.current_page = "Dashboard"
        st.rerun()
    if st.sidebar.button("👤 Profile"):
        st.session_state.current_page = "Profile"
        st.rerun()
    if st.sidebar.button("📋 Training Plan"):
        st.session_state.current_page = "Training Plan"
        st.rerun()
    if st.sidebar.button("🤖 Chat with AI Coach"):
        st.session_state.current_page = "Chat with AI Coach"
        st.rerun()
    if st.sidebar.button("💪 Workout Context"):
        st.session_state.current_page = "Workout Context"
        st.rerun()
    if st.sidebar.button("🏃 Strava"):
        st.session_state.current_page = "Strava"
        st.rerun()
    if st.sidebar.button("⚙️ Settings"):
        st.session_state.current_page = "Settings"
        st.rerun()
    
    # Initialize current page if not set
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    # Route to appropriate page
    if st.session_state.current_page == "Dashboard":
        show_dashboard()
    elif st.session_state.current_page == "Profile":
        show_profile()
    elif st.session_state.current_page == "Training Plan":
        show_training_plan()
    elif st.session_state.current_page == "Chat with AI Coach":
        show_chat()
    elif st.session_state.current_page == "Workout Context":
        show_workout_context()
    elif st.session_state.current_page == "Strava":
        show_strava()
    elif st.session_state.current_page == "Settings":
        show_settings()

def load_profile_data():
    """Load user profile data from API"""
    try:
        response = requests.get(f"{API_URL}/users/profile", timeout=5)
        if response.status_code == 200:
            st.session_state.profile_data = response.json()
        else:
            st.error(f"Failed to load profile: {response.text}")
    except Exception as e:
        st.error(f"Error loading profile data: {str(e)}")

def load_training_plan():
    """Load training plan data from API"""
    try:
        response = requests.get(f"{API_URL}/training?user_id=1", timeout=10)
        if response.status_code == 200:
            trainings = response.json()
            # Filter for planned/coach-generated workouts
            plan_workouts = [t for t in trainings if t.get('plan_source') in ['coach_photo', 'ai_generated']]
        else:
            plan_workouts = []
    except Exception as e:
        st.error(f"Error loading training plan: {str(e)}")
        plan_workouts = []
    
    return plan_workouts

def show_daily_log():
    st.header("Daily Training Log")
    
    # Date Selection
    log_date = st.date_input("Date", datetime.now())
    
    # Morning Metrics
    st.subheader("Morning Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input("Resting Heart Rate", min_value=30, max_value=100, value=55)
    with col2:
        st.number_input("HRV Score", min_value=0, max_value=100, value=65)
    with col3:
        st.number_input("Sleep Hours", min_value=0.0, max_value=12.0, value=7.5, step=0.5)
    
    # Subjective Feelings
    st.subheader("How are you feeling?")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Fatigue Level", 1, 10, 5)
        st.slider("Motivation Level", 1, 10, 7)
    with col2:
        st.slider("Stress Level", 1, 10, 4)
        st.slider("Soreness Level", 1, 10, 3)
    
    # Workout Completion
    st.subheader("Workout Completion")
    completed = st.checkbox("Workout Completed")
    if completed:
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Distance (km)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
            st.number_input("Duration (minutes)", min_value=0, max_value=300, value=60)
        with col2:
            st.number_input("Average Heart Rate", min_value=0, max_value=200, value=145)
            st.slider("Perceived Effort", 1, 10, 6)
    
    st.text_area("Notes", "How did the session feel?")
    if st.button("Save Daily Log"):
        st.success("Daily log saved successfully!")

def show_progress():
    """Show progress metrics and charts."""
    st.header("Progress")
    
    # Get metrics data
    try:
        response = requests.get(f"{API_URL}/metrics?user_id=1", timeout=5)
        if response.status_code == 200:
            metrics_data = response.json()
            
            # Convert to DataFrame for easier plotting
            df = pd.DataFrame(metrics_data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Filter last 2 weeks
            two_weeks_ago = pd.Timestamp.now() - pd.Timedelta(days=14)
            df = df[df['date'] >= two_weeks_ago]
            
            if not df.empty:
                st.subheader("📈 Your Training Metrics (Last 2 Weeks)")
                
                # Create tabs for different metrics
                tab1, tab2, tab3 = st.tabs(["Distance", "Pace", "Heart Rate"])
                
                with tab1:
                    # Distance chart
                    fig = px.line(df, x='date', y='distance',
                                title='Distance Over Time',
                                labels={'distance': 'Distance (km)', 'date': 'Date'})
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    # Pace chart
                    fig = px.line(df, x='date', y='pace',
                                title='Pace Over Time',
                                labels={'pace': 'Pace (min/km)', 'date': 'Date'})
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab3:
                    # Heart rate chart
                    fig = px.line(df, x='date', y='heart_rate',
                                title='Heart Rate Over Time',
                                labels={'heart_rate': 'Heart Rate (bpm)', 'date': 'Date'})
                    st.plotly_chart(fig, use_container_width=True)
                
                # Summary statistics
                st.subheader("📊 Summary Statistics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Distance", f"{df['distance'].sum():.1f} km")
                with col2:
                    st.metric("Average Pace", f"{df['pace'].mean():.1f} min/km")
                with col3:
                    st.metric("Average Heart Rate", f"{df['heart_rate'].mean():.0f} bpm")
            else:
                st.info("No metrics data available for the last 2 weeks.")
        else:
            st.error(f"Failed to load metrics: {response.text}")
    except Exception as e:
        st.error(f"Error loading metrics: {str(e)}")

def show_profile():
    st.header("Runner Profile")
    
    # Basic Information
    st.subheader("Personal Information")
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", value=st.session_state.profile_data.get('name', ''))
            age = st.number_input("Age", min_value=16, max_value=100, value=st.session_state.profile_data.get('age', 35))
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(st.session_state.profile_data.get('gender', 'Male')))
        with col2:
            experience = st.number_input("Running Experience (years)", min_value=0, max_value=50, value=st.session_state.profile_data.get('experience', 5))
            training_days = st.number_input("Weekly Training Days", min_value=1, max_value=7, value=st.session_state.profile_data.get('training_days', 5))
            level = st.selectbox("Experience Level", ["Beginner", "Intermediate", "Advanced", "Elite"], 
                               index=["Beginner", "Intermediate", "Advanced", "Elite"].index(st.session_state.profile_data.get('level', 'Intermediate')))
        
        # Training Preferences
        st.subheader("Training Preferences")
        col1, col2 = st.columns(2)
        with col1:
            run_time = st.selectbox("Preferred Run Time", ["Morning", "Afternoon", "Evening"], 
                                  index=["Morning", "Afternoon", "Evening"].index(st.session_state.profile_data.get('run_time', 'Morning')))
            long_run_day = st.selectbox("Long Run Day", ["Saturday", "Sunday"], 
                                      index=["Saturday", "Sunday"].index(st.session_state.profile_data.get('long_run_day', 'Sunday')))
        with col2:
            max_distance = st.number_input("Max Weekly Distance (km)", min_value=20, max_value=200, 
                                         value=st.session_state.profile_data.get('max_distance', 60))
            target_sessions = st.number_input("Target Weekly Sessions", min_value=1, max_value=14, 
                                            value=st.session_state.profile_data.get('target_sessions', 5))
        
        # Race Goals
        st.subheader("Race Goals")
        col1, col2 = st.columns(2)
        with col1:
            race_date = st.date_input("Target Race Date", 
                                    value=datetime.fromisoformat(st.session_state.profile_data.get('race_date', (datetime.now() + timedelta(days=90)).isoformat())))
            race_distance = st.selectbox("Target Race Distance", ["5K", "10K", "Half Marathon", "Marathon"], 
                                       index=["5K", "10K", "Half Marathon", "Marathon"].index(st.session_state.profile_data.get('race_distance', 'Marathon')))
        with col2:
            race_time = st.text_input("Target Race Time", value=st.session_state.profile_data.get('race_time', '3:30:00'))
            race_name = st.text_input("Target Race Name", value=st.session_state.profile_data.get('race_name', 'City Marathon'))
        
        submitted = st.form_submit_button("Save Profile")
        if submitted:
            profile_data = {
                'name': name,
                'age': age,
                'gender': gender,
                'experience': experience,
                'training_days': training_days,
                'level': level,
                'run_time': run_time,
                'long_run_day': long_run_day,
                'max_distance': max_distance,
                'target_sessions': target_sessions,
                'race_date': race_date.isoformat(),
                'race_distance': race_distance,
                'race_time': race_time,
                'race_name': race_name
            }
            
            if save_profile_data(profile_data):
                st.success("Profile updated successfully!")
                st.rerun()

def show_strava():
    st.header("Strava Integration")
    
    # Check Strava connection status without authentication for testing
    try:
        # FOR TESTING: Use test endpoints without authentication
        # strava_response = requests.get(f"{API_URL}/auth/strava/connection/status", headers=get_headers(), timeout=5)
        strava_response = requests.get(f"{API_URL}/auth/strava/test/connection/status", timeout=5)
        if strava_response.status_code == 200 and strava_response.json().get("connected"):
            st.success("✅ Strava connected!")
            
            # Show disconnect button
            if st.button("🔌 Disconnect Strava"):
                try:
                    # disconnect_response = requests.post(f"{API_URL}/auth/strava/disconnect", headers=get_headers(), timeout=5)
                    disconnect_response = requests.post(f"{API_URL}/auth/strava/test/disconnect", timeout=5)
                    if disconnect_response.status_code == 200:
                        st.success("✅ Strava disconnected!")
                        st.rerun()
                    else:
                        st.error("Failed to disconnect Strava")
                except Exception as e:
                    st.error(f"Error disconnecting: {e}")
            
            # Show recent activities
            st.subheader("Recent Activities")
            
            # Initialize session state for activities count
            if 'num_activities' not in st.session_state:
                st.session_state.num_activities = 10
            
            # Add controls for number of activities
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("5 Activities"):
                    st.session_state.num_activities = 5
                    st.rerun()
            with col2:
                if st.button("10 Activities"):
                    st.session_state.num_activities = 10
                    st.rerun()
            with col3:
                if st.button("20 Activities"):
                    st.session_state.num_activities = 20
                    st.rerun()
            
            try:
                # activities_response = requests.get(f"{API_URL}/auth/strava/activities", headers=get_headers(), params={"limit": st.session_state.num_activities}, timeout=10)
                activities_response = requests.get(f"{API_URL}/auth/strava/test/activities", params={"limit": st.session_state.num_activities}, timeout=10)
                if activities_response.status_code == 200:
                    activities = activities_response.json()
                    if activities:
                        st.write(f"Showing **{len(activities)}** recent activities:")
                        
                        for activity in activities:
                            # Format the date nicely
                            start_date = activity.get('start_date', '')
                            formatted_date = "Unknown Date"
                            if start_date:
                                try:
                                    from datetime import datetime
                                    # Parse ISO date and format it nicely
                                    date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                                    formatted_date = date_obj.strftime('%B %d, %Y at %I:%M %p')  # e.g., "January 15, 2024 at 7:00 AM"
                                except:
                                    # Fallback to just the date part if parsing fails
                                    formatted_date = start_date[:10]  # Just show YYYY-MM-DD
                            
                            # Display activity in an expander with key metrics
                            with st.expander(f"🏃 {activity.get('name', 'Unknown Activity')} - {formatted_date}"):
                                # First row - Most important metrics (larger)
                                st.markdown("### **Key Metrics**")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    # Distance (convert meters to km)
                                    distance_m = activity.get('distance', 0)
                                    distance_km = distance_m / 1000
                                    st.markdown(f"""
                                    <div class="metric-container">
                                        <div class="metric-label">Distance</div>
                                        <div class="metric-value">{distance_km:.1f} km</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col2:
                                    # Average speed (convert m/s to km/h) and calculate pace
                                    avg_speed = activity.get('average_speed')
                                    if avg_speed and avg_speed > 0:
                                        speed_kmh = avg_speed * 3.6  # m/s to km/h
                                        pace_min_per_km = 1000 / (avg_speed * 60)  # min/km
                                        # Convert to minutes:seconds format
                                        minutes = int(pace_min_per_km)
                                        seconds = int((pace_min_per_km - minutes) * 60)
                                        pace_str = f"{minutes}:{seconds:02d} min/km"
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Pace</div>
                                            <div class="metric-value">{pace_str}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Pace</div>
                                            <div class="metric-value">N/A</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                with col3:
                                    # Moving time (convert seconds to minutes)
                                    moving_time_s = activity.get('moving_time', 0)
                                    moving_time_min = moving_time_s / 60
                                    st.markdown(f"""
                                    <div class="metric-container">
                                        <div class="metric-label">Time</div>
                                        <div class="metric-value">{moving_time_min:.0f} min</div>
                                    </div>
                                    """, unsafe_allow_html=True)

                                # Centered block for Avg HR, Max HR, Cadence, Max Speed
                                st.markdown('<div class="metrics-center-block">', unsafe_allow_html=True)
                                
                                # First row: Avg HR, Max HR
                                col_hr1, col_hr2 = st.columns(2)
                                with col_hr1:
                                    avg_hr = activity.get('average_heartrate')
                                    if avg_hr:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Avg HR</div>
                                            <div class="metric-value">{avg_hr:.0f} bpm</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Avg HR</div>
                                            <div class="metric-value">N/A</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                with col_hr2:
                                    max_hr = activity.get('max_heartrate')
                                    if max_hr:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Max HR</div>
                                            <div class="metric-value">{max_hr:.0f} bpm</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Max HR</div>
                                            <div class="metric-value">N/A</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                # Second row: Cadence, Max Speed
                                col_cad1, col_cad2 = st.columns(2)
                                with col_cad1:
                                    avg_cadence = activity.get('average_cadence')
                                    if avg_cadence:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Cadence</div>
                                            <div class="metric-value">{avg_cadence:.0f} spm</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Cadence</div>
                                            <div class="metric-value">N/A</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                with col_cad2:
                                    # Max speed converted to max pace
                                    max_speed = activity.get('max_speed')
                                    if max_speed and max_speed > 0:
                                        # Calculate max pace (same method as average pace)
                                        max_pace_min_per_km = 1000 / (max_speed * 60)  # min/km
                                        # Convert to minutes:seconds format
                                        minutes = int(max_pace_min_per_km)
                                        seconds = int((max_pace_min_per_km - minutes) * 60)
                                        max_pace_str = f"{minutes}:{seconds:02d} min/km"
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Max Pace</div>
                                            <div class="metric-value">{max_pace_str}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div class="metric-container">
                                            <div class="metric-label">Max Pace</div>
                                            <div class="metric-value">N/A</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)

                                # Additional info
                                st.markdown("---")
                                
                                # Activity type and elevation
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Type:** {activity.get('type', 'Unknown')}")
                                with col2:
                                    elevation = activity.get('total_elevation_gain')
                                    if elevation:
                                        st.write(f"**Elevation:** {elevation:.0f} m")
                                    else:
                                        st.write("**Elevation:** N/A")
                                
                                # Location info if available
                                location_parts = []
                                if activity.get('location_city'):
                                    location_parts.append(activity['location_city'])
                                if activity.get('location_state'):
                                    location_parts.append(activity['location_state'])
                                if activity.get('location_country'):
                                    location_parts.append(activity['location_country'])
                                
                                if location_parts:
                                    st.write(f"**Location:** {', '.join(location_parts)}")
                                
                                # Description if available
                                if activity.get('description'):
                                    st.write(f"**Description:** {activity.get('description')}")
                                
                                # Route/map info if available
                                if activity.get('map') and activity['map'].get('summary_polyline'):
                                    st.write("**Route:** Map data available")
                    else:
                        st.info("No recent activities found")
                else:
                    st.error("Failed to load activities")
            except Exception as e:
                st.error(f"Error loading activities: {e}")
        else:
            st.info("ℹ️ Connect your Strava account to sync your activities")
            
            # Show connect button
            if st.button("🔗 Connect Strava"):
                try:
                    # auth_response = requests.get(f"{API_URL}/auth/strava/authorize", headers=get_headers(), timeout=5)
                    auth_response = requests.get(f"{API_URL}/auth/strava/test/authorize", timeout=5)
                    if auth_response.status_code == 200:
                        auth_url = auth_response.json().get("url")
                        if auth_url:
                            st.markdown(f"[Click here to connect your Strava account]({auth_url})")
                        else:
                            st.error("No authorization URL received")
                    else:
                        st.error("Failed to get authorization URL")
                except Exception as e:
                    st.error(f"Error getting authorization URL: {e}")
    except Exception as e:
        st.error(f"Error checking Strava connection: {e}")
        st.info("ℹ️ Connect your Strava account to sync your activities")
        
        # Show connect button
        if st.button("🔗 Connect Strava"):
            try:
                # auth_response = requests.get(f"{API_URL}/auth/strava/authorize", headers=get_headers(), timeout=5)
                auth_response = requests.get(f"{API_URL}/auth/strava/test/authorize", timeout=5)
                if auth_response.status_code == 200:
                    auth_url = auth_response.json().get("url")
                    if auth_url:
                        st.markdown(f"[Click here to connect your Strava account]({auth_url})")
                    else:
                        st.error("No authorization URL received")
                else:
                    st.error("Failed to get authorization URL")
            except Exception as e:
                st.error(f"Error getting authorization URL: {e}")

def show_coach_chat():
    """Show the coach chat interface - alias for show_chat()"""
    show_chat()

def show_chat():
    st.header("🤖 AI Running Coach Chat")
    
    # Show status information
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💬 **Chat with your AI coach!** I can analyze your Strava data and provide personalized training advice.")
    with col2:
        # Check if AI is configured
        try:
            test_response = requests.get(f"{API_URL}/ai-coach/quick-insights", timeout=5)
            if test_response.status_code == 200:
                data = test_response.json()
                if "error" not in data:
                    st.success("🟢 AI Active")
                else:
                    st.warning("🟡 No Data")
            else:
                st.error("🔴 AI Offline")
        except:
            st.error("🔴 AI Offline")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your AI running coach. I've analyzed your Strava activities and I'm ready to help you improve your training. What would you like to know about your running?"}
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Plan Photo Upload Section
    st.subheader("📷 Upload Training Plan Photo")
    with st.expander("📋 **Upload Your Coach's Training Plan**", expanded=False):
        st.write("Take a photo of your coach's training plan and I'll help you import it into your digital training system!")
        
        uploaded_file = st.file_uploader(
            "Choose a photo of your training plan",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo of your training plan. Works best with printed plans, handwritten notes, or screenshots."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            parse_only = st.button("🔍 Parse Plan Only", type="secondary", disabled=not uploaded_file)
        with col2:
            parse_and_save = st.button("💾 Parse & Save to Training Plan", type="primary", disabled=not uploaded_file)
        
        if uploaded_file and (parse_only or parse_and_save):
            with st.spinner("🤖 Reading your training plan..."):
                try:
                    # Prepare the file for upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    
                    # Send the request to the correct endpoint
                    response = requests.post(
                        f"{API_URL}/plan-parser/upload-image",
                        files=files,
                        params={"user_id": 1}
                    )
                    print(f"Debug: Upload response status: {response.status_code}")
                    print(f"Debug: Upload response text: {response.text}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Plan parsed successfully!")
                        # Store the result in session state and redirect
                        st.session_state.parsed_plan = result
                        st.session_state.active_page = "Training Plan"
                        st.rerun()
                    else:
                        st.error(f"Error processing image: {response.text}")
                except Exception as e:
                    st.error(f"Error processing image: {str(e)}")
                    print(f"Debug: Upload error: {str(e)}")
    
    # Chat input
    if prompt := st.chat_input("Ask your AI coach about your training..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your data..."):
                try:
                    response = requests.post(
                        f"{API_URL}/chat/message",
                        json={"message": prompt},
                        timeout=15
                    )
                    if response.status_code == 200:
                        ai_response = response.json()["message"]
                        st.markdown(ai_response)
                        # Add AI response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    else:
                        error_detail = response.json().get("detail", "Unknown error")
                        error_msg = f"I'm having trouble right now. Error: {error_detail}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"I'm having trouble connecting. Please make sure the backend is running. Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Enhanced Quick Prompts
    st.sidebar.markdown("### 🚀 Quick Questions")
    
    if st.sidebar.button("📊 Analyze my recent training"):
        prompt = "Can you analyze my recent running activities and tell me how I'm doing?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    if st.sidebar.button("🎯 What should I focus on?"):
        prompt = "Based on my recent activities, what areas should I focus on improving?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    if st.sidebar.button("🏃 Pace analysis"):
        prompt = "How consistent is my running pace and what does it tell you about my training?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    if st.sidebar.button("📈 Training trends"):
        prompt = "What trends do you see in my training volume and frequency?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    if st.sidebar.button("💡 Training recommendations"):
        prompt = "What specific recommendations do you have for my next week of training?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    if st.sidebar.button("📋 Review my training plan"):
        prompt = "Can you review my current training plan and see how it aligns with my recent activities?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    if st.sidebar.button("📷 How to photograph plans"):
        prompt = "How should I take a photo of my coach's training plan for the best results?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    
    # Clear chat option
    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your AI running coach. I've analyzed your Strava activities and I'm ready to help you improve your training. What would you like to know about your running?"}
        ]
        st.rerun()

def show_workout_context():
    st.header("💪 Enhanced Workout Context")
    st.info("Add detailed context to your Strava activities for better AI coaching insights!")
    
    # Get user's recent activities
    try:
        activities_response = requests.get(f"{API_URL}/strava/activities?limit=20", timeout=5)
        if activities_response.status_code == 200:
            activities = activities_response.json()
        else:
            st.error("Failed to load activities")
            return
    except:
        st.error("Cannot connect to backend")
        return
    
    if not activities:
        st.warning("No activities found. Import your Strava activities first!")
        return
    
    # Activity selection
    st.subheader("📋 Select Activity to Enhance")
    
    activity_options = {}
    for activity in activities:
        date_str = activity['start_date'][:10] if 'start_date' in activity else "Unknown date"
        label = f"{activity['name']} - {date_str} ({activity['distance_km']:.2f} km)"
        activity_options[label] = activity
    
    selected_label = st.selectbox("Choose an activity:", list(activity_options.keys()))
    selected_activity = activity_options[selected_label]
    
    # Check if context already exists
    existing_context = None
    try:
        context_response = requests.get(f"{API_URL}/workout-context/{selected_activity['strava_id']}", timeout=5)
        if context_response.status_code == 200:
            existing_context = context_response.json()
    except:
        pass  # No existing context
    
    st.subheader("🏃 Workout Details")
    
    # Basic workout info
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Activity:** {selected_activity['name']}")
        st.write(f"**Distance:** {selected_activity['distance_km']:.2f} km")
        st.write(f"**Duration:** {selected_activity['duration']}")
    with col2:
        st.write(f"**Pace:** {selected_activity.get('pace_per_km', 'N/A')}")
        st.write(f"**HR:** {selected_activity.get('average_heartrate', 'N/A')} bpm")
        st.write(f"**Elevation:** {selected_activity.get('total_elevation_gain', 'N/A')} m")
    
    # Enhanced context form
    st.subheader("🔥 Add Enhanced Context")
    
    with st.form("workout_context_form"):
        # Workout classification
        col1, col2 = st.columns(2)
        
        with col1:
            workout_types = ["Easy Run", "Tempo Run", "Intervals", "Fartlek", "Long Run", 
                           "Recovery Run", "Threshold Run", "Track Workout", "Hill Repeats", 
                           "Race", "Time Trial", "Progression Run"]
            workout_type = st.selectbox(
                "Workout Type*", 
                workout_types,
                index=workout_types.index(existing_context.get('workout_type', 'Easy Run')) if existing_context and existing_context.get('workout_type') in workout_types else 0
            )
            
            terrain_types = ["Road", "Track", "Trail", "Treadmill", "Mixed"]
            terrain = st.selectbox(
                "Terrain", 
                terrain_types,
                index=terrain_types.index(existing_context.get('terrain', 'Road')) if existing_context and existing_context.get('terrain') in terrain_types else 0
            )
        
        with col2:
            weather_conditions = ["Perfect", "Hot", "Cold", "Windy", "Rainy", "Humid", "Snowy"]
            weather = st.selectbox(
                "Weather", 
                weather_conditions,
                index=weather_conditions.index(existing_context.get('weather', 'Perfect')) if existing_context and existing_context.get('weather') in weather_conditions else 0
            )
            
            temperature = st.number_input(
                "Temperature (°C)", 
                min_value=-30.0, max_value=50.0, value=existing_context.get('temperature', 20.0) if existing_context else 20.0, step=0.5
            )
        
        # Interval details
        if workout_type in ["Intervals", "Track Workout", "Fartlek"]:
            st.subheader("⏱️ Interval Details")
            
            # Number of intervals
            num_intervals = st.number_input("Number of intervals", min_value=1, max_value=20, value=5)
            
            intervals_data = []
            for i in range(num_intervals):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    distance = st.text_input(f"Rep {i+1} Distance", value="400m", key=f"dist_{i}")
                with col2:
                    time = st.text_input(f"Rep {i+1} Time", value="1:30", key=f"time_{i}")
                with col3:
                    rest = st.text_input(f"Rep {i+1} Rest", value="90s", key=f"rest_{i}")
                with col4:
                    hr_avg = st.number_input(f"Rep {i+1} HR", min_value=100, max_value=220, value=180, key=f"hr_{i}")
                
                intervals_data.append({
                    "distance": distance,
                    "time": time,
                    "rest": rest,
                    "hr_avg": hr_avg
                })
        
        # Performance metrics
        st.subheader("📊 Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if workout_type in ["Intervals", "Track Workout", "Fartlek"]:
                avg_hr_work = st.number_input(
                    "Avg HR (work intervals)", 
                    min_value=100, max_value=220, 
                    value=existing_context.get('avg_hr_work_intervals', 170) if existing_context else 170
                )
            else:
                avg_hr_work = None
            
            max_hr = st.number_input(
                "Max HR (session)", 
                min_value=120, max_value=220, 
                value=existing_context.get('max_hr_session', 185) if existing_context else 185
            )
        
        with col2:
            lactate = st.number_input(
                "Lactate (mmol/L)", 
                min_value=0.0, max_value=25.0, 
                value=existing_context.get('lactate_measurement', 0.0) if existing_context else 0.0, 
                step=0.1,
                help="Leave at 0 if not measured"
            )
            
            if workout_type in ["Intervals", "Track Workout", "Tempo Run"]:
                rpe_work = st.slider(
                    "RPE (work/hard efforts)", 
                    1, 10, 
                    existing_context.get('rpe_work_intervals', 7) if existing_context else 7
                )
            else:
                rpe_work = None
        
        with col3:
            rpe_overall = st.slider(
                "RPE (overall session)", 
                1, 10, 
                existing_context.get('rpe_overall', 6) if existing_context else 6
            )
            
            target_pace = st.text_input(
                "Target pace (e.g., 4:00/km)", 
                value=existing_context.get('target_pace', '') if existing_context else ''
            )
        
        # Subjective metrics
        st.subheader("🧠 How It Felt")
        
        col1, col2 = st.columns(2)
        with col1:
            energy_pre = st.slider(
                "Energy level (pre-workout)", 
                1, 10, 
                existing_context.get('energy_level_pre', 7) if existing_context else 7
            )
            
            energy_post = st.slider(
                "Energy level (post-workout)", 
                1, 10, 
                existing_context.get('energy_level_post', 6) if existing_context else 6
            )
            
            motivation = st.slider(
                "Motivation level", 
                1, 10, 
                existing_context.get('motivation', 7) if existing_context else 7
            )
        
        with col2:
            sleep_quality = st.slider(
                "Sleep quality (previous night)", 
                1, 10, 
                existing_context.get('sleep_quality_previous_night', 7) if existing_context else 7
            )
            
            soreness_pre = st.slider(
                "Soreness (pre-workout)", 
                1, 10, 
                existing_context.get('soreness_pre', 3) if existing_context else 3
            )
            
            soreness_post = st.slider(
                "Soreness (post-workout)", 
                1, 10, 
                existing_context.get('soreness_post', 4) if existing_context else 4
            )
        
        # Goal achievement
        goal_achieved = st.checkbox(
            "Goal achieved", 
            value=existing_context.get('goal_achieved', False) if existing_context else False
        )
        
        # Notes
        st.subheader("📝 Notes")
        workout_description = st.text_area(
            "Workout description", 
            value=existing_context.get('workout_description', '') if existing_context else '',
            help="Describe the workout plan, targets, conditions"
        )
        
        how_it_felt = st.text_area(
            "How it felt", 
            value=existing_context.get('how_it_felt', '') if existing_context else '',
            help="Describe how the workout felt, any challenges, wins"
        )
        
        coaching_notes = st.text_area(
            "Coaching notes", 
            value=existing_context.get('coaching_notes', '') if existing_context else '',
            help="Notes for future training, adjustments needed"
        )
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Enhanced Context", type="primary")
        
        if submitted:
            # Prepare data for API
            context_data = {
                "strava_activity_id": selected_activity['strava_id'],
                "workout_type": workout_type,
                "terrain": terrain,
                "weather": weather,
                "temperature": temperature,
                "avg_hr_work_intervals": avg_hr_work,
                "max_hr_session": max_hr,
                "lactate_measurement": lactate if lactate > 0 else None,
                "rpe_work_intervals": rpe_work,
                "rpe_overall": rpe_overall,
                "target_pace": target_pace if target_pace else None,
                "energy_level_pre": energy_pre,
                "energy_level_post": energy_post,
                "motivation": motivation,
                "sleep_quality_previous_night": sleep_quality,
                "soreness_pre": soreness_pre,
                "soreness_post": soreness_post,
                "goal_achieved": goal_achieved,
                "workout_description": workout_description if workout_description else None,
                "how_it_felt": how_it_felt if how_it_felt else None,
                "coaching_notes": coaching_notes if coaching_notes else None
            }
            
            # Add intervals data if applicable
            if workout_type in ["Intervals", "Track Workout", "Fartlek"]:
                context_data["intervals_data"] = json.dumps(intervals_data)
            
            # Remove None values
            context_data = {k: v for k, v in context_data.items() if v is not None}
            
            try:
                response = requests.post(f"{API_URL}/workout-context/", json=context_data, timeout=10)
                if response.status_code == 200:
                    st.success("✅ Enhanced context saved successfully!")
                    st.info("Your AI coach will now have much better insights into this workout!")
                else:
                    st.error(f"Failed to save context: {response.text}")
            except Exception as e:
                st.error(f"Error saving context: {str(e)}")
    
    # Show interval analytics if available
    st.subheader("📈 Your Interval Training Analytics")
    try:
        analytics_response = requests.get(f"{API_URL}/workout-context/analytics/intervals", timeout=5)
        if analytics_response.status_code == 200:
            analytics = analytics_response.json()
            
            if analytics['total_interval_sessions'] > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Interval Sessions", analytics['total_interval_sessions'])
                with col2:
                    st.metric("Avg Work HR", f"{analytics['avg_work_hr']} bpm" if analytics['avg_work_hr'] else "N/A")
                with col3:
                    st.metric("Avg Lactate", f"{analytics['avg_lactate']} mmol/L" if analytics['avg_lactate'] else "N/A")
                
                if analytics['pace_progression']:
                    st.subheader("🏃 Pace Progression")
                    pace_df = pd.DataFrame(analytics['pace_progression'])
                    st.dataframe(pace_df)
            else:
                st.info("Add context to interval workouts to see analytics here!")
    except:
        pass

def show_training_plan():
    st.header("Training Plan")
    
    # Check if we have a newly parsed plan
    if "parsed_plan" in st.session_state:
        plan = st.session_state.parsed_plan
        st.success("✅ New training plan loaded!")
        
        # Display plan title and duration
        st.subheader(plan["title"])
        st.write(f"Duration: {plan['duration_weeks']} weeks")
        
        # Display weekly structure
        st.subheader("Weekly Structure")
        for week in plan["weekly_structure"]:
            st.markdown(f"### Week {week['week_number']} - Total Distance: {week['total_distance']:.1f} km")
            
            # Create a DataFrame for the table
            table_data = {
                "Day": [],
                "Workout": [],
                "Distance (km)": []
            }
            
            for workout in week["workouts"]:
                table_data["Day"].append(workout["day"])
                table_data["Workout"].append(workout["description"])
                table_data["Distance (km)"].append(f"{workout['distance']:.1f}")
            
            # Display as a table
            st.table(pd.DataFrame(table_data))
            st.markdown("---")
        
        # Clear the parsed plan from session state
        del st.session_state.parsed_plan
        return
    
    # Fetch actual training data from the database
    try:
        response = requests.get(f"{API_URL}/training?user_id=1", timeout=10)
        if response.status_code == 200:
            trainings = response.json()
            # Filter for planned/coach-generated workouts
            plan_workouts = [t for t in trainings if t.get('plan_source') in ['coach_photo', 'ai_generated']]
        else:
            plan_workouts = []
    except Exception as e:
        st.error(f"Error loading training plan: {str(e)}")
        plan_workouts = []
    
    if not plan_workouts:
        # No plan uploaded yet
        st.info("🚀 **No training plan loaded yet!**")
        st.write("Upload a training plan photo in the Coach Chat page to see your dynamic plan here.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📷 Upload Training Plan", type="primary", key="training_plan_upload_primary"):
                st.info("💡 **Go to 'Coach Chat' page** (in the sidebar) to upload a training plan photo!")
        with col2:
            if st.button("🤖 Generate AI Plan", type="secondary", key="training_plan_generate_ai"):
                with st.spinner("Generating personalized training plan..."):
                    try:
                        generate_response = requests.post(f"{API_URL}/ai-coach/generate-plan", 
                                                        json={"user_id": 1, "weeks": 4}, timeout=30)
                        if generate_response.status_code == 200:
                            st.success("✅ AI training plan generated!")
                            st.rerun()
                        else:
                            st.error("Failed to generate AI plan")
                    except Exception as e:
                        st.error(f"Error generating plan: {e}")
        return
    
    # Plan exists - show dynamic content
    plan_source = plan_workouts[0].get('plan_source', 'unknown')
    plan_title = plan_workouts[0].get('plan_title', 'Training Plan')
    
    # Plan Overview
    st.subheader(f"📊 Current Plan: {plan_title}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Workouts", len(plan_workouts))
    with col2:
        source_emoji = "📷" if plan_source == "coach_photo" else "🤖"
        st.metric("Source", f"{source_emoji} {plan_source.replace('_', ' ').title()}")
    with col3:
        # Calculate date range
        dates = [datetime.fromisoformat(t['date']) for t in plan_workouts]
        if dates:
            duration_days = (max(dates) - min(dates)).days
            duration_weeks = duration_days // 7 + 1
            st.metric("Duration", f"{duration_weeks} weeks")
    
    # AI Analysis & Recommendations
    st.subheader("🤖 AI Plan Analysis")
    
    # Get AI analysis of the current plan
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🔍 Analyze Plan with AI", type="secondary", key="training_plan_analyze_ai"):
            with st.spinner("AI analyzing your training plan..."):
                try:
                    # Fetch the parsed plan data
                    plan_response = requests.get(f"{API_URL}/training?user_id=1", timeout=10)
                    if plan_response.status_code == 200:
                        plan_workouts = plan_response.json()
                        # Filter for planned/coach-generated workouts
                        plan_workouts = [t for t in plan_workouts if t.get('plan_source') in ['coach_photo', 'ai_generated']]
                        
                        # Prepare the plan data for analysis
                        plan_data = {
                            "plan_title": plan_workouts[0].get('plan_title', 'Training Plan'),
                            "workouts": plan_workouts
                        }
                        
                        # Send the plan data for analysis
                        analysis_response = requests.post(
                            f"{API_URL}/chat/message",
                            json={"message": f"Please analyze this training plan and provide specific feedback on the structure, intensity distribution, and any recommendations for improvements. Plan data: {plan_data}"},
                            timeout=20
                        )
                        if analysis_response.status_code == 200:
                            analysis = analysis_response.json()["message"]
                            st.session_state.plan_analysis = analysis
                            st.rerun()
                        else:
                            st.error("Failed to get AI analysis")
                    else:
                        st.error("Failed to fetch plan data")
                except Exception as e:
                    st.error(f"Error getting analysis: {e}")
    
    with col2:
        if st.button("💡 Get Modifications", type="primary", key="training_plan_get_modifications"):
            with st.spinner("AI suggesting plan modifications..."):
                try:
                    mod_response = requests.post(
                        f"{API_URL}/chat/message",
                        json={"message": "Based on my current training plan and recent Strava activities, what specific modifications would you recommend? Please be specific about which workouts to change and why."},
                        timeout=20
                    )
                    if mod_response.status_code == 200:
                        modifications = mod_response.json()["message"]
                        st.session_state.plan_modifications = modifications
                        st.rerun()
                    else:
                        st.error("Failed to get modifications")
                except Exception as e:
                    st.error(f"Error getting modifications: {e}")
    
    # Show AI analysis if available
    if "plan_analysis" in st.session_state:
        with st.expander("📊 **AI Plan Analysis**", expanded=True):
            st.write(st.session_state.plan_analysis)
    
    # Show AI modifications if available
    if "plan_modifications" in st.session_state:
        with st.expander("💡 **AI Recommended Modifications**", expanded=True):
            st.write(st.session_state.plan_modifications)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Apply Suggestions", type="primary", key="training_plan_apply_suggestions"):
                    st.info("Feature coming soon: Automatic plan modifications based on AI suggestions!")
            with col2:
                if st.button("🔄 Get New Suggestions", key="training_plan_new_suggestions"):
                    del st.session_state.plan_modifications
                    st.rerun()
    
    # Training Schedule by Week
    st.subheader("📅 Weekly Training Schedule")
    
    # Group workouts by week
    workouts_by_week = {}
    for workout in plan_workouts:
        workout_date = datetime.fromisoformat(workout['date'])
        # Calculate week number from start of plan
        start_date = min(datetime.fromisoformat(t['date']) for t in plan_workouts)
        week_num = ((workout_date - start_date).days // 7) + 1
        
        if week_num not in workouts_by_week:
            workouts_by_week[week_num] = {}
        
        # Create a unique key for each workout based on date and type
        workout_key = f"{workout_date.strftime('%Y-%m-%d')}_{workout.get('type', '')}"
        
        # If we already have a workout for this day and type, keep the one with more details
        if workout_key in workouts_by_week[week_num]:
            existing = workouts_by_week[week_num][workout_key]
            # Keep the workout with the longer description or more details
            if len(workout.get('description', '')) > len(existing.get('description', '')):
                workouts_by_week[week_num][workout_key] = workout
        else:
            workouts_by_week[week_num][workout_key] = workout
    
    # Display each week
    for week_num in sorted(workouts_by_week.keys()):
        # Convert dictionary values to list and sort by date
        week_workouts = sorted(workouts_by_week[week_num].values(), key=lambda x: x['date'])
        
        with st.expander(f"📊 **Week {week_num}** ({len(week_workouts)} workouts)", expanded=week_num <= 2):
            # Week statistics
            distances = [w.get('distance', 0) or 0 for w in week_workouts]
            total_distance = sum(distances)
            workout_types = [w.get('type', 'unknown') for w in week_workouts]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Distance", f"{total_distance:.1f} km")
            with col2:
                st.metric("Workouts", len(week_workouts))
            with col3:
                intensity_mix = len(set(workout_types))
                st.metric("Variety", f"{intensity_mix} types")
            
            # Daily schedule
            st.write("**Daily Schedule:**")
            for workout in week_workouts:
                workout_date = datetime.fromisoformat(workout['date'])
                day_name = workout_date.strftime('%A')
                
                col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                with col1:
                    st.write(f"**{day_name}**")
                with col2:
                    workout_type = workout.get('type', 'unknown').replace('_', ' ').title()
                    type_emoji = {
                        'Easy Run': '🏃', 'Long Run': '🏃‍♂️', 'Intervals': '⚡', 
                        'Tempo': '🔥', 'Hills': '⛰️', 'Recovery': '😌', 'Rest': '😴'
                    }.get(workout_type, '🏃')
                    st.write(f"{type_emoji} {workout_type}")
                with col3:
                    description = workout.get('description', 'No description')
                    st.write(description)
                with col4:
                    distance = workout.get('distance')
                    if distance:
                        st.write(f"{distance:.1f}km")
                    else:
                        st.write("-")
    
    # Plan Management
    st.subheader("⚙️ Plan Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📷 Upload New Plan", key="training_plan_upload_new"):
            st.info("💡 **Go to 'Coach Chat' page** (in the sidebar) to upload a new training plan photo!")
    
    with col2:
        if st.button("🗑️ Clear Current Plan", type="secondary", key="training_plan_clear"):
            if st.session_state.get("confirm_clear", False):
                try:
                    delete_response = requests.delete(
                        f"{API_URL}/training/clear-plan",
                        params={"user_id": 1},
                        timeout=10
                    )
                    if delete_response.status_code == 200:
                        st.success("✅ Training plan cleared!")
                        st.session_state.confirm_clear = False
                        st.rerun()
                    else:
                        st.error(f"Failed to clear plan: {delete_response.text}")
                except Exception as e:
                    st.error(f"Error clearing plan: {e}")
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion of current plan")
                st.rerun()
    
    with col3:
        if st.button("📤 Export Plan", key="training_plan_export"):
            import io
            output = io.StringIO()
            output.write("Date,Day,Type,Description,Distance (km),Intensity\n")
            for workout in sorted(plan_workouts, key=lambda x: x['date']):
                date = workout['date']
                day = datetime.fromisoformat(date).strftime('%A')
                workout_type = workout.get('type', '').replace('_', ' ').title()
                description = workout.get('description', '').replace(',', ';')
                distance = workout.get('distance', 0) or 0
                intensity = workout.get('intensity', '')
                output.write(f"{date},{day},{workout_type},{description},{distance},{intensity}\n")
            
            st.download_button(
                label="💾 Download as CSV",
                data=output.getvalue(),
                file_name=f"training_plan_{plan_title.replace(' ', '_')}.csv",
                mime="text/csv"
            )
    
    # Integration with Strava
    st.subheader("🔗 Integration Status")
    
    try:
        # Get authentication headers
        headers = {
            "Authorization": f"Bearer {st.session_state['access_token']}",
            "Content-Type": "application/json"
        }
        
        # Check Strava connection
        strava_response = requests.get(f"{API_URL}/auth/strava/connection/status", headers=headers, timeout=5)
        if strava_response.status_code == 200 and strava_response.json().get("connected"):
            st.success("✅ Strava connected - Plan workouts can be compared with actual activities")
            
            if st.button("📊 Compare Plan vs Actual Performance", key="training_plan_compare_strava"):
                with st.spinner("Analyzing plan adherence..."):
                    try:
                        comparison_response = requests.post(
                            f"{API_URL}/chat/message",
                            json={"message": "Compare my training plan workouts with my actual Strava activities. How well am I following the plan and what adjustments should I make?"},
                            timeout=20
                        )
                        if comparison_response.status_code == 200:
                            comparison = comparison_response.json()["message"]
                            st.info("📈 **Plan vs Actual Analysis:**")
                            st.write(comparison)
                    except Exception as e:
                        st.error(f"Error getting comparison: {e}")
        else:
            st.info("ℹ️ Connect Strava to compare planned vs actual workouts")
            if st.button("🔗 Connect Strava", key="training_plan_connect_strava"):
                st.info("💡 **Go to 'Strava' page** (in the sidebar) to connect your account!")
    except:
        st.warning("⚠️ Unable to check Strava connection status")

def display_parsed_plan(plan_data: dict):
    """Display the parsed training plan data."""
    st.write("### 📋 Parsed Training Plan")
    
    # Display plan title and duration
    st.write(f"**Plan Title:** {plan_data.get('title', 'Untitled Plan')}")
    st.write(f"**Duration:** {plan_data.get('duration_weeks', 0)} weeks")
    
    # Display weekly structure
    st.write("### 📅 Weekly Structure")
    for week in plan_data.get('weekly_structure', []):
        st.write(f"#### Week {week.get('week_number', 'N/A')}")
        
        # Display workouts for this week
        for workout in week.get('workouts', []):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"**{workout.get('day', 'N/A')}**")
            with col2:
                st.write(f"{workout.get('workout_type', 'N/A')}: {workout.get('description', 'No description')}")
                if workout.get('distance'):
                    st.write(f"Distance: {workout.get('distance')} km")
        
        st.write("---")

def show_dashboard():
    """Show main dashboard with overview of training plan and recent activities."""
    st.header("🏠 Dashboard")
    
    # Load profile and training data
    load_profile_data()
    load_training_plan()
    
    # Quick overview section
    st.subheader("📊 Quick Overview")
    
    # Initialize variables
    plan_workouts = []
    recent_trainings = []
    response = None
    
    # Fetch recent training data
    try:
        response = requests.get(f"{API_URL}/training?user_id=1", timeout=10)
        if response.status_code == 200:
            trainings = response.json()
            recent_trainings = [t for t in trainings if t.get('plan_source') not in ['coach_photo', 'ai_generated']]
            plan_workouts = [t for t in trainings if t.get('plan_source') in ['coach_photo', 'ai_generated']]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Recent Activities", len(recent_trainings[-7:]))  # Last 7 days
            with col2:
                if plan_workouts:
                    st.metric("Plan Workouts", len(plan_workouts))
                else:
                    st.metric("Plan Workouts", 0)
            with col3:
                if recent_trainings:
                    total_distance = sum(t.get('actual_distance', 0) or 0 for t in recent_trainings[-7:])
                    st.metric("Weekly Distance", f"{total_distance:.1f} km")
                else:
                    st.metric("Weekly Distance", "0 km")
        else:
            st.info("No training data available")
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")
    
    # Quick actions
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📷 Upload Plan", key="dashboard_upload_plan"):
            st.info("💡 **Go to 'Coach Chat' page** (in the sidebar) to upload a training plan photo!")
    
    with col2:
        if st.button("📝 Log Activity", key="dashboard_log_activity"):
            st.info("💡 **Go to 'Daily Log' page** (in the sidebar) to log your activities!")
    
    with col3:
        if st.button("🤖 AI Coach", key="dashboard_ai_coach"):
            st.info("💡 **Go to 'Coach Chat' page** (in the sidebar) to chat with your AI coach!")
    
    # Recent activities preview
    st.subheader("📈 Recent Activities")
    try:
        if response.status_code == 200 and recent_trainings:
            recent_activities = recent_trainings[-5:]  # Show last 5 activities
            for activity in reversed(recent_activities):
                with st.expander(f"{activity['date']} - {activity.get('type', 'Activity')}", expanded=False):
                    st.write(f"**Distance:** {activity.get('actual_distance', 0):.1f} km")
                    st.write(f"**Duration:** {activity.get('actual_duration', 0)} minutes")
                    if activity.get('notes'):
                        st.write(f"**Notes:** {activity['notes']}")
        else:
            st.info("No recent activities to show")
    except Exception as e:
        st.error(f"Error loading recent activities: {str(e)}")
    
    # Link to full training plan
    st.subheader("📋 Training Plan")
    if plan_workouts:
        st.success(f"✅ You have an active training plan with {len(plan_workouts)} workouts")
        if st.button("View Full Plan", key="dashboard_view_plan"):
            st.info("💡 **Go to 'Training Plan' page** (in the sidebar) to see your complete plan!")
    else:
        st.info("🚀 **No training plan loaded yet!**")
        st.write("Upload a training plan photo in the Coach Chat page to see your dynamic plan here.")

if __name__ == "__main__":
    main() 
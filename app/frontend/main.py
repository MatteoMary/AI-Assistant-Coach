import streamlit as st
import requests
import plotly.express as px
import pandas as pd
import json
from datetime import datetime, timedelta
from PIL import Image
import base64
from io import BytesIO

# Configure the page
st.set_page_config(
    page_title="AI Running Coach",
    page_icon="🏃",
    layout="wide"
)

# API Configuration
API_URL = "http://localhost:8000/api/v1"

def main():
    st.title("🏃 AI Running Coach")
    
    # Initialize session state for data persistence
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'training_plan' not in st.session_state:
        st.session_state.training_plan = None
    if 'profile_data' not in st.session_state:
        st.session_state.profile_data = {}
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None

    # Login section
    if not st.session_state.get("access_token"):
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            try:
                print(f"Debug: Attempting login with email: {email}, password: {password}")
                response = requests.post(
                    f"{API_URL}/users/token",
                    data={"username": email, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                print(f"Debug: Response status code: {response.status_code}, headers: {response.headers}, text: {response.text}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state["access_token"] = token_data["access_token"]
                    st.session_state["token_type"] = token_data["token_type"]
                    print(f"Debug: Token stored in session state: {st.session_state['access_token']}")
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Login failed. Please check your credentials.")
            except Exception as e:
                st.error(f"Error during login: {str(e)}")
                print(f"Debug: Login error: {str(e)}")
        return

    # Sidebar for navigation
    with st.sidebar:
        st.title("Navigation")
        page = st.radio(
            "Go to",
            ["Dashboard", "Training Plan", "Daily Log", "Progress", "Profile", "Strava", "Workout Context", "Coach Chat"]
        )
    
    # Check API connection with timeout
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("Connected to backend")
        else:
            st.sidebar.error(f"Backend error: {response.status_code}")
            st.error("Please make sure the backend server is running on port 8000")
            return
    except requests.exceptions.ConnectionError:
        st.sidebar.error("Cannot connect to backend")
        st.error("""
        Cannot connect to the backend server. Please ensure:
        1. The backend server is running (uvicorn app.main:app --host 0.0.0.0 --port 8000)
        2. You're running both frontend and backend
        3. The API_URL is correct (currently set to http://localhost:8000)
        """)
        return
    except requests.exceptions.Timeout:
        st.sidebar.error("Backend connection timeout")
        st.error("The backend server is taking too long to respond. Please check if it's running correctly.")
        return
    except Exception as e:
        st.sidebar.error(f"Unexpected error: {str(e)}")
        return

    # Load data based on current page
    if page == "Profile":
        load_profile_data()
    elif page == "Training Plan":
        load_training_plan()
    
    # Display selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "Training Plan":
        show_training_plan()
    elif page == "Daily Log":
        show_daily_log()
    elif page == "Progress":
        show_progress()
    elif page == "Profile":
        show_profile()
    elif page == "Strava":
        show_strava()
    elif page == "Workout Context":
        show_workout_context()
    elif page == "Coach Chat":
        show_chat()

def load_profile_data():
    """Load user profile data from API"""
    try:
        response = requests.get(f"{API_URL}/user/profile", timeout=5)
        if response.status_code == 200:
            st.session_state.profile_data = response.json()
    except Exception as e:
        st.error(f"Error loading profile data: {str(e)}")

def load_training_plan():
    """Load training plan data from API"""
    try:
        response = requests.get(f"{API_URL}/training?user_id=1", timeout=10)
        if response.status_code == 200:
            trainings = response.json()
            st.session_state.training_plan = [t for t in trainings if t.get('plan_source') in ['coach_photo', 'ai_generated']]
    except Exception as e:
        st.error(f"Error loading training plan: {str(e)}")

def save_profile_data(profile_data):
    """Save user profile data to API"""
    try:
        response = requests.put(
            f"{API_URL}/users/me", 
            json=profile_data, 
            timeout=10
        )
        
        if response.status_code == 200:
            st.session_state.profile_data = response.json()
            return True
        else:
            st.error(f"Failed to save profile: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error saving profile: {str(e)}")
        return False

def save_training_plan(plan_data: dict):
    """Save the parsed training plan to the database."""
    try:
        if "access_token" not in st.session_state:
            st.error("Please log in first")
            return
            
        token = st.session_state["access_token"]
        print(f"Debug: Using access token: {token}")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        print(f"Debug: Request headers: {headers}")
        
        response = requests.post(
            f"{API_URL}/plan-parser/parse-and-save",
            json=plan_data,
            headers=headers
        )
        print(f"Debug: Save response status: {response.status_code}")
        print(f"Debug: Save response text: {response.text}")
        
        if response.status_code == 200:
            st.success("Training plan saved successfully!")
        else:
            st.error(f"Error saving training plan: {response.text}")
    except Exception as e:
        st.error(f"Error saving training plan: {str(e)}")
        print(f"Debug: Save error: {str(e)}")

def upload_file():
    """Handle file upload and processing."""
    try:
        if "access_token" not in st.session_state:
            st.error("Please log in first")
            return
            
        token = st.session_state["access_token"]
        print(f"Debug: Using access token for upload: {token}")
        
        uploaded_file = st.file_uploader("Upload your training plan image", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            # Display the uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Training Plan", use_column_width=True)
            
            # Convert the image to base64
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Prepare the request
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            print(f"Debug: Upload request headers: {headers}")
            
            data = {
                "image": img_str,
                "filename": uploaded_file.name
            }
            
            # Send the request
            response = requests.post(
                f"{API_URL}/plan-parser/upload-image",
                json=data,
                headers=headers
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

def show_dashboard():
    st.header("🏃 AI Running Coach Dashboard")

    # Get AI insights for dashboard
    try:
        insights_response = requests.get(f"{API_URL}/ai-coach/quick-insights", timeout=10)
        if insights_response.status_code == 200:
            insights = insights_response.json()
            has_data = "error" not in insights
        else:
            has_data = False
            insights = {}
    except:
        has_data = False
        insights = {}

    if has_data:
        # AI Insights Section
        st.subheader("🤖 AI Coach Insights")
        with st.container():
            st.info("📊 **Your Training Analysis**")
            st.write(insights.get("ai_summary", "No insights available"))

        # Real Training Metrics
        st.subheader("📈 Your Training Metrics (Last 2 Weeks)")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            weekly_dist = insights.get("weekly_distance", 0)
            st.metric("Weekly Distance", f"{weekly_dist:.1f} km")
        with col2:
            weekly_freq = insights.get("weekly_frequency", 0)
            st.metric("Weekly Frequency", f"{weekly_freq:.1f} runs")
        with col3:
            avg_pace = insights.get("average_pace", "N/A")
            st.metric("Average Pace", f"{avg_pace}/km" if avg_pace != "N/A" else avg_pace)
        with col4:
            longest = insights.get("longest_run", 0)
            st.metric("Longest Run", f"{longest:.1f} km")

        # Training Summary
        st.subheader("🎯 Recent Activity Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Activities", insights.get("total_activities", 0))
        with col2:
            if st.button("🔍 Get Detailed Analysis", type="primary"):
                with st.spinner("Analyzing your training data..."):
                    try:
                        analysis_response = requests.get(f"{API_URL}/ai-coach/analysis?days_back=30", timeout=15)
                        if analysis_response.status_code == 200:
                            detailed = analysis_response.json()
                            if "ai_insights" in detailed:
                                st.success("✅ Analysis Complete!")
                                st.markdown("### 📋 Detailed AI Analysis")
                                st.write(detailed["ai_insights"])
                            else:
                                st.warning("Analysis completed but no AI insights available")
                        else:
                            st.error("Failed to get detailed analysis")
                    except Exception as e:
                        st.error(f"Error getting analysis: {e}")
    else:
        # Fallback for no data
        st.subheader("🚀 Welcome to Your AI Running Coach!")
        st.info("💡 **Connect your Strava account to unlock AI coaching features!**")
        st.write("Once connected, you'll see:")
        st.write("• 🤖 **Personalized AI insights** based on your actual running data")
        st.write("• 📊 **Real training metrics** from your activities")
        st.write("• 🎯 **Specific recommendations** for improving your performance")
        st.write("• 📈 **Progress tracking** and trend analysis")

        if st.button("Connect Strava Now", type="primary"):
            st.info("💡 **Go to 'Strava' page** (in the sidebar) to connect your account!")

    # General Training Tips (always show)
    st.subheader("💡 Today's Training Tips")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**🏃 Easy Run Focus**")
        st.write("80% of your runs should be at an easy, conversational pace")
    with col2:
        st.info("**💤 Recovery is Key**")
        st.write("Listen to your body and prioritize sleep and nutrition")

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
    except Exception:
        plan_workouts = []
    
    if not plan_workouts:
        # No plan uploaded yet
        st.info("🚀 **No training plan loaded yet!**")
        st.write("Upload a training plan photo in the Coach Chat page to see your dynamic plan here.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📷 Upload Training Plan", type="primary"):
                st.info("💡 **Go to 'Coach Chat' page** (in the sidebar) to upload a training plan photo!")
        with col2:
            if st.button("🤖 Generate AI Plan", type="secondary"):
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
        if st.button("🔍 Analyze Plan with AI", type="secondary"):
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
        if st.button("💡 Get Modifications", type="primary"):
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
                if st.button("✅ Apply Suggestions", type="primary"):
                    st.info("Feature coming soon: Automatic plan modifications based on AI suggestions!")
            with col2:
                if st.button("🔄 Get New Suggestions"):
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
        if st.button("📷 Upload New Plan"):
            st.info("💡 **Go to 'Coach Chat' page** (in the sidebar) to upload a new training plan photo!")
    
    with col2:
        if st.button("🗑️ Clear Current Plan", type="secondary"):
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
        if st.button("📤 Export Plan"):
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
        # Check Strava connection
        strava_response = requests.get(f"{API_URL}/strava/connection/status", timeout=5)
        if strava_response.status_code == 200 and strava_response.json().get("connected"):
            st.success("✅ Strava connected - Plan workouts can be compared with actual activities")
            
            if st.button("📊 Compare Plan vs Actual Performance"):
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
            if st.button("🔗 Connect Strava"):
                st.info("💡 **Go to 'Strava' page** (in the sidebar) to connect your account!")
    except:
        st.warning("⚠️ Unable to check Strava connection status")

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
    st.header("Progress Tracking")
    
    # Time Period Selection
    period = st.selectbox("View Period", ["Last Week", "Last Month", "Last 3 Months", "Year to Date"])
    
    # Key Metrics
    st.subheader("Training Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Weekly Average", "45.2 km", "+2.3 km")
    with col2:
        st.metric("Monthly Volume", "180.8 km", "+15.5 km")
    with col3:
        st.metric("Year to Date", "1,205 km", None)
    
    # Progress Graphs
    weekly_data = {
        'Week': list(range(1, 11)),
        'Distance': [40, 42, 45, 43, 46, 44, 48, 45, 47, 45],
        'Long Run': [15, 16, 16, 15, 17, 16, 18, 16, 17, 16]
    }
    df = pd.DataFrame(weekly_data)
    
    fig1 = px.line(df, x='Week', y=['Distance', 'Long Run'], 
                  title='Weekly Distance Progression')
    st.plotly_chart(fig1, use_container_width=True)
    
    # Race Times
    st.subheader("Race Times")
    times = {
        'Distance': ['5K', '10K', 'Half Marathon', 'Marathon'],
        'Personal Best': ['20:30', '43:15', '1:35:00', '3:35:00'],
        'Recent': ['20:45', '44:00', '1:37:00', '-']
    }
    st.table(pd.DataFrame(times))

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
    st.header("🚴 Strava Integration")
    
    # Handle disconnection state
    if st.session_state.get("strava_disconnected", False):
        st.session_state.strava_disconnected = False
        st.info("Refreshing connection status...")
        
    # Check connection status
    try:
        response = requests.get(f"{API_URL}/strava/connection/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            is_connected = status.get("connected", False)
            athlete_info = status.get("athlete")
        else:
            is_connected = False
            athlete_info = None
    except Exception:
        is_connected = False
        athlete_info = None
    
    if is_connected:
        # Show connected status
        if athlete_info:
            st.success(f"✅ Connected to Strava as {athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Athlete ID", athlete_info.get("id", "N/A"))
            with col2:
                st.metric("Location", athlete_info.get("city", "Unknown"))
        else:
            st.success("✅ Connected to Strava")
            st.info("Loading athlete information...")
        
        # Import activities section
        st.subheader("Import Activities")
        col1, col2 = st.columns(2)
        
        with col1:
            days_back = st.number_input("Days to import", min_value=1, max_value=365, value=30)
        
        with col2:
            st.write("")  # Spacing
            if st.button("Import Activities"):
                with st.spinner("Importing activities from Strava..."):
                    try:
                        import_response = requests.post(
                            f"{API_URL}/strava/activities/import",
                            params={"days_back": days_back},
                            timeout=30
                        )
                        if import_response.status_code == 200:
                            result = import_response.json()
                            st.success(f"✅ {result['message']}")
                        else:
                            st.error("Failed to import activities")
                    except Exception as e:
                        st.error(f"Error importing activities: {e}")
        
        # Show activity statistics
        st.subheader("Activity Statistics")
        try:
            stats_response = requests.get(f"{API_URL}/strava/activities/stats", timeout=5)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Activities", stats["total_activities"])
                with col2:
                    st.metric("Total Distance", f"{stats['total_distance_km']} km")
                with col3:
                    st.metric("Total Time", f"{stats['total_time_hours']} hours")
                
                # Activity types breakdown
                if stats["activity_types"]:
                    st.subheader("Activity Types")
                    for activity_type, data in stats["activity_types"].items():
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**{activity_type}**")
                        with col2:
                            st.write(f"{data['count']} activities, {data['distance_km']:.1f} km")
        except Exception:
            st.warning("Could not load activity statistics")
        
        # Show recent activities
        st.subheader("Recent Activities")
        try:
            activities_response = requests.get(f"{API_URL}/strava/activities?limit=10", timeout=5)
            if activities_response.status_code == 200:
                activities = activities_response.json()
                
                if activities:
                    for activity in activities:
                        with st.expander(f"{activity['name']} ({activity['type']})"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**Distance:** {activity['distance_km']:.2f} km")
                                st.write(f"**Duration:** {activity['duration']}")
                            with col2:
                                if activity['pace_per_km']:
                                    st.write(f"**Pace:** {activity['pace_per_km']}/km")
                                if activity['average_heartrate']:
                                    st.write(f"**Avg HR:** {activity['average_heartrate']:.0f} bpm")
                            with col3:
                                if activity['total_elevation_gain']:
                                    st.write(f"**Elevation:** {activity['total_elevation_gain']:.0f} m")
                                if activity['calories']:
                                    st.write(f"**Calories:** {activity['calories']:.0f}")
                else:
                    st.info("No activities imported yet. Click 'Import Activities' to get started!")
        except Exception:
            st.warning("Could not load recent activities")
        
        # Disconnect option
        st.subheader("Manage Connection")
        if st.button("Disconnect Strava", type="secondary"):
            try:
                disconnect_response = requests.delete(f"{API_URL}/strava/connection", timeout=5)
                if disconnect_response.status_code == 200:
                    st.success("Disconnected from Strava successfully!")
                    # Set flag to refresh on next load instead of immediate rerun
                    st.session_state.strava_disconnected = True
                else:
                    st.error("Failed to disconnect from Strava")
            except Exception as e:
                st.error(f"Error disconnecting: {e}")
    
    else:
        # Show connect to Strava option
        st.info("Connect your Strava account to import your activities and get personalized coaching insights!")
        
        st.subheader("Benefits of connecting Strava:")
        st.write("🏃 **Automatic activity import** - Your runs, rides, and workouts")
        st.write("📊 **Performance analysis** - Detailed metrics and trends")
        st.write("🎯 **Personalized coaching** - AI recommendations based on your data")
        st.write("📈 **Progress tracking** - See your improvement over time")
        
        if st.button("Connect to Strava", type="primary"):
            try:
                # Get authorization URL
                auth_response = requests.get(f"{API_URL}/strava/auth/connect", timeout=5)
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    auth_url = auth_data["authorization_url"]
                    
                    st.success("Click the link below to connect your Strava account:")
                    st.markdown(f"[**Connect to Strava**]({auth_url})")
                    st.info("After authorizing, you'll be redirected back to this page.")
                else:
                    st.error("Failed to get Strava authorization URL")
            except Exception as e:
                st.error(f"Error connecting to Strava: {e}")
    
    # Check for connection status in URL parameters (only show message once)
    if "strava_connected" in st.query_params and st.query_params["strava_connected"] == "true":
        if "strava_success_shown" not in st.session_state:
            st.success("✅ Successfully connected to Strava!")
            st.session_state.strava_success_shown = True
    elif "strava_error" in st.query_params and st.query_params["strava_error"] == "true":
        if "strava_error_shown" not in st.session_state:
            st.error("❌ Error connecting to Strava. Please try again.")
            st.session_state.strava_error_shown = True

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
                        f"{API_URL}/plan-parser/parse-and-save",
                        files=files
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

if __name__ == "__main__":
    main() 
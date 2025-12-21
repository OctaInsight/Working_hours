# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import calendar
from io import BytesIO
import base64

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.error("⚠️ Supabase library not installed. Run: pip install supabase")

# -------------------------------------------------------------
# Supabase connection
# -------------------------------------------------------------
@st.cache_resource
def get_supabase_client() -> Client:
    """Initialize Supabase client with error handling"""
    try:
        if "supabase" not in st.secrets:
            st.error("❌ Supabase credentials not found in secrets.toml")
            st.info("""
            Please add the following to .streamlit/secrets.toml:
            
            [supabase]
            url = "your-project-url"
            key = "your-anon-key"
            """)
            st.stop()
        
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        
        if not url or not key:
            st.error("❌ Supabase URL or Key is empty")
            st.stop()
        
        client = create_client(url, key)
        
        # Test connection
        try:
            client.table("workinghours").select("id", count="exact").limit(1).execute()
        except Exception as e:
            st.error(f"❌ Failed to connect to Supabase: {str(e)}")
            st.info("Please check your Supabase credentials and ensure the 'workinghours' table exists.")
            st.stop()
        
        return client
    except Exception as e:
        st.error(f"❌ Error initializing Supabase: {str(e)}")
        st.stop()

# -------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="Working Hours Tracker",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Session state
# -------------------------------------------------------------
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "current_month" not in st.session_state:
    st.session_state.current_month = datetime.now().month
if "current_year" not in st.session_state:
    st.session_state.current_year = datetime.now().year
if "num_project_columns" not in st.session_state:
    st.session_state.num_project_columns = 2  # Start with 2 projects

# -------------------------------------------------------------
# User credentials (read from secrets)
# -------------------------------------------------------------
try:
    USER_CREDENTIALS = dict(st.secrets.get("user_credentials", {}))
    if not USER_CREDENTIALS:
        st.warning("⚠️ No user credentials configured in secrets.toml")
        USER_CREDENTIALS = {"demo@example.com": "demo123"}  # Fallback for testing
except Exception as e:
    st.error(f"Error loading user credentials: {e}")
    USER_CREDENTIALS = {"demo@example.com": "demo123"}

# -------------------------------------------------------------
# Project list (read from secrets or use default)
# -------------------------------------------------------------
try:
    PROJECT_LIST = list(st.secrets.get("projects", {}).get("names", []))
    if not PROJECT_LIST:
        PROJECT_LIST = ["Project A", "Project B", "Project C", "Project D", "Project E"]
except Exception as e:
    PROJECT_LIST = ["Project A", "Project B", "Project C", "Project D", "Project E"]

# -------------------------------------------------------------
# Authentication Functions
# -------------------------------------------------------------
def authenticate_user(email, password):
    """Authenticate user"""
    if USER_CREDENTIALS.get(email) == password:
        st.session_state.authenticated_user = email
        return True
    return False

def logout():
    """Logout current user"""
    st.session_state.authenticated_user = None
    st.rerun()

# -------------------------------------------------------------
# Data Management Functions
# -------------------------------------------------------------
def save_working_hours(user_email, year, month, day, hours, project, comments=""):
    """Save or update working hours entry"""
    try:
        supabase = get_supabase_client()
        
        # Check if entry exists
        existing = supabase.table("workinghours").select("*").eq("user_email", user_email).eq("year", year).eq("month", month).eq("day", day).eq("project", project).execute()
        
        if existing.data:
            # Update existing
            payload = {
                "hours": float(hours),
                "comments": comments
            }
            supabase.table("workinghours").update(payload).eq("id", existing.data[0]["id"]).execute()
        else:
            # Insert new
            payload = {
                "user_email": user_email,
                "year": year,
                "month": month,
                "day": day,
                "hours": float(hours),
                "project": project,
                "comments": comments
            }
            supabase.table("workinghours").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

def save_monthly_summary(user_email, year, month, summary_text):
    """Save monthly summary text"""
    try:
        supabase = get_supabase_client()
        
        # Check if summary exists
        existing = supabase.table("monthly_summaries").select("*").eq("user_email", user_email).eq("year", year).eq("month", month).execute()
        
        if existing.data:
            # Update existing
            supabase.table("monthly_summaries").update({"summary_text": summary_text}).eq("id", existing.data[0]["id"]).execute()
        else:
            # Insert new
            payload = {
                "user_email": user_email,
                "year": year,
                "month": month,
                "summary_text": summary_text
            }
            supabase.table("monthly_summaries").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Error saving summary: {e}")
        return False

def load_working_hours(user_email, year, month):
    """Load working hours for a specific month"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("workinghours").select("*").eq("user_email", user_email).eq("year", year).eq("month", month).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def load_monthly_summary(user_email, year, month):
    """Load monthly summary text"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("monthly_summaries").select("*").eq("user_email", user_email).eq("year", year).eq("month", month).execute()
        return result.data[0]["summary_text"] if result.data else ""
    except Exception as e:
        return ""

def delete_working_hours_entry(entry_id):
    """Delete a working hours entry"""
    try:
        supabase = get_supabase_client()
        supabase.table("workinghours").delete().eq("id", entry_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting entry: {e}")
        return False

# -------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------
def get_days_in_month(year, month):
    """Get list of days in a month with day names"""
    num_days = calendar.monthrange(year, month)[1]
    days_data = []
    
    for day in range(1, num_days + 1):
        date_obj = date(year, month, day)
        day_name = date_obj.strftime("%A")
        days_data.append({
            "day": day,
            "day_name": day_name,
            "date": date_obj
        })
    
    return days_data

def get_week_number(date_obj):
    """Get week number of the month"""
    first_day = date(date_obj.year, date_obj.month, 1)
    return (date_obj.day + first_day.weekday()) // 7 + 1

# -------------------------------------------------------------
# Main App
# -------------------------------------------------------------
def main():
    if not SUPABASE_AVAILABLE:
        st.stop()
    
    st.title("⏰ Working Hours Tracking System")
    
    # Authentication
    if not st.session_state.authenticated_user:
        st.markdown("### 🔐 Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("🔓 Login", type="primary", use_container_width=True):
                if authenticate_user(email, password):
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
        
        st.stop()
    
    # User is authenticated
    st.sidebar.success(f"👤 Logged in as: {st.session_state.authenticated_user}")
    if st.sidebar.button("🚪 Logout"):
        logout()
    
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["📝 Enter Hours", "📊 Dashboard", "📋 View/Edit Data"]
    )
    
    # Month/Year selector
    st.sidebar.title("📅 Select Period")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        selected_month = st.selectbox(
            "Month",
            range(1, 13),
            index=st.session_state.current_month - 1,
            format_func=lambda x: calendar.month_name[x]
        )
    with col2:
        selected_year = st.selectbox(
            "Year",
            range(2020, 2031),
            index=st.session_state.current_year - 2020
        )
    
    st.session_state.current_month = selected_month
    st.session_state.current_year = selected_year
    
    # -------------- PAGE 1: Enter Hours ------------------
    if page == "📝 Enter Hours":
        st.header(f"📝 Enter Working Hours - {calendar.month_name[selected_month]} {selected_year}")
        
        # Button to add more project columns
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            if st.button("➕ Add 1 More Projects", disabled=st.session_state.num_project_columns >= 10):
                st.session_state.num_project_columns = min(10, st.session_state.num_project_columns + 1)
                st.rerun()
        with col2:
            if st.button("➖ Remove 1 Projects", disabled=st.session_state.num_project_columns <= 2):
                st.session_state.num_project_columns = max(2, st.session_state.num_project_columns - 1)
                st.rerun()
        
        st.info(f"Currently showing {st.session_state.num_project_columns} project columns")
        
        days_data = get_days_in_month(selected_year, selected_month)
        existing_data = load_working_hours(
            st.session_state.authenticated_user,
            selected_year,
            selected_month
        )
        
        # Create input form
        with st.form("hours_entry_form"):
            st.subheader("Daily Hours Entry")
            
            # Calculate column widths dynamically
            num_projects = st.session_state.num_project_columns
            base_cols = [1, 1]  # Day and Date
            project_cols = [2, 1.2] * num_projects  # Project (wider) and Hours for each
            comment_col = [2.5]  # Comments
            
            all_col_widths = base_cols + project_cols + comment_col
            
            # Create table headers
            cols = st.columns(all_col_widths)
            cols[0].markdown("**Day**")
            cols[1].markdown("**Date**")
            
            # Dynamic project headers
            for i in range(num_projects):
                cols[2 + i*2].markdown(f"**Project {i+1}**")
                cols[3 + i*2].markdown(f"**Hours {i+1}**")
            
            # Comments header at the end
            cols[2 + num_projects*2].markdown("**Comments**")
            
            # Store form data
            form_data = []
            
            for day_info in days_data:
                day = day_info["day"]
                day_name = day_info["day_name"]
                date_str = day_info["date"].strftime("%Y-%m-%d")
                
                # Get existing data for this day
                day_existing = existing_data[existing_data["day"] == day] if not existing_data.empty else pd.DataFrame()
                
                # Create columns for this row
                cols = st.columns(all_col_widths)
                
                # Day and date
                cols[0].write(f"{day_name[:3]}")
                cols[1].write(f"{day}")
                
                # Projects and hours (dynamic number)
                day_entries = []
                for i in range(num_projects):
                    project_col = cols[2 + i*2]
                    hours_col = cols[3 + i*2]
                    
                    # Get existing data for this project slot
                    existing_project = ""
                    existing_hours = 0.0
                    
                    if not day_existing.empty and i < len(day_existing):
                        existing_project = day_existing.iloc[i].get("project", "")
                        existing_hours = float(day_existing.iloc[i].get("hours", 0))
                    
                    project = project_col.selectbox(
                        f"Project {i+1}",
                        [""] + PROJECT_LIST,
                        index=PROJECT_LIST.index(existing_project) + 1 if existing_project in PROJECT_LIST else 0,
                        key=f"project_{day}_{i}",
                        label_visibility="collapsed"
                    )
                    
                    hours = hours_col.number_input(
                        f"Hours {i+1}",
                        min_value=0.0,
                        max_value=24.0,
                        step=0.5,
                        value=existing_hours,
                        key=f"hours_{day}_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if project and hours > 0:
                        day_entries.append({
                            "day": day,
                            "project": project,
                            "hours": hours,
                            "comments": ""  # Will be set below
                        })
                
                # Comments at the end (rightmost column)
                existing_comments = ""
                if not day_existing.empty:
                    existing_comments = day_existing.iloc[0].get("comments", "")
                
                comments = cols[2 + num_projects*2].text_input(
                    "Comments",
                    value=existing_comments,
                    key=f"comments_{day}",
                    label_visibility="collapsed"
                )
                
                # Update comments for all day entries
                for entry in day_entries:
                    entry["comments"] = comments
                
                form_data.extend(day_entries)
            
            # Monthly summary
            st.markdown("---")
            st.subheader("📄 Monthly Activity Summary")
            existing_summary = load_monthly_summary(
                st.session_state.authenticated_user,
                selected_year,
                selected_month
            )
            
            monthly_summary = st.text_area(
                "Describe your activities for this month",
                value=existing_summary,
                height=150,
                key="monthly_summary"
            )
            
            # Submit button
            submitted = st.form_submit_button("💾 Save All Data", type="primary", use_container_width=True)
            
            if submitted:
                with st.spinner("Saving data..."):
                    success_count = 0
                    
                    # Save working hours
                    for entry in form_data:
                        if save_working_hours(
                            st.session_state.authenticated_user,
                            selected_year,
                            selected_month,
                            entry["day"],
                            entry["hours"],
                            entry["project"],
                            entry["comments"]
                        ):
                            success_count += 1
                    
                    # Save monthly summary
                    save_monthly_summary(
                        st.session_state.authenticated_user,
                        selected_year,
                        selected_month,
                        monthly_summary
                    )
                    
                    if success_count > 0:
                        st.success(f"✅ Successfully saved {success_count} entries!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.info("ℹ️ No data to save")
    
    # -------------- PAGE 2: Dashboard ------------------
    elif page == "📊 Dashboard":
        st.header(f"📊 Dashboard - {calendar.month_name[selected_month]} {selected_year}")
        
        data = load_working_hours(
            st.session_state.authenticated_user,
            selected_year,
            selected_month
        )
        
        if data.empty:
            st.info("No data available for this period. Please enter your working hours first.")
            return
        
        # Calculate statistics
        total_hours = data["hours"].sum()
        unique_projects = data["project"].nunique()
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Hours", f"{total_hours:.1f}h")
        col2.metric("Projects Worked", unique_projects)
        col3.metric("Working Days", data["day"].nunique())
        col4.metric("Avg Hours/Day", f"{total_hours / data['day'].nunique():.1f}h")
        
        # Hours per project
        st.subheader("📊 Hours per Project")
        project_hours = data.groupby("project")["hours"].sum().sort_values(ascending=False)
        
        fig1 = px.bar(
            x=project_hours.index,
            y=project_hours.values,
            labels={"x": "Project", "y": "Hours"},
            title="Total Hours by Project"
        )
        fig1.update_traces(marker_color='#1f77b4')
        st.plotly_chart(fig1, use_container_width=True)
        
        # Weekly summary
        st.subheader("📅 Weekly Hours Summary")
        
        # Calculate weekly hours
        data["week"] = data["day"].apply(lambda d: get_week_number(date(selected_year, selected_month, d)))
        weekly_hours = data.groupby("week")["hours"].sum()
        
        # Create weekly comparison chart
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Actual Hours",
            x=[f"Week {w}" for w in weekly_hours.index],
            y=weekly_hours.values,
            marker_color='#1f77b4'
        ))
        fig2.add_trace(go.Bar(
            name="Target (37.5h)",
            x=[f"Week {w}" for w in weekly_hours.index],
            y=[37.5] * len(weekly_hours),
            marker_color='#2ca02c'
        ))
        fig2.update_layout(
            title="Weekly Hours vs Target (37.5h/week)",
            barmode='group',
            yaxis_title="Hours"
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Weekly breakdown table
        st.subheader("📋 Weekly Breakdown")
        weekly_df = pd.DataFrame({
            "Week": [f"Week {w}" for w in weekly_hours.index],
            "Total Hours": weekly_hours.values,
            "Target": 37.5,
            "Difference": weekly_hours.values - 37.5,
            "Status": ["✅ On Track" if h >= 37.5 else "⚠️ Below Target" for h in weekly_hours.values]
        })
        st.dataframe(weekly_df, use_container_width=True)
        
        # Daily hours chart
        st.subheader("📈 Daily Hours Trend")
        daily_hours = data.groupby("day")["hours"].sum()
        
        fig3 = px.line(
            x=daily_hours.index,
            y=daily_hours.values,
            markers=True,
            labels={"x": "Day of Month", "y": "Hours"},
            title="Daily Hours Worked"
        )
        fig3.update_traces(line_color='#1f77b4', marker_color='#ff7f0e')
        fig3.add_hline(y=7.5, line_dash="dash", line_color="green", annotation_text="Daily Target (7.5h)")
        st.plotly_chart(fig3, use_container_width=True)
        
        # Project distribution pie chart
        st.subheader("🥧 Time Distribution by Project")
        fig4 = px.pie(
            values=project_hours.values,
            names=project_hours.index,
            title="Percentage of Time per Project"
        )
        st.plotly_chart(fig4, use_container_width=True)
        
        # Monthly summary
        st.subheader("📄 Monthly Summary")
        summary = load_monthly_summary(
            st.session_state.authenticated_user,
            selected_year,
            selected_month
        )
        if summary:
            st.text_area("Monthly Activities", value=summary, height=150, disabled=True)
        else:
            st.info("No monthly summary available")
    
    # -------------- PAGE 3: View/Edit Data ------------------
    elif page == "📋 View/Edit Data":
        st.header(f"📋 View/Edit Data - {calendar.month_name[selected_month]} {selected_year}")
        
        data = load_working_hours(
            st.session_state.authenticated_user,
            selected_year,
            selected_month
        )
        
        if data.empty:
            st.info("No data available for this period.")
            return
        
        # Display data
        st.subheader("Current Entries")
        
        # Format data for display
        display_data = data.copy()
        if not display_data.empty:
            display_data = display_data.sort_values(["day", "project"])
            display_data["date"] = display_data["day"].apply(
                lambda d: date(selected_year, selected_month, d).strftime("%Y-%m-%d")
            )
            
            # Reorder columns
            columns_order = ["day", "date", "project", "hours", "comments", "id"]
            display_data = display_data[[col for col in columns_order if col in display_data.columns]]
            
            st.dataframe(display_data, use_container_width=True)
        
        # Edit/Delete functionality
        st.subheader("✏️ Edit or Delete Entry")
        
        if not data.empty:
            entry_options = []
            for _, row in data.iterrows():
                entry_label = f"Day {row['day']} - {row['project']} - {row['hours']}h"
                entry_options.append((entry_label, row['id']))
            
            selected_entry = st.selectbox(
                "Select entry to edit/delete",
                options=range(len(entry_options)),
                format_func=lambda x: entry_options[x][0]
            )
            
            if selected_entry is not None:
                entry_id = entry_options[selected_entry][1]
                entry_data = data[data["id"] == entry_id].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Edit Entry**")
                    new_project = st.selectbox(
                        "Project",
                        PROJECT_LIST,
                        index=PROJECT_LIST.index(entry_data["project"]) if entry_data["project"] in PROJECT_LIST else 0
                    )
                    new_hours = st.number_input("Hours", min_value=0.0, max_value=24.0, step=0.5, value=float(entry_data["hours"]))
                    new_comments = st.text_area("Comments", value=entry_data.get("comments", ""))
                    
                    if st.button("💾 Update Entry", type="primary"):
                        if save_working_hours(
                            st.session_state.authenticated_user,
                            selected_year,
                            selected_month,
                            entry_data["day"],
                            new_hours,
                            new_project,
                            new_comments
                        ):
                            st.success("✅ Entry updated successfully!")
                            st.rerun()
                
                with col2:
                    st.markdown("**Delete Entry**")
                    st.warning(f"⚠️ You are about to delete:\nDay {entry_data['day']} - {entry_data['project']} - {entry_data['hours']}h")
                    
                    if st.button("🗑️ Delete Entry", type="secondary"):
                        if delete_working_hours_entry(entry_id):
                            st.success("✅ Entry deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete entry")

if __name__ == "__main__":
    main()

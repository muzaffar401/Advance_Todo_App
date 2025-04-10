import streamlit as st
import json
import os
from datetime import datetime
import random
import hashlib
import hmac
import base64 
import plotly.express as px
import pandas as pd
import time

# Constants
DATA_FILE = "todo_data.json"
LIST_EMOJIS = ["📋", "📝", "✅", "📌", "🗒️", "✏️", "📅", "📊"]
TASK_EMOJIS = ["•", "→", "⇒", "⦿", "○", "▪", "▫", "‣"]

def hash_password(password):
    """Hash a password for storing."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'key': base64.b64encode(key).decode('utf-8')
    }

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    try:
        salt = base64.b64decode(stored_password['salt'].encode('utf-8'))
        stored_key = base64.b64decode(stored_password['key'].encode('utf-8'))
        key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key, stored_key)
    except:
        return False

def check_credentials(username, password):
    """Check if credentials are valid"""
    if username in st.session_state.users:
        stored_password = st.session_state.users[username]["password_hash"]
        return verify_password(stored_password, password)
    return False

def load_data():
    """Load all data from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"lists": {}, "current_list": None, "users": {}}
    return {"lists": {}, "current_list": None, "users": {}}

def save_data():
    """Save all data to JSON file"""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({
                "lists": st.session_state.lists,
                "current_list": st.session_state.current_list,
                "users": st.session_state.users
            }, f, indent=2)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def initialize_state():
    """Initialize session state variables"""
    if "initialized" not in st.session_state:
        data = load_data()
        st.session_state.lists = data.get("lists", {})
        st.session_state.current_list = data.get("current_list", next(iter(st.session_state.lists.keys()))) if st.session_state.lists else None
        st.session_state.users = data.get("users", {})
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.auth_tab = "Login"
        st.session_state.initialized = True
        st.session_state.register_success = False
    
    defaults = {
        "new_task": "",
        "new_list_name": "",
        "new_task_priority": "Medium",
        "show_completed": True,
        "show_pending": True,
        "priority_filter": "All",
        "delete_confirmation": None,
        "reset_db_confirm": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def add_list():
    """Add a new list"""
    if st.session_state.new_list_name and st.session_state.new_list_name.strip():
        list_id = f"list_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        st.session_state.lists[list_id] = {
            "name": st.session_state.new_list_name.strip(),
            "tasks": [],
            "emoji": random.choice(LIST_EMOJIS),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "owner": st.session_state.username
        }
        st.session_state.current_list = list_id
        st.session_state.new_list_name = ""
        st.session_state.delete_confirmation = None
        save_data()

def add_task():
    """Add a new task to current list"""
    if (st.session_state.new_task and st.session_state.new_task.strip() and 
        st.session_state.current_list):
        task = {
            "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "text": st.session_state.new_task.strip(),
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "priority": st.session_state.new_task_priority,
            "emoji": random.choice(TASK_EMOJIS)
        }
        st.session_state.lists[st.session_state.current_list]["tasks"].append(task)
        st.session_state.new_task = ""
        save_data()

def toggle_task(list_id, task_id):
    """Toggle task completion status"""
    if list_id in st.session_state.lists:
        for task in st.session_state.lists[list_id]["tasks"]:
            if task["id"] == task_id:
                task["completed"] = not task["completed"]
                task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if task["completed"] else None
                break
        save_data()

def delete_task(list_id, task_id):
    """Delete a specific task"""
    if list_id in st.session_state.lists:
        st.session_state.lists[list_id]["tasks"] = [
            task for task in st.session_state.lists[list_id]["tasks"]
            if task["id"] != task_id
        ]
        save_data()

def clear_completed(list_id):
    """Remove all completed tasks from a list"""
    if list_id in st.session_state.lists:
        st.session_state.lists[list_id]["tasks"] = [
            task for task in st.session_state.lists[list_id]["tasks"]
            if not task["completed"]
        ]
        save_data()

def delete_list(list_id):
    """Delete an entire list"""
    if list_id in st.session_state.lists:
        del st.session_state.lists[list_id]
        if st.session_state.current_list == list_id:
            st.session_state.current_list = next(iter(st.session_state.lists.keys())) if st.session_state.lists else None
        st.session_state.delete_confirmation = None
        save_data()

def get_task_count(list_id):
    """Get task statistics for a list"""
    if list_id in st.session_state.lists:
        tasks = st.session_state.lists[list_id]["tasks"]
        total = len(tasks)
        completed = sum(1 for task in tasks if task["completed"])
        return total, completed
    return 0, 0

def create_priority_chart(list_id):
    """Create a pie chart showing task priority distribution"""
    if list_id in st.session_state.lists:
        tasks = st.session_state.lists[list_id]["tasks"]
        if not tasks:
            return None
            
        priorities = {"High": 0, "Medium": 0, "Low": 0}
        for task in tasks:
            priorities[task["priority"]] += 1
            
        df = pd.DataFrame({
            "Priority": ["High", "Medium", "Low"],
            "Count": [priorities["High"], priorities["Medium"], priorities["Low"]],
            "Color": ["#d32f2f", "#ffa000", "#2e7d32"]
        })
        
        fig = px.pie(
            df, 
            values="Count", 
            names="Priority",
            title="Task Priority Distribution",
            color="Priority",
            color_discrete_map={
                "High": "#d32f2f",
                "Medium": "#ffa000",
                "Low": "#2e7d32"
            }
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hole=0.4,
            marker=dict(line=dict(color='#ffffff', width=2))
        )
        
        fig.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
            height=300
        )
        
        return fig
    return None

def reset_database():
    """Reset the entire database"""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    initialize_state()
    st.success("Database reset successfully!")

def logout():
    """Handle logout"""
    st.session_state.authenticated = False
    st.session_state.username = None
    

# Initialize session state
initialize_state()

# App UI
st.set_page_config(page_title="Advanced To-Do App", page_icon="✅", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.05);
    }
    .task-completed {
        color: #2e7d32 !important;
    }
    .task-pending {
        color: #d32f2f !important;
    }
    .list-card {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        transition: all 0.3s ease;
    }
    .list-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .priority-high {
        border-left: 4px solid #d32f2f;
        padding-left: 8px;
    }
    .priority-medium {
        border-left: 4px solid #ffa000;
        padding-left: 8px;
    }
    .priority-low {
        border-left: 4px solid #2e7d32;
        padding-left: 8px;
    }
    .motivational-tip {
        font-style: italic;
        color: #555;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 5px;
        margin-top: 10px;
    }
    .confirmation-dialog {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .success-message {
        color: #2e7d32;
        font-weight: bold;
        padding: 10px;
        background-color: #e8f5e9;
        border-radius: 5px;
        margin: 10px 0;
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Check authentication
if not st.session_state.get("authenticated", False):
    st.title("To-Do App Login")

    # Init default tab
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "Login"

    # Handle registration success
    if st.session_state.get("register_success", False):
        st.session_state.register_success = False
        st.session_state.auth_tab = "Login"
        st.rerun()

    # Handle tab switch buttons
    if st.session_state.get("switch_to_register", False):
        st.session_state.auth_tab = "Register"
        st.session_state.switch_to_register = False
        st.rerun()

    if st.session_state.get("switch_to_login", False):
        st.session_state.auth_tab = "Login"
        st.session_state.switch_to_login = False
        st.rerun()

    # ----------------- LOGIN FORM -----------------
    if st.session_state.auth_tab == "Login":
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password")
                elif check_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        # Button to switch to Register
        if st.button("Don't have an account? Create one", type="secondary"):
            st.session_state.switch_to_register = True
            st.rerun()

    # ----------------- REGISTER FORM -----------------
    elif st.session_state.auth_tab == "Register":
        with st.form("register_form"):
            st.subheader("Register")
            username = st.text_input("Username", key="register_username")
            password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")
            submitted = st.form_submit_button("Register")

            if submitted:
                error = None
                if not username or not password:
                    error = "Please enter both username and password"
                elif len(username) < 3:
                    error = "Username must be at least 3 characters"
                elif password != confirm_password:
                    error = "Passwords do not match"
                elif len(password) < 4:
                    error = "Password must be at least 4 characters"
                elif username in st.session_state.users:
                    error = "Username already exists"

                if error:
                    st.error(error)
                else:
                    with st.spinner('Creating your account...'):
                        time.sleep(1.5)
                        st.session_state.users[username] = {
                            "password_hash": hash_password(password),
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        save_data()

                    st.success("✓ Registration successful! Redirecting to login...")
                    time.sleep(1.5)
                    st.session_state.register_success = True
                    st.rerun()

        # Button to switch to Login
        if st.button("Already have an account? Login", type="secondary"):
            st.session_state.switch_to_login = True
            st.rerun()

    st.stop()


# Main app (only visible if authenticated)
st.sidebar.title(f"Welcome, {st.session_state.username}!")
if st.sidebar.button("Logout", on_click=logout):
    pass

# Sidebar - Lists management
with st.sidebar:
    st.header("📋 My Lists")
    
    # Create new list
    with st.form("new_list_form"):
        st.text_input(
            "Create new list", 
            value=st.session_state.new_list_name,
            placeholder="Enter list name...",
            key="new_list_name",
            label_visibility="collapsed"
        )
        if st.form_submit_button("Create List", on_click=add_list):
            pass
    
    # Display all lists
    st.subheader("Your Lists")
    if not st.session_state.lists:
        st.info("No lists yet. Create one to get started!")
    
    # Filter lists owned by current user
    user_lists = {
        list_id: list_data for list_id, list_data in st.session_state.lists.items()
        if list_data.get("owner") == st.session_state.username
    }
    
    for list_id, list_data in user_lists.items():
        cols = st.columns([6, 1])
        with cols[0]:
            if st.button(
                f"{list_data['emoji']} {list_data['name']}",
                key=f"btn_{list_id}",
                use_container_width=True,
                type="primary" if list_id == st.session_state.current_list else "secondary"
            ):
                st.session_state.current_list = list_id
                st.session_state.delete_confirmation = None
        
        with cols[1]:
            if st.button("🗑️", key=f"del_btn_{list_id}"):
                st.session_state.delete_confirmation = list_id
        
        if st.session_state.delete_confirmation == list_id:
            with st.container():
                st.markdown('<div class="confirmation-dialog">Are you sure?</div>', unsafe_allow_html=True)
                cols_confirm = st.columns(2)
                with cols_confirm[0]:
                    if st.button("Yes", key=f"confirm_del_{list_id}", use_container_width=True):
                        delete_list(list_id)
                        st.rerun()
                with cols_confirm[1]:
                    if st.button("No", key=f"cancel_del_{list_id}", use_container_width=True):
                        st.session_state.delete_confirmation = None
        
        total, completed = get_task_count(list_id)
        st.caption(f"{completed}/{total} tasks completed")
    
    st.divider()
    st.caption("Advanced To-Do App v3.0")
    st.caption("Made with ❤️ using Streamlit")

# Main content - Tasks for selected list
if st.session_state.current_list and st.session_state.current_list in st.session_state.lists:
    current_list_data = st.session_state.lists[st.session_state.current_list]
    
    # Check if user owns this list
    if current_list_data.get("owner") != st.session_state.username:
        st.error("You don't have permission to access this list")
        st.session_state.current_list = None
        st.rerun()
    
    # List header
    cols = st.columns([1, 8, 1])
    with cols[0]:
        st.markdown(f"<h1>{current_list_data['emoji']}</h1>", unsafe_allow_html=True)
    with cols[1]:
        st.title(current_list_data["name"])
    with cols[2]:
        st.caption(f"Created: {current_list_data['created_at']}")
    
    # Add new task form
    with st.form("add_task_form"):
        cols = st.columns([5, 2, 1])
        with cols[0]:
            st.text_input(
                "Add a new task", 
                value=st.session_state.new_task,
                placeholder="What do you need to do?",
                key="new_task",
                label_visibility="collapsed"
            )
        with cols[1]:
            st.selectbox(
                "Priority",
                ["High", "Medium", "Low"],
                index=1,
                key="new_task_priority",
                label_visibility="collapsed"
            )
        with cols[2]:
            if st.form_submit_button("Add Task", on_click=add_task):
                pass
    
    # Task list
    if current_list_data["tasks"]:
        st.divider()
        
        # Filter options
        filter_cols = st.columns(3)
        with filter_cols[0]:
            st.checkbox("Show completed", value=st.session_state.show_completed, key="show_completed")
        with filter_cols[1]:
            st.checkbox("Show pending", value=st.session_state.show_pending, key="show_pending")
        with filter_cols[2]:
            st.selectbox(
                "Priority filter",
                ["All", "High", "Medium", "Low"],
                index=0,
                key="priority_filter"
            )
        
        filtered_tasks = [
            task for task in current_list_data["tasks"]
            if ((task["completed"] and st.session_state.show_completed) or 
                (not task["completed"] and st.session_state.show_pending))
            and (st.session_state.priority_filter == "All" or 
                 task["priority"] == st.session_state.priority_filter)
        ]
        
        if not filtered_tasks:
            st.info("No tasks match your filters")
        else:
            for task in filtered_tasks:
                priority_class = f"priority-{task['priority'].lower()}"
                with st.container():
                    cols = st.columns([1, 8, 1])
                    with cols[0]:
                        st.checkbox(
                            "",
                            value=task["completed"],
                            on_change=toggle_task,
                            args=(st.session_state.current_list, task["id"]),
                            key=f"check_{task['id']}",
                            label_visibility="collapsed"
                        )
                    with cols[1]:
                        if task["completed"]:
                            st.markdown(
                                f"""<div class="{priority_class}">
                                    <p class="task-completed">✅ {task['emoji']} {task['text']}
                                    </p>
                                    <p><small>Completed: {task.get('completed_at', 'Just now')} (Priority: {task['priority']})</small></p>
                                </div>""",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f"""<div class="{priority_class}">
                                    <p class="task-pending">{task['emoji']} {task['text']}</p>
                                    <p><small>Created: {task['created_at']} (Priority: {task['priority']})</small></p>
                                </div>""",
                                unsafe_allow_html=True
                            )
                    with cols[2]:
                        st.button(
                            "🗑️", 
                            key=f"del_task_{task['id']}",
                            on_click=delete_task,
                            args=(st.session_state.current_list, task["id"]),
                            use_container_width=True
                        )
                    st.divider()
        
        # List statistics and actions
        total_tasks = len(current_list_data["tasks"])
        completed_tasks = sum(1 for task in current_list_data["tasks"] if task["completed"])
        
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Tasks", total_tasks)
        with cols[1]:
            st.metric("Completed", f"{completed_tasks} ({int((completed_tasks/total_tasks)*100 if total_tasks else 0)}%)")
        with cols[2]:
            if completed_tasks > 0:
                if st.button("Clear Completed", use_container_width=True, 
                           on_click=clear_completed, args=(st.session_state.current_list,)):
                    pass
        with cols[3]:
            if st.button("Clear All Tasks", type="primary", use_container_width=True):
                st.session_state.lists[st.session_state.current_list]["tasks"] = []
                save_data()
                st.rerun()
        
        # Priority distribution chart
        if total_tasks > 0:
            st.divider()
            st.subheader("Task Priority Distribution")
            chart = create_priority_chart(st.session_state.current_list)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
    else:
        st.info("This list is empty. Add your first task above!")
else:
    st.info("No list selected or no lists available. Create a new list from the sidebar.")

# Motivational quotes
motivational_quotes = [
    "Productivity is doing what needs to be done when it needs to be done.",
    "Small daily improvements lead to stunning results.",
    "The way to get started is to quit talking and begin doing.",
    "Your time is limited, don't waste it living someone else's life.",
    "The secret of getting ahead is getting started."
]

if st.session_state.lists:
    st.divider()
    st.markdown(
        f'<div class="motivational-tip">💡 Motivational Tip: {random.choice(motivational_quotes)}</div>',
        unsafe_allow_html=True
    )

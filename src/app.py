"""
High School Management System API

A super simple FastAPI application that allows students to browse
extracurricular activities at Mergington High School while requiring
teacher authentication for registration management.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_COOKIE_NAME = "teacher_session"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
TEACHER_CONFIG_PATH = current_dir / "teachers.json"

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

class TeacherLoginRequest(BaseModel):
    username: str
    password: str


def load_teacher_credentials():
    with TEACHER_CONFIG_PATH.open(encoding="utf-8") as teacher_file:
        teacher_data = json.load(teacher_file)

    teachers = {}
    for teacher in teacher_data.get("teachers", []):
        username = teacher.get("username")
        password_hash = teacher.get("password_hash")
        salt = teacher.get("salt")

        if username and password_hash and salt:
            teachers[username] = {
                "password_hash": password_hash,
                "salt": salt,
                "iterations": int(teacher.get("iterations", 100000))
            }

    if not teachers:
        raise RuntimeError("No teacher credentials found in teachers.json")

    return teachers


def verify_teacher_password(password: str, teacher_record: dict):
    expected_hash = base64.b64decode(teacher_record["password_hash"])
    salt = base64.b64decode(teacher_record["salt"])
    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        teacher_record["iterations"]
    )
    return hmac.compare_digest(calculated_hash, expected_hash)


def require_teacher(request: Request):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    username = teacher_sessions.get(session_token)

    if not username:
        raise HTTPException(
            status_code=401,
            detail="Teacher login required for registration changes"
        )

    return username


teacher_credentials = load_teacher_credentials()
teacher_sessions = {}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/teacher/session")
def get_teacher_session(request: Request):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    username = teacher_sessions.get(session_token)
    return {"authenticated": bool(username), "username": username}


@app.post("/teacher/login")
def teacher_login(credentials: TeacherLoginRequest):
    teacher_record = teacher_credentials.get(credentials.username)

    if not teacher_record or not verify_teacher_password(
        credentials.password, teacher_record
    ):
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    session_token = secrets.token_urlsafe(32)
    teacher_sessions[session_token] = credentials.username

    response = JSONResponse(
        {"message": f"Logged in as {credentials.username}",
         "username": credentials.username}
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        max_age=SESSION_MAX_AGE_SECONDS,
        samesite="strict"
    )
    return response


@app.post("/teacher/logout")
def teacher_logout(request: Request):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        teacher_sessions.pop(session_token, None)

    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(
            status_code=400,
            detail="Activity is already at capacity"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}

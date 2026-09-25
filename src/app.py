"""
High School Management System API

A super simple FastAPI application that allows students to browse
extracurricular activities at Mergington High School while requiring
teacher authentication for registration management.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
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
TEACHER_CONFIG_PATH = Path(
    os.environ.get("TEACHER_CONFIG_PATH", current_dir / "teachers.json")
)

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
    if not TEACHER_CONFIG_PATH.exists():
        raise RuntimeError(
            "Teacher config not found. Copy src/teachers.example.json to "
            "src/teachers.json and add local teacher credentials."
        )

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


def build_session_signature(username: str, issued_at: int):
    payload = f"{username}:{issued_at}".encode("utf-8")
    return hmac.new(session_secret_key, payload, hashlib.sha256).hexdigest()


def create_session_token(username: str):
    issued_at = int(time.time())
    signature = build_session_signature(username, issued_at)
    token = f"{username}:{issued_at}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("utf-8")


def get_authenticated_teacher(request: Request):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None

    try:
        decoded_token = base64.urlsafe_b64decode(session_token.encode("utf-8"))
        username, issued_at, signature = decoded_token.decode("utf-8").split(":", 2)
        issued_at = int(issued_at)
    except (ValueError, TypeError, binascii.Error):
        return None

    if username not in teacher_credentials:
        return None

    expected_signature = build_session_signature(username, issued_at)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    if time.time() - issued_at > SESSION_MAX_AGE_SECONDS:
        return None

    return username


def require_teacher(request: Request):
    username = get_authenticated_teacher(request)

    if not username:
        raise HTTPException(
            status_code=401,
            detail="Teacher login required for registration changes"
        )

    return username


teacher_credentials = load_teacher_credentials()
session_secret_key = hashlib.sha256(
    TEACHER_CONFIG_PATH.read_bytes()
).digest()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/teacher/session")
def get_teacher_session(request: Request):
    username = get_authenticated_teacher(request)
    return {"authenticated": bool(username), "username": username}


@app.post("/teacher/login")
def teacher_login(credentials: TeacherLoginRequest, request: Request):
    teacher_record = teacher_credentials.get(credentials.username)

    if not teacher_record or not verify_teacher_password(
        credentials.password, teacher_record
    ):
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    session_token = create_session_token(credentials.username)

    response = JSONResponse(
        {"message": f"Logged in as {credentials.username}",
         "username": credentials.username}
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        max_age=SESSION_MAX_AGE_SECONDS,
        secure=request.url.scheme == "https",
        samesite="strict"
    )
    return response


@app.post("/teacher/logout")
def teacher_logout():
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

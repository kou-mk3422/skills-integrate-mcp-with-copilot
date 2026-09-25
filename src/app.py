"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import secrets
import sqlite3

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)
security = HTTPBasic()

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = Path(os.getenv("ACTIVITY_DB_PATH", current_dir / "activities.db"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "teacher")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SEED_ACTIVITIES = {
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


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL CHECK (max_participants > 0)
            );
            CREATE TABLE IF NOT EXISTS registrations (
                activity_id INTEGER NOT NULL REFERENCES activities(id),
                email TEXT NOT NULL,
                PRIMARY KEY (activity_id, email)
            );
            """
        )
        for name, details in SEED_ACTIVITIES.items():
            activity = connection.execute(
                "SELECT id FROM activities WHERE name = ?", (name,)
            ).fetchone()
            if activity is None:
                cursor = connection.execute(
                    "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                    (
                        name,
                        details["description"],
                        details["schedule"],
                        details["max_participants"],
                    ),
                )
                activity_id = cursor.lastrowid
                connection.executemany(
                    "INSERT INTO registrations (activity_id, email) VALUES (?, ?)",
                    [(activity_id, email) for email in details["participants"]],
                )


initialize_database()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    valid_password = ADMIN_PASSWORD is not None and secrets.compare_digest(
        credentials.password, ADMIN_PASSWORD
    )
    valid_user = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid teacher credentials are required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT a.name, a.description, a.schedule, a.max_participants,
                   COALESCE(GROUP_CONCAT(r.email), '') AS participant_emails
            FROM activities AS a
            LEFT JOIN registrations AS r ON r.activity_id = a.id
            GROUP BY a.id
            ORDER BY a.name
            """
        ).fetchall()
    return {
        row["name"]: {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": row["participant_emails"].split(",")
            if row["participant_emails"]
            else [],
        }
        for row in rows
    }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _admin: str = Depends(require_admin)
):
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        activity = connection.execute(
            "SELECT id, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        existing = connection.execute(
            "SELECT 1 FROM registrations WHERE activity_id = ? AND email = ?",
            (activity["id"], email),
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=400, detail="Student is already signed up")
        registered = connection.execute(
            "SELECT COUNT(*) AS count FROM registrations WHERE activity_id = ?",
            (activity["id"],),
        ).fetchone()["count"]
        if registered >= activity["max_participants"]:
            raise HTTPException(status_code=409, detail="Activity is full")
        connection.execute(
            "INSERT INTO registrations (activity_id, email) VALUES (?, ?)",
            (activity["id"], email),
        )
        remaining = activity["max_participants"] - registered - 1
    return {
        "message": f"Signed up {email} for {activity_name}",
        "remaining_capacity": remaining,
    }


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _admin: str = Depends(require_admin)
):
    with get_connection() as connection:
        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ?", (activity_name,)
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        result = connection.execute(
            "DELETE FROM registrations WHERE activity_id = ? AND email = ?",
            (activity["id"], email),
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity",
            )
    return {"message": f"Unregistered {email} from {activity_name}"}

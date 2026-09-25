# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Persist activities and registrations in SQLite
- Require teacher authentication for registration changes
- Enforce activity capacity atomically

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   ADMIN_PASSWORD=change-this-password uvicorn app:app --reload
   ```

   `ADMIN_USERNAME` defaults to `teacher`. Set `ACTIVITY_DB_PATH` to choose a
   different SQLite database location.

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity (teacher authentication required)           |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remove a registration (teacher authentication required)          |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activities and registrations are stored in SQLite, so registrations survive
server restarts. The default database file is `src/activities.db`.

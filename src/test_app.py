import copy
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).parent))


class TeacherAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(dir="/tmp")
        cls.teacher_config_path = Path(cls.temp_dir.name) / "teachers.json"
        cls.teacher_config_path.write_text(
            json.dumps(
                {
                    "teachers": [
                        {
                            "username": "teacher",
                            "password_hash": "N6qZ48USETr9eKpwYjbkzzZo709WDGGZszmTtXFBwDg=",
                            "salt": "mydJTzIPsNHus6ET24a6+A==",
                            "iterations": 100000,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        os.environ["TEACHER_CONFIG_PATH"] = str(cls.teacher_config_path)
        os.environ["SESSION_SECRET_KEY"] = "test-session-secret"

        import app as app_module

        cls.app_module = importlib.reload(app_module)
        cls.original_activities = copy.deepcopy(cls.app_module.activities)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("TEACHER_CONFIG_PATH", None)
        os.environ.pop("SESSION_SECRET_KEY", None)
        cls.temp_dir.cleanup()

    def setUp(self):
        self.app_module.activities.clear()
        self.app_module.activities.update(copy.deepcopy(self.original_activities))
 
    def make_request(self, cookies=None):
        headers = []
        if cookies:
            cookie_header = "; ".join(
                f"{name}={value}" for name, value in cookies.items()
            ).encode("utf-8")
            headers.append((b"cookie", cookie_header))

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "headers": headers,
                "scheme": "http",
            }
        )

    def test_students_cannot_signup_without_teacher_login(self):
        with self.assertRaises(self.app_module.HTTPException) as context:
            self.app_module.signup_for_activity(
                "Chess Club",
                "student@mergington.edu",
                self.make_request(),
            )

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(
            context.exception.detail,
            "Teacher login required for registration changes",
        )

    def test_teacher_cannot_signup_when_activity_is_full(self):
        activity = self.app_module.activities["Chess Club"]
        activity["participants"] = [
            f"student{i}@mergington.edu"
            for i in range(activity["max_participants"])
        ]

        request = self.make_request(
            {"teacher_session": self.app_module.create_session_token("teacher")}
        )

        with self.assertRaises(self.app_module.HTTPException) as context:
            self.app_module.signup_for_activity(
                "Chess Club",
                "overflow@mergington.edu",
                request,
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail,
            "Activity is already at capacity",
        )

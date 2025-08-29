# screen_tracker.py
import cv2
import numpy as np
import pyautogui
import pytesseract
import time
import psycopg2
import requests
import json
from datetime import datetime
import psutil
import win32gui
import win32process
from PIL import Image, ImageGrab
from dataclasses import dataclass
from typing import List, Dict, Optional
import os
from urllib.parse import urlparse
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

@dataclass
class ActivitySession:
    start_time: datetime
    end_time: Optional[datetime]
    application: str
    window_title: str
    screenshot_path: str
    extracted_text: str
    # ai_response: str
    ai_analysis: Dict
    client_identified: Optional[str]
    category: str
    productivity_score: int
    user_id: int

class AITimeTracker:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.is_tracking = False
        self.current_session = None
        self.screenshot_interval = 30
        self.current_user_id: Optional[int] = None
        self.init_database()

    def db(self):
        return psycopg2.connect(DATABASE_URL)

    def init_database(self):
        conn = self.db()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT CHECK(role IN ('employee','admin')) NOT NULL DEFAULT 'employee'
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            application TEXT,
            window_title TEXT,
            screenshot_path TEXT,
            extracted_text TEXT,
            ai_analysis JSONB,
            client_identified TEXT,
            category TEXT,
            productivity_score INTEGER,
            duration_minutes INTEGER
        )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            contact_email VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)


        conn.commit()
        cur.close()
        conn.close()

    def match_client(self, client_name: str) -> str:
        if not client_name:
            return "None"

        try:
            conn = self.db()
            cur = conn.cursor()
            
            # Case-insensitive match against clients table
            cur.execute("SELECT name FROM clients WHERE LOWER(name) = LOWER(%s) LIMIT 1;", (client_name,))
            result = cur.fetchone()

            cur.close()
            conn.close()

            return result[0] if result else "None"
        except Exception as e:
            print("DB Error in match_client:", str(e))
            return "None"



    def get_active_window_info(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return {"application": process.name(), "window_title": window_title}
        except Exception:
            return {"application": "Unknown", "window_title": "Unknown"}

    def capture_screenshot(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("screenshots", exist_ok=True)
        path = f"screenshots/screenshot_{timestamp}.png"
        ImageGrab.grab().save(path)
        return path

    def extract_text_from_screen(self, screenshot_path: str) -> str:
        try:
            image = Image.open(screenshot_path)
            return pytesseract.image_to_string(image, lang='eng').strip()
        except Exception:
            return ""

    # def analyze_content_with_gpt(self, window_info: Dict, extracted_text: str) -> Dict:
    #     try:
    #         prompt = f"""
    #         Application: {window_info['application']}
    #         Window Title: {window_info['window_title']}
    #         Extracted Text: {extracted_text[:2000]}
    #         Return JSON with: client_name, activity_type, productivity_level,
    #         description, project_or_task, category
    #         """
    #         headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    #         data = {
    #             "model": "gpt-3.5-turbo",
    #             "messages": [
    #                 {"role": "system", "content": "You analyze workplace activities."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             "max_tokens": 300,
    #             "temperature": 0.3
    #         }
    #         resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
    #         if resp.status_code == 200:
    #             try:
    #                 return json.loads(resp.json()['choices'][0]['message']['content'])
    #             except:
    #                 return {"client_name": "Unknown", "activity_type": "general_work", "productivity_level": 5, "description": "Unknown", "project_or_task": "Unknown", "category": "Work"}
    #         return self.get_fallback_analysis(window_info)
    #     except:
    #         return self.get_fallback_analysis(window_info)

    def analyze_content_with_gpt(self, window_info: Dict, extracted_text: str, manual_override: bool = False):
        try:
            if manual_override:
                # 🔥 For manual entries, only ask for AI-driven fields
                prompt = f"""
                You are an AI that analyzes user activity for productivity tracking.

                Application: {window_info.get('application', '')}
                Window Title: {window_info.get('window_title', '')}
                Extracted Text: {extracted_text[:2000]}

                Return ONLY a JSON object with the following keys:
                - activity_type (string)
                - productivity_level (integer from 1–10)
                - category (string: Work, Communication, Research, Social, Idle/Leisure, etc.)

                Example:
                {{
                    "activity_type": "coding",
                    "productivity_level": 9,
                    "category": "Work"
                }}
                """
            
            else:
                prompt = f"""
                You are an AI that analyzes user activity for productivity tracking.

                Application: {window_info.get('application', '')}
                Window Title: {window_info.get('window_title', '')}
                Extracted Text: {extracted_text[:2000]}

                Return ONLY a JSON object with the following keys:
                - client_name (string)
                - activity_type (string)
                - productivity_level (integer from 1–10, where 1 = unproductive/idle, 10 = highly productive. 
                  If the user is coding, designing, writing documents, attending meetings → score 7–10. 
                  If browsing social media, YouTube, or unrelated apps → score 0–2. 
                  If ambiguous but seems work-related (e.g., Chrome tab with project context) → default to 7.)
                - description (string)
                - project_or_task (string)
                - category (string: Work, Communication, Research, Social, Idle/Leisure, etc.)

                Example:
                {{
                    "client_name": "Acme Corp",
                    "activity_type": "coding",
                    "productivity_level": 9,
                    "description": "User is writing Python code in VSCode",
                    "project_or_task": "Backend API development",
                    "category": "Work"
                }}

                Return only ONE JSON object with fields: client_name, activity_type, productivity_level, description, project_or_task, category.
                Do not return an array or multiple objects.
                """

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": "You analyze workplace activities and must always return strict JSON."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.2  # lower → more consistent JSON
            }

            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            print("##########################################")
            print(resp.status_code)
            ai_response = resp.json()["choices"][0]["message"]["content"]
            print(ai_response)

            if resp.status_code == 200:
                try:
                    # ✅ Use AI JSON directly
                    ai_analysis = json.loads(ai_response)
                    # 🔥 If it's a list, take the first element
                    if isinstance(ai_analysis, list) and len(ai_analysis) > 0:
                        ai_analysis = ai_analysis[0]
                    # ✅ Validate client name
                    ai_analysis["client_name"] = self.match_client(ai_analysis.get("client_name"))
                    return ai_analysis, ai_response
                except Exception:
                    # If LLM didn’t return proper JSON, fallback
                    return self.get_fallback_analysis(window_info), ai_response

            return self.get_fallback_analysis(window_info), ai_response

        except Exception as e:
            print("LLM Exception:", str(e))
            return self.get_fallback_analysis(window_info), "Some Exception"



    def get_fallback_analysis(self, window_info: Dict) -> Dict:
        app = (window_info['application'] or "").lower()
        if "word" in app or "excel" in app:
            return {"client_name": "None", "activity_type": "document_editing", "productivity_level": 8, "description": f"Working with {app}", "project_or_task": "Unknown", "category": "Work"}
        return {"client_name": "None", "activity_type": "general_work", "productivity_level": 5, "description": f"Working with {app}", "project_or_task": "Unknown", "category": "Work"}

    def save_session(self, session: ActivitySession):
        conn = self.db()
        cur = conn.cursor()
        duration = 0
        if session.end_time and session.start_time:
            duration = int((session.end_time - session.start_time).total_seconds() / 60)
        cur.execute("""
        INSERT INTO activities (user_id, start_time, end_time, application, window_title, screenshot_path, extracted_text, ai_analysis, client_identified, category, productivity_score, duration_minutes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session.user_id,
            session.start_time,
            session.end_time,
            session.application,
            session.window_title,
            session.screenshot_path,
            session.extracted_text,
            json.dumps(session.ai_analysis),
            session.client_identified,
            session.category,
            session.productivity_score,
            duration
        ))
        conn.commit()
        cur.close()
        conn.close()

    def start_tracking_for_user(self, user_id: int):
        self.current_user_id = user_id
        self.start_tracking()

    def start_tracking(self):
        self.is_tracking = True
        while self.is_tracking:
            window_info = self.get_active_window_info()
            if not self.current_session or self.current_session.window_title != window_info['window_title']:
                if self.current_session:
                    self.current_session.end_time = datetime.now()
                    self.save_session(self.current_session)
                screenshot_path = self.capture_screenshot()
                print("Screenshot Saved.")
                extracted_text = self.extract_text_from_screen(screenshot_path)
                ai_analysis, ai_response = self.analyze_content_with_gpt(window_info, extracted_text)
                print("AI ANALYSIS: *****************************")
                print(ai_analysis)
                print("AI RESPONSE: ^^^^^^^^^^^^^^^^^^")
                print(ai_response)
                self.current_session = ActivitySession(
                    start_time=datetime.now(),
                    end_time=None,
                    application=window_info['application'],
                    window_title=window_info['window_title'],
                    screenshot_path=screenshot_path,
                    extracted_text=extracted_text,
                    # ai_response=ai_response,
                    ai_analysis=ai_analysis,
                    client_identified = ai_analysis.get("client_name", "None") if isinstance(ai_analysis, dict) else "None",
                    category=ai_analysis.get("category", "Work"),
                    productivity_score=ai_analysis.get("productivity_level", 5),
                    user_id=self.current_user_id or 0
                )
            time.sleep(self.screenshot_interval)

    def stop_tracking(self):
        self.is_tracking = False

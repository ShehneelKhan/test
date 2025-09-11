# api_server.py
import os
import psycopg2
import threading
from datetime import datetime, timedelta
from typing import Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from .screen_tracker import AITimeTracker, ActivitySession #Enter dot for deployment
import json
# from api_server import AITimeTracker
from jose.exceptions import ExpiredSignatureError

# print("Debug message", flush=True)


# ====== Config ======
load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET", "change_this_dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 8 * 60  # 8 hours
DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql://user:pass@localhost:5432/dbname
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")

# ====== Auth setup ======
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ====== FastAPI ======
app = FastAPI(title="AI Time Tracker (Multi-User)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # update if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check if the 'screenshots' directory exists and mount the static files
if os.path.isdir("screenshots"):
    print("Screenshots directory found. Mounting static files...")
    app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")
else:
    print("Screenshots directory not found!")

# ====== Tracker (single instance per machine) ======
tracker = AITimeTracker()  # removed db_path param
tracking_thread: Optional[threading.Thread] = None

# ====== DB helpers ======
def db():
    return psycopg2.connect(DATABASE_URL)

def init_admin_seed():
    """Seed an admin if none exists."""
    conn = db()
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
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            ("Admin", "admin@example.com", pwd_context.hash("admin123"), "admin")
        )
        conn.commit()
        print("Seeded default admin: admin@example.com / admin123")
    cur.close()
    conn.close()

init_admin_seed()

# ====== Schemas ======
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "employee"

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ClientCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None


# ====== Auth utils ======
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(pw):
    return pwd_context.hash(pw)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(email: str):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash, role FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_user_by_id(user_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash, role FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if uid is None:
            raise credentials_exc
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, please log in again",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError:
        raise credentials_exc

    row = get_user_by_id(int(uid))
    if not row:
        raise credentials_exc
    return UserOut(id=row[0], name=row[1], email=row[2], role=row[4])


def require_admin(current_user: UserOut = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only"
        )
    return current_user


# ====== Auth endpoints ======
@app.post("/api/register")
def register_user(payload: RegisterIn):
    # require_admin(current_user)
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (payload.name, payload.email, hash_password(payload.password), payload.role)
        )
        uid = cur.fetchone()[0]
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    cur.close()
    conn.close()
    return UserOut(id=uid, name=payload.name, email=payload.email, role=payload.role)

@app.post("/api/login", response_model=TokenOut)
def login(payload: LoginRequest):
    row = get_user_by_email(payload.username)
    if not row or not verify_password(payload.password, row[3]):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    token = create_access_token({"sub": str(row[0]), "role": row[4]})
    return TokenOut(access_token=token, role=row[4])

@app.post("/api/logout")
def logout(current_user: UserOut = Depends(get_current_user)):
    """
    Logout endpoint — since JWTs are stateless, this just tells frontend to clear token.
    """
    return {"status": "logged_out"}


@app.get("/api/me", response_model=UserOut)
def me(current_user: UserOut = Depends(get_current_user)):
    return current_user

# ====== Tracking endpoints ======
@app.post("/api/start-tracking")
def start_tracking(current_user: UserOut = Depends(get_current_user)):
    global tracking_thread
    if tracker.is_tracking and tracker.current_user_id == current_user.id:
        return {"status": "already_running_for_this_user"}

    if tracker.is_tracking and tracker.current_user_id != current_user.id:
        tracker.stop_tracking()

    def run():
        tracker.start_tracking_for_user(current_user.id)

    tracking_thread = threading.Thread(target=run, daemon=True)
    tracking_thread.start()
    return {"status": "tracking_started", "user_id": current_user.id}

@app.post("/api/stop-tracking")
def stop_tracking(current_user: UserOut = Depends(get_current_user)):
    if not tracker.is_tracking:
        return {"status": "not_running"}
    if tracker.current_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can't stop another user's tracker")
    tracker.stop_tracking()
    print("Tracker stopped by user ID:", current_user.id)
    return {"status": "tracking_stopped"}

@app.get("/api/tracking-status")
def tracking_status(current_user: UserOut = Depends(get_current_user)):
    return {
        "is_tracking": tracker.is_tracking,
        "current_user_id": tracker.current_user_id
    }




# ====== Data endpoints ======
@app.get("/api/activities")
def get_activities(
    date: str = Query(..., description="YYYY-MM-DD"),
    user_id: Optional[int] = Query(None, description="Admin only: view someone else"),
    current_user: UserOut = Depends(get_current_user)
):
    print("Started get_activities...")
    target_user_id = current_user.id
    print("Filtering for User ID = {}, Date = {}".format(target_user_id, date))

    if user_id is not None:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required to view other users")
        target_user_id = user_id

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, start_time, end_time, application, window_title,
               screenshot_path, ai_analysis, client_identified,
               category, productivity_score,
               ROUND(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) / 60.0, 2) AS duration_minutes,
               status, entry_type
        FROM activities
        WHERE user_id = %s AND DATE(start_time) = %s
        ORDER BY start_time
    """, (target_user_id, date))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    columns = [
        'id','user_id','start_time','end_time','application','window_title',
        'screenshot_path','ai_analysis','client_identified',
        'category','productivity_score','duration_minutes','status', 'entry_type'
    ]

    results = []
    for r in rows:
        rec = dict(zip(columns, r))

        # Ensure ai_analysis is always a JSON object
        if rec["ai_analysis"] is None:
            rec["ai_analysis"] = {}
        elif isinstance(rec["ai_analysis"], str):
            try:
                rec["ai_analysis"] = json.loads(rec["ai_analysis"])
            except:
                rec["ai_analysis"] = {}

        # Normalize client_identified
        if isinstance(rec["client_identified"], dict):
            rec["client_identified"] = rec["client_identified"].get("client_name", "None")

        # Fix productivity_score
        try:
            rec["productivity_score"] = int(rec["productivity_score"])
        except:
            rec["productivity_score"] = 5

        # Round duration safely (if SQL didn’t handle it for some reason)
        if rec["duration_minutes"] is not None:
            rec["duration_minutes"] = round(float(rec["duration_minutes"]), 2)
        else:
            rec["duration_minutes"] = 0.0

        results.append(rec)

    print("Ended get_activities")
    return results



#### ADD CLIENTS #####
@app.post("/api/clients")
def add_client(client: ClientCreate, current_user: UserOut = Depends(get_current_user)):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clients (name, contact_email) VALUES (%s, %s) RETURNING id",
        (client.name, client.contact_email)
    )
    client_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": client_id, "name": client.name, "contact_email": client.contact_email}


@app.get("/api/clients")
def list_clients(current_user: UserOut = Depends(get_current_user)):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, contact_email FROM clients ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "name": r[1], "contact_email": r[2]} for r in rows]

from fastapi import HTTPException, Path

@app.put("/api/clients/{client_id}")
def update_client(client_id: int, client: ClientCreate, current_user: UserOut = Depends(get_current_user)):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE clients SET name=%s, contact_email=%s WHERE id=%s",
                (client.name, client.contact_email, client_id))
    conn.commit()
    cur.close()
    conn.close()
    return {"id": client_id, "name": client.name, "contact_email": client.contact_email}

@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int, current_user: UserOut = Depends(get_current_user)):
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM clients WHERE id=%s", (client_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "success"}




@app.get("/api/clients-summary")
def clients_summary(
    date: str = Query(..., description="YYYY-MM-DD"),
    user_id: Optional[int] = Query(None),
    current_user: UserOut = Depends(get_current_user)
):
    target_user_id = current_user.id
    if user_id is not None:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        target_user_id = user_id

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(client_identified, 'None') AS client, 
               COALESCE(SUM(duration_minutes),0) AS minutes
        FROM activities
        WHERE user_id = %s AND DATE(start_time) = %s
        GROUP BY client
        ORDER BY minutes DESC
    """, (target_user_id, date))
    data = [{"client": r[0], "minutes": r[1]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return data


from fastapi import Body


@app.post("/api/manual-entry")
def manual_entry(payload: dict = Body(...), current_user: UserOut = Depends(get_current_user)):
    # ✅ Validation
    # if not payload.get("clientName"):
    #     raise HTTPException(status_code=400, detail="Client is required")
    if not payload.get("description"):
        raise HTTPException(status_code=400, detail="Description is required")
    if not payload.get("application"):
        raise HTTPException(status_code=400, detail="Application is required")
    if not payload.get("project_task"):
        raise HTTPException(status_code=400, detail="Project / Task is required")
    if not payload.get("duration"):
        raise HTTPException(status_code=400, detail="Duration is required")

    conn = db()
    cur = conn.cursor()

    # ✅ Duration in minutes
    try:
        duration_minutes = round(float(payload["duration"]) * 60, 2)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duration")

    if duration_minutes <= 0:
        raise HTTPException(status_code=400, detail="Duration must be greater than 0")
    if duration_minutes > 1440:  # ✅ no more than 24h
        raise HTTPException(status_code=400, detail="Duration cannot exceed 24 hours")


    # ✅ Combine date + startTime
    start_time = datetime.strptime(
        f"{payload['date']} {payload.get('startTime','09:00')}:00", 
        "%Y-%m-%d %H:%M:%S"
    )

    if start_time.date() != datetime.utcnow().date():
        raise HTTPException(status_code=400, detail="Date must be today's date only")

    end_time = start_time + timedelta(minutes=duration_minutes)

    status = payload.get("status", "In Progress")

    # 🔥 Step 0: Check for duplicate entry at same time for same user
    cur.execute("""
        SELECT id, start_time, end_time
        FROM activities
        WHERE user_id = %s
          AND (
                (start_time <= %s AND end_time > %s) OR
                (start_time < %s AND end_time >= %s) OR
                (start_time >= %s AND end_time <= %s)
              )
    """, (
        current_user.id,
        start_time, start_time,   # overlap at start
        end_time, end_time,       # overlap at end
        start_time, end_time      # contained within
    ))
    conflict = cur.fetchone()
    if conflict:
        cur.close()
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"⛔ Time conflict: overlaps with an existing task from {conflict[1]} to {conflict[2]}"
        )

    # ✅ Step 1: Ask LLM only for AI fields
    gpt = AITimeTracker()
    ai_analysis, raw_ai_response = gpt.analyze_content_with_gpt(
        {"application": payload["application"], "window_title": payload["description"]},
        payload["description"],
        manual_override=True   # only return activity_type, productivity_level, category
    )

    print("Payload from manual form frontend: ", payload)

    # ✅ Step 2: Force manual fields override
    merged_ai = {
        "client_name": payload["clientName"],             # User input only
        "description": payload["description"],            # User input only
        "project_or_task": payload["project_task"],       # User input only
        "activity_type": ai_analysis.get("activity_type", ""),   # LLM
        "productivity_level": ai_analysis.get("productivity_level", 7), # LLM
        "category": ai_analysis.get("category", "Work")   # LLM
    }

    # ✅ Step 3: Force same overrides inside `ai_response` (so frontend shows correctly)
    clean_ai_response = json.dumps(merged_ai, indent=2)
    print("Cleaned AI Response to store in DB:", clean_ai_response)

    # ✅ Step 4: Insert into DB
    cur.execute("""
        INSERT INTO activities 
        (user_id, client_identified, duration_minutes, start_time, end_time,
         ai_analysis, category, productivity_score, status, application, entry_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        current_user.id,
        payload["clientName"],
        duration_minutes,
        start_time,
        end_time,
        json.dumps(merged_ai),     # merged JSON (always correct)
        merged_ai["category"],
        merged_ai["productivity_level"],
        status,
        payload["application"],
        # clean_ai_response,          # 🔥 now matches merged_ai, not raw LLM
        "Manual Entry"
    ))

    act_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return {"id": act_id, "status": "success", "ai_analysis": merged_ai}



##################### ADMIN MODULE ###########################

from typing import List

def require_admin(current_user: UserOut = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only"
        )
    return current_user

# ✅ Admin-only endpoint to fetch all users
@app.get("/api/admin/users", response_model=List[UserOut])
def get_all_users(current_user: UserOut = Depends(require_admin)):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role FROM users ORDER BY id ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [UserOut(id=r[0], name=r[1], email=r[2], role=r[3]) for r in rows]


@app.get("/api/admin/users/{user_id}/activities")
def get_user_activities(user_id: int, current_user: UserOut = Depends(require_admin)):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, start_time, end_time, client_identified, ai_analysis, category, 
               productivity_score, application, window_title, status, entry_type,
               ROUND(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) / 60.0, 2) AS duration_minutes
        FROM activities
        WHERE user_id = %s
        ORDER BY start_time DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    activities = []
    for r in rows:
        rec = {
            "id": r[0],
            "start_time": r[1],
            "end_time": r[2],
            "client_identified": r[3],
            "ai_analysis": r[4],
            "category": r[5],
            "productivity_score": r[6],
            "application": r[7],
            "window_title": r[8],
            "status": r[9],
            "entry_type": r[10],
            "duration_minutes": r[11],
        }

        # --- normalize ai_analysis like in /api/activities ---
        if rec["ai_analysis"] is None:
            rec["ai_analysis"] = {}
        elif isinstance(rec["ai_analysis"], str):
            try:
                rec["ai_analysis"] = json.loads(rec["ai_analysis"])
            except:
                rec["ai_analysis"] = {}

        # normalize client_identified
        if isinstance(rec["client_identified"], dict):
            rec["client_identified"] = rec["client_identified"].get("client_name", "None")

        # fix productivity score
        try:
            rec["productivity_score"] = int(rec["productivity_score"])
        except:
            rec["productivity_score"] = 5

        # fix duration
        if rec["duration_minutes"] is not None:
            rec["duration_minutes"] = round(float(rec["duration_minutes"]), 2)
        else:
            rec["duration_minutes"] = 0.0

        activities.append(rec)

    return activities



from decimal import Decimal

@app.get("/api/admin/users/{user_id}/summary")
def get_user_summary(user_id: int, date: str, current_user: UserOut = Depends(require_admin)):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COALESCE(SUM(duration_minutes),0) AS total_minutes,
            COALESCE(AVG(productivity_score),0) AS avg_productivity,
            COUNT(*) AS task_count
        FROM activities
        WHERE user_id = %s AND DATE(start_time) = %s
    """, (user_id, date))
    row = cur.fetchone()

    # convert Decimals to float
    total_minutes = float(row[0]) if isinstance(row[0], Decimal) else row[0]
    avg_productivity = float(row[1]) if isinstance(row[1], Decimal) else row[1]

    # count distinct clients
    cur.execute("""
        SELECT COUNT(DISTINCT client_identified)
        FROM activities
        WHERE user_id = %s AND DATE(start_time) = %s AND client_identified IS NOT NULL
    """, (user_id, date))
    client_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total_hours": round(total_minutes / 60.0, 2),
        "avg_productivity": round(avg_productivity, 1) if avg_productivity else 0,
        "task_count": row[2],
        "clients_count": client_count
    }


@app.get("/api/admin/users/{user_id}/activities-by-date")
def get_user_activities_by_date(user_id: int, date: str, current_user: UserOut = Depends(require_admin)):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, start_time, end_time, client_identified, ai_analysis, category, 
               productivity_score, application, window_title, status, entry_type,
               ROUND(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) / 60.0, 2) AS duration_minutes
        FROM activities
        WHERE user_id = %s AND DATE(start_time) = %s
        ORDER BY start_time
    """, (user_id, date))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    activities = []
    for r in rows:
        # ✅ normalize ai_analysis
        raw_ai = r[4]
        if not raw_ai:
            ai_analysis = {}
        elif isinstance(raw_ai, dict):
            ai_analysis = raw_ai
        elif isinstance(raw_ai, str):
            try:
                ai_analysis = json.loads(raw_ai)
            except Exception:
                ai_analysis = {}
        else:
            ai_analysis = {}

        activities.append({
            "id": r[0],
            "start_time": r[1],
            "end_time": r[2],
            "client_identified": r[3],
            "ai_analysis": ai_analysis,
            "category": r[5],
            "productivity_score": r[6],
            "application": r[7],
            "window_title": r[8],
            "status": r[9],
            "entry_type": r[10],
            "duration_minutes": r[11],
        })
    return activities


from datetime import datetime, timedelta

@app.get("/api/admin/users/{user_id}/weekly-report")
def get_weekly_report(user_id: int, current_user: UserOut = Depends(require_admin)):
    conn = db()
    cur = conn.cursor()

    # Fetch user info
    cur.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
    user_row = cur.fetchone()
    username = user_row[0] if user_row else f"User {user_id}"

    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)

    # Fetch activities
    cur.execute("""
        SELECT start_time, end_time, client_identified, ai_analysis, category,
               productivity_score,
               ROUND(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) / 60.0, 2) AS duration_minutes
        FROM activities
        WHERE user_id = %s AND DATE(start_time) BETWEEN %s AND %s
        ORDER BY start_time
    """, (user_id, week_start, week_end))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    total_time = 0
    productive_time = 0
    productivity_scores = []
    client_count = {}
    category_time = {}
    daily_time = {d.strftime("%a"): 0 for d in [week_start + timedelta(days=i) for i in range(7)]}

    for r in rows:
        start_time, end_time, client_identified, raw_ai, category, prod_score, duration = r
        duration = duration or 0
        total_time += duration
        if prod_score and prod_score >= 7:
            productive_time += duration
        if prod_score:
            productivity_scores.append(prod_score)

        # Client frequency
        if client_identified and client_identified != "None":
            client_count[client_identified] = client_count.get(client_identified, 0) + 1

        # Category breakdown
        if category:
            category_time[category] = category_time.get(category, 0) + duration

        # Daily breakdown
        day_name = start_time.strftime("%a")
        daily_time[day_name] += duration

    avg_productivity = round(sum(productivity_scores) / len(productivity_scores), 2) if productivity_scores else 0
    top_clients = sorted(client_count.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "summary": {
            "total_hours": round(total_time / 60, 2),
            "productive_hours": round(productive_time / 60, 2),
            "avg_productivity": avg_productivity,
            "top_clients": top_clients,
        },
        "category_breakdown": category_time,
        "daily_breakdown": daily_time,
        "username": username,
    }


@app.get("/api/admin/users/{user_id}/screenshots-by-date")
def get_user_screenshots_by_date(user_id: int, date: str, current_user: UserOut = Depends(require_admin)):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, path, taken_at, activity_id
        FROM screenshots
        WHERE user_id = %s AND DATE(taken_at) = %s
        ORDER BY taken_at
    """, (user_id, date))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "path": r[1],
            "taken_at": r[2],
            "activity_id": r[3],
        }
        for r in rows
    ]



from fastapi import File, UploadFile, Form

@app.post("/api/upload-screenshot")
async def upload_screenshot(
    screenshot: UploadFile = File(...),
    application: str = Form(...),
    window_title: str = Form(...),
    timestamp: str = Form(...),
    current_user: UserOut = Depends(get_current_user)
):
    try:
        # Ensure the screenshots directory exists
        os.makedirs("screenshots", exist_ok=True)
        file_path = f"screenshots/{timestamp}_{screenshot.filename}"

        # Log the file path for debugging
        print(f"Saving screenshot to: {file_path}")

        # Save the screenshot
        with open(file_path, "wb") as f:
            f.write(await screenshot.read())
        
        # Log after file is saved
        print(f"Screenshot saved successfully to: {file_path}")

        # Run AI analysis
        # print("Running AI analysis...")
        extracted_text = tracker.extract_text_from_screen(file_path)
        ai_analysis, ai_response = tracker.analyze_content_with_gpt(
            {"application": application, "window_title": window_title},
            extracted_text
        )

        # print(f"AI analysis complete: {ai_analysis}")

        # Connect to the database
        conn = db()
        cur = conn.cursor()

        # Log the SQL query execution
        # print("Checking the last activity for the user...")
        # 🔍 Check last activity for this user
        cur.execute("""
            SELECT id, application, window_title, end_time
            FROM activities
            WHERE user_id = %s
            ORDER BY start_time DESC
            LIMIT 1
        """, (current_user.id,))
        last_activity = cur.fetchone()

        if last_activity and last_activity[1] == application and last_activity[2] == window_title:
            # ✅ Same window → just update end_time + duration
            activity_id = last_activity[0]
            # print(f"Updating existing activity (ID: {activity_id})...")
            cur.execute("""
                UPDATE activities
                SET end_time = NOW(),
                    duration_minutes = ROUND(EXTRACT(EPOCH FROM (NOW() - start_time)) / 60.0, 2),
                    screenshot_path = %s,
                    ai_analysis = %s,
                    client_identified = %s,
                    category = %s,
                    productivity_score = %s
                WHERE id = %s
            """, (
                file_path,
                json.dumps(ai_analysis),
                ai_analysis.get("client_name", "None"),
                ai_analysis.get("category", "Work"),
                ai_analysis.get("productivity_level", 5),
                activity_id
            ))
            # print(f"Activity {activity_id} updated.")
        else:
            # 🆕 New window → close the previous activity (if any)
            if last_activity and last_activity[3] is None:
                # print(f"Closing last activity (ID: {last_activity[0]}) due to new window...")
                cur.execute("""
                    UPDATE activities
                    SET end_time = NOW(),
                        duration_minutes = ROUND(EXTRACT(EPOCH FROM (NOW() - start_time)) / 60.0, 2)
                    WHERE id = %s
                """, (last_activity[0],))

            # Start a new activity (end_time = NULL for now)
            # print("Starting a new activity...")
            cur.execute("""
                INSERT INTO activities (
                    user_id, start_time, application, window_title,
                    screenshot_path, extracted_text, ai_analysis,
                    client_identified, category, productivity_score,
                    entry_type
                )
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, 'Agent Upload')
                RETURNING id
            """, (
                current_user.id,
                application,
                window_title,
                file_path,
                extracted_text,
                json.dumps(ai_analysis),
                ai_analysis.get("client_name", "None"),
                ai_analysis.get("category", "Work"),
                ai_analysis.get("productivity_level", 5)
            ))
            activity_id = cur.fetchone()[0]
            # print(f"New activity started with ID: {activity_id}")

        # 📸 Always log screenshot
        print("Logging screenshot...")
        cur.execute("""
            INSERT INTO screenshots (user_id, activity_id, path, taken_at)
            VALUES (%s, %s, %s, NOW())
        """, (current_user.id, activity_id, file_path))

        conn.commit()
        cur.close()
        conn.close()

        # Return response with the screenshot path and activity ID
        return {
            "status": "success",
            "path": f"/screenshots/{os.path.basename(file_path)}",
            "activity_id": activity_id,
            "ai_analysis": ai_analysis
        }

    except Exception as e:
        # Log any exceptions
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")






from fastapi.staticfiles import StaticFiles

if os.path.isdir("screenshots"):
    app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")













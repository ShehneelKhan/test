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
from .screen_tracker import AITimeTracker
import json
# from api_server import AITimeTracker
from jose.exceptions import ExpiredSignatureError




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

# ====== Data endpoints ======
@app.get("/api/activities")
def get_activities(
    date: str = Query(..., description="YYYY-MM-DD"),
    user_id: Optional[int] = Query(None, description="Admin only: view someone else"),
    current_user: UserOut = Depends(get_current_user)
):
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

    return results



#### ADD CLIENTS #####
@app.post("/api/clients")
def add_client(name: str, contact_email: Optional[str] = None, current_user: UserOut = Depends(get_current_user)):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (name, contact_email) VALUES (%s, %s) RETURNING id", (name, contact_email))
    client_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": client_id, "name": name, "contact_email": contact_email}


@app.get("/api/clients")
def list_clients(current_user: UserOut = Depends(get_current_user)):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, contact_email FROM clients ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "name": r[1], "contact_email": r[2]} for r in rows]

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

    # ✅ Combine date + startTime
    start_time = datetime.strptime(
        f"{payload['date']} {payload.get('startTime','09:00')}:00", 
        "%Y-%m-%d %H:%M:%S"
    )
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
        try:
            ai_analysis = json.loads(r[4]) if r[4] else {}
        except Exception:
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











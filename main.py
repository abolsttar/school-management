import os
import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Protocol, runtime_checkable, Any, cast
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Form, BackgroundTasks
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as redis
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

# ============================================================================
# Logging Configuration
# ============================================================================

import pathlib
pathlib.Path("logs").mkdir(exist_ok=True)

error_handler = logging.FileHandler('logs/error.log', encoding='utf-8')
error_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        error_handler,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
error_logger = logging.getLogger('error')
access_logger = logging.getLogger('access')


# ============================================================================
# Configuration
# ============================================================================

class Settings(BaseModel):
    mongo_uri: str = Field(default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    mongo_db: str = Field(default=os.getenv("MONGO_DB", "school_db"))
    redis_url: str = Field(default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    cache_ttl_seconds: int = Field(default=int(os.getenv("CACHE_TTL_SECONDS", "60")))
    admin_api_key: str = Field(default=os.getenv("ADMIN_API_KEY", "change-me"))
    sms_provider: str = Field(default=os.getenv("SMS_PROVIDER", "log"))
    twilio_account_sid: Optional[str] = Field(default=os.getenv("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: Optional[str] = Field(default=os.getenv("TWILIO_AUTH_TOKEN"))
    twilio_from_number: Optional[str] = Field(default=os.getenv("TWILIO_FROM_NUMBER"))
    max_recent_requests: int = Field(default=100)
    rate_limit_per_minute: int = Field(default=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")))
    rate_limit_per_hour: int = Field(default=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")))
    app_name: str = Field(default="School Management System")
    app_version: str = Field(default="2.0.0")


settings = Settings()


# ============================================================================
# App Setup
# ============================================================================

templates = Jinja2Templates(directory="templates")

mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None
redis_client: Optional[Any] = None


# ============================================================================
# Redis Protocol
# ============================================================================

@runtime_checkable
class AsyncRedisLike(Protocol):
    async def ping(self) -> bool: ...
    async def get(self, key: str) -> Optional[str]: ...
    async def setex(self, key: str, seconds: int, value: str) -> Any: ...
    async def delete(self, *keys: str) -> Any: ...
    async def scan(self, cursor: int, match: Optional[str] = None, count: Optional[int] = None) -> Any: ...
    async def incr(self, key: str) -> int: ...
    async def hincrby(self, key: str, field: str, amount: int) -> int: ...
    async def hgetall(self, key: str) -> dict: ...
    async def zadd(self, key: str, mapping: dict) -> int: ...
    async def zrange(self, key: str, start: int, end: int, withscores: bool = False, desc: bool = False) -> List: ...
    async def zremrangebyrank(self, key: str, start: int, end: int) -> int: ...
    async def sadd(self, key: str, *values: str) -> int: ...
    async def scard(self, key: str) -> int: ...
    async def close(self) -> Any: ...


# ============================================================================
# Custom Exceptions
# ============================================================================

class DatabaseNotInitializedError(Exception):
    """Raised when database is not initialized"""
    pass


class CacheNotInitializedError(Exception):
    """Raised when cache is not initialized"""
    pass


class StudentNotFoundError(Exception):
    """Raised when student is not found"""
    pass


# ============================================================================
# Dependencies
# ============================================================================

async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency: Get MongoDB database instance
    
    Returns:
        AsyncIOMotorDatabase: Database instance
        
    Raises:
        HTTPException: If database is not initialized
    """
    if mongo_db is None:
        error_logger.error("Database access attempted but not initialized")
        raise HTTPException(status_code=503, detail="Database is not initialized")
    return mongo_db


async def get_cache() -> Any:
    """
    Dependency: Get Redis cache instance
    
    Returns:
        Redis client instance
        
    Raises:
        HTTPException: If cache is not initialized
    """
    if redis_client is None:
        error_logger.warning("Cache access attempted but not initialized")
        raise HTTPException(status_code=503, detail="Cache is not initialized")
    return redis_client


# ============================================================================
# Models
# ============================================================================

class StudentIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    student_code: str = Field(..., min_length=1, max_length=50)
    grade_level: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    class_name: Optional[str] = Field(None, max_length=50)
    
    @field_validator('student_code')
    @classmethod
    def validate_student_code(cls, v):
        if not v.strip():
            raise ValueError('student_code cannot be empty')
        return v.strip().upper()


class Student(StudentIn):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(alias="_id")


class AttendanceMarkIn(BaseModel):
    student_id: Optional[str] = None
    student_code: Optional[str] = None
    date: str
    status: str = Field(pattern=r"^(present|absent|late)$")
    note: Optional[str] = Field(None, max_length=500)
    recorded_by: Optional[str] = Field(None, max_length=100)
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('date must be in YYYY-MM-DD format')


class AttendanceRecord(AttendanceMarkIn):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(alias="_id")


# ============================================================================
# Middleware
# ============================================================================

async def _track_usage(request: StarletteRequest, response: Response, process_time: float):
    if redis_client is None:
        return
    
    rc = redis_client
    method = request.method
    path = request.url.path
    status_code = response.status_code
    client_ip = request.client.host if request.client else "unknown"
    today = datetime.now().strftime("%Y-%m-%d")
    
    await rc.incr(f"usage:total:{today}")
    
    endpoint_key = f"{method} {path}"
    await rc.hincrby(f"usage:endpoints:{today}", endpoint_key, 1)
    
    await rc.zadd(
        f"usage:response_times:{today}",
        {endpoint_key: int(process_time * 1000)}
    )
    
    await rc.hincrby(f"usage:status_codes:{today}", str(status_code), 1)
    await rc.sadd(f"usage:ips:{today}", client_ip)
    
    request_data = {
        "method": method,
        "path": path,
        "status": status_code,
        "time_ms": round(process_time * 1000, 2),
        "ip": client_ip,
        "timestamp": datetime.now().isoformat()
    }
    
    timestamp = int(time.time() * 1000)
    await rc.zadd(
        "usage:recent_requests",
        {json.dumps(request_data): timestamp}
    )
    await rc.zremrangebyrank("usage:recent_requests", 0, -(settings.max_recent_requests + 1))


# ============================================================================
# Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, mongo_db, redis_client

    # Startup
    logger.info("Starting School Management System...")
    
    try:
        mongo_client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=1500)
        mongo_db = mongo_client[settings.mongo_db]
        await mongo_db.command("ping")
        await mongo_db["attendance"].create_index([("student_id", 1), ("date", 1)], unique=True)
        logger.info(f"✅ MongoDB connected: {settings.mongo_uri}/{settings.mongo_db}")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}")
        mongo_client = None
        mongo_db = None

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        rc = redis_client
        if rc is not None:
            await cast(Any, rc).ping()
            logger.info(f"✅ Redis connected: {settings.redis_url}")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        pass

    logger.info("🚀 Server ready! All systems operational.")
    yield

    # Shutdown
    logger.info("Shutting down...")
    if mongo_client is not None:
        mongo_client.close()
        logger.info("✅ MongoDB connection closed")
    rc = redis_client
    if rc is not None:
        await cast(Any, rc).close()
        logger.info("✅ Redis connection closed")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Complete School Management System with Students, Attendance, and Analytics",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)


@app.middleware("http")
async def security_middleware(request: StarletteRequest, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response


@app.middleware("http")
async def rate_limiting_middleware(request: StarletteRequest, call_next):
    """Rate limiting middleware using Redis."""
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/health", "/readiness", "/docs", "/openapi.json", "/redoc", "/api/docs", "/api/redoc"]:
        return await call_next(request)
    
    if redis_client is not None:
        rc = redis_client
        client_ip = request.client.host if request.client else "unknown"
        now = int(time.time())
        
        # Per-minute rate limit
        minute_key = f"rate_limit:minute:{client_ip}:{now // 60}"
        minute_count = await rc.incr(minute_key)
        await rc.expire(minute_key, 60)
        
        if minute_count > settings.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {minute_count} requests/minute")
            return Response(
                content=json.dumps({"detail": "Rate limit exceeded. Please try again later."}),
                status_code=429,
                headers={"Retry-After": "60", "Content-Type": "application/json"}
            )
        
        # Per-hour rate limit
        hour_key = f"rate_limit:hour:{client_ip}:{now // 3600}"
        hour_count = await rc.incr(hour_key)
        await rc.expire(hour_key, 3600)
        
        if hour_count > settings.rate_limit_per_hour:
            logger.warning(f"Hourly rate limit exceeded for IP {client_ip}: {hour_count} requests/hour")
            return Response(
                content=json.dumps({"detail": "Hourly rate limit exceeded. Please try again later."}),
                status_code=429,
                headers={"Retry-After": "3600", "Content-Type": "application/json"}
            )
    
    return await call_next(request)


@app.middleware("http")
async def usage_tracking_middleware(request: StarletteRequest, call_next):
    """Track API usage statistics."""
    start_time = time.time()
    
    if request.url.path in ["/health", "/readiness", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    try:
        await _track_usage(request, response, process_time)
    except Exception:
        pass
    
    return response


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/readiness")
async def readiness() -> dict:
    db_ready = False
    cache_ready = False
    
    if mongo_db is not None:
        try:
            await mongo_db.command("ping")
            db_ready = True
        except Exception:
            pass
    
    try:
        rc = redis_client
        if rc is not None:
            await cast(Any, rc).ping()
            cache_ready = True
    except Exception:
        pass
    
    return {
        "ready": db_ready and cache_ready,
        "mongo": db_ready,
        "redis": cache_ready
    }


# ============================================================================
# Cache Utilities
# ============================================================================

def student_cache_key(student_code: str) -> str:
    return f"student:{student_code}"


def students_list_cache_key() -> str:
    return "students:list"


def attendance_cache_key(student_code: str, date: str) -> str:
    return f"attendance:{student_code}:{date}"


def attendance_list_cache_key(date: Optional[str] = None, student_id: Optional[str] = None) -> str:
    if date and student_id:
        return f"attendance:list:{date}:{student_id}"
    elif date:
        return f"attendance:list:{date}"
    elif student_id:
        return f"attendance:list:student:{student_id}"
    else:
        return "attendance:list:all"


async def invalidate_student_related_cache(cache: Any, student_code: str) -> None:
    try:
        await cache.delete(student_cache_key(student_code))
        await cache.delete(students_list_cache_key())
    except Exception:
        pass


async def invalidate_attendance_related_cache(cache: Any, student_code: Optional[str] = None, date: Optional[str] = None) -> None:
    try:
        if student_code and date:
            await cache.delete(attendance_cache_key(student_code, date))
        
        await cache.delete(attendance_list_cache_key())
        
        if date:
            await cache.delete(attendance_list_cache_key(date=date))
        if student_code:
            await cache.delete(attendance_list_cache_key(student_id=student_code))
        if date and student_code:
            await cache.delete(attendance_list_cache_key(date=date, student_id=student_code))
        
        if student_code:
            try:
                pattern = f"attendance:{student_code}:*"
                cursor = 0
                while True:
                    result = await cast(Any, cache).scan(cursor, match=pattern, count=100)
                    if isinstance(result, tuple) and len(result) >= 2:
                        cursor, keys = result[0], result[1]
                    else:
                        break
                    if keys:
                        await cast(Any, cache).delete(*keys)
                    if cursor == 0:
                        break
            except Exception:
                pass
    except Exception:
        pass


# ============================================================================
# Students Endpoints
# ============================================================================

@app.post("/students", response_model=Student, status_code=201)
async def create_student(payload: StudentIn, db=Depends(get_db), cache=Depends(get_cache)):
    """
    Create a new student record
    
    Args:
        payload: Student data
        db: MongoDB database dependency
        cache: Redis cache dependency
    
    Returns:
        Created student object
    
    Raises:
        HTTPException: 409 if student_code already exists
    """
    logger.info(f"Creating student: {payload.student_code} - {payload.first_name} {payload.last_name}")
    
    try:
        doc = payload.model_dump()
        doc["_id"] = payload.student_code
        
        exists = await db["students"].find_one({"_id": doc["_id"]})
        if exists:
            logger.warning(f"Student creation failed: {payload.student_code} already exists")
            raise HTTPException(status_code=409, detail="student_code already exists")
        
        result = await db["students"].insert_one(doc)
        created = {**doc, "_id": result.inserted_id}
        
        await invalidate_student_related_cache(cache, payload.student_code)
        logger.info(f"✅ Student created successfully: {payload.student_code}")
        
        return Student(**{**created, "_id": str(created["_id"])})
    except HTTPException:
        raise
    except Exception as e:
        error_logger.error(f"Failed to create student {payload.student_code}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/students", response_model=List[Student])
async def list_students(db=Depends(get_db), cache=Depends(get_cache)):
    """
    Get all students list with caching
    
    Args:
        db: MongoDB database dependency
        cache: Redis cache dependency
    
    Returns:
        List of all students
    """
    logger.debug("Fetching students list")
    cache_key = students_list_cache_key()
    
    try:
        cached = await cache.get(cache_key)
        if cached:
            data = json.loads(cached)
            logger.debug(f"Cache hit for students list ({len(data)} students)")
            return [Student(**item) for item in data]
    except Exception as e:
        logger.debug(f"Cache miss or error: {e}")
    
    docs = []
    async for doc in db["students"].find({}).sort("last_name"):
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    
    logger.info(f"Fetched {len(docs)} students from database")
    
    try:
        await cache.setex(cache_key, settings.cache_ttl_seconds * 2, json.dumps(docs))
    except Exception as e:
        logger.warning(f"Failed to cache students list: {e}")
    
    return [Student(**doc) for doc in docs]


@app.get("/students/{student_code}", response_model=Student)
async def get_student(student_code: str, db=Depends(get_db), cache=Depends(get_cache)):
    try:
        cached = await cache.get(student_cache_key(student_code))
        if cached:
            data = json.loads(cached)
            return Student(**data)
    except Exception:
        pass

    doc = await db["students"].find_one({"_id": student_code})
    if not doc:
        raise HTTPException(status_code=404, detail="student not found")

    try:
        await cache.setex(student_cache_key(student_code), settings.cache_ttl_seconds, json.dumps(doc))
    except Exception:
        pass

    return Student(**doc)


@app.put("/students/{student_code}", response_model=Student)
async def update_student(student_code: str, payload: StudentIn, db=Depends(get_db), cache=Depends(get_cache)):
    await db["students"].update_one({"_id": student_code}, {"$set": payload.model_dump()})
    doc = await db["students"].find_one({"_id": student_code})
    
    if not doc:
        raise HTTPException(status_code=404, detail="student not found")
    
    await invalidate_student_related_cache(cache, student_code)
    
    return Student(**doc)


@app.delete("/students/{student_code}", status_code=204)
async def delete_student(student_code: str, db=Depends(get_db), cache=Depends(get_cache)):
    result = await db["students"].delete_one({"_id": student_code})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="student not found")
    
    await invalidate_student_related_cache(cache, student_code)
    
    return None


# ============================================================================
# Attendance Endpoints
# ============================================================================

async def send_sms_if_needed(mark: AttendanceMarkIn, db: AsyncIOMotorDatabase, cache: Optional[Any] = None) -> None:
    if mark.status != "absent":
        return
    
    student_code = mark.student_code or mark.student_id
    if not student_code:
        return
    
    student = None
    if cache:
        try:
            cached = await cache.get(student_cache_key(student_code))
            if cached:
                student = json.loads(cached)
        except Exception:
            pass
    
    if not student:
        student_doc = await db["students"].find_one({"_id": student_code})
        if not student_doc:
            return
        student = student_doc
        if cache:
            try:
                await cache.setex(student_cache_key(student_code), settings.cache_ttl_seconds, json.dumps(student))
            except Exception:
                pass
    
    phone = student.get("phone")
    if not phone:
        return
    
    first_name = student.get("first_name", "")
    last_name = student.get("last_name", "")
    message = f"Student {first_name} {last_name} was absent on {mark.date}."

    if settings.sms_provider == "twilio" and settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number:
        try:
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    body=message,
                    from_=settings.twilio_from_number,
                    to=phone
                )
            )
        except Exception as e:
            error_logger.error(f"SMS send failed via Twilio", exc_info=True, extra={"phone": phone, "error": str(e)})
    else:
        logger.info(f"SMS notification (log mode): {message}", extra={"phone": phone})


@app.post("/attendance/mark", response_model=AttendanceRecord, status_code=201)
async def mark_attendance(
    payload: AttendanceMarkIn,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    cache=Depends(get_cache)
):
    """
    Mark student attendance for a specific date
    
    Args:
        payload: Attendance data (student_code, date, status)
        background_tasks: FastAPI background tasks for async SMS
        db: MongoDB database dependency
        cache: Redis cache dependency
    
    Returns:
        Created/updated attendance record
    
    Raises:
        HTTPException: 400 if student_code is missing
    """
    student_code = payload.student_code or payload.student_id
    if not student_code:
        logger.warning("Attendance mark failed: student_code missing")
        raise HTTPException(status_code=400, detail="student_code is required")
    
    logger.info(f"Marking attendance: {student_code} - {payload.date} - {payload.status}")
    
    try:
        doc = payload.model_dump()
        doc["student_id"] = student_code
        doc["student_code"] = student_code
        
        await db["attendance"].update_one(
            {"student_id": student_code, "date": payload.date},
            {"$set": doc},
            upsert=True
        )
        
        stored = await db["attendance"].find_one({"student_id": student_code, "date": payload.date})
        if not stored:
            raise HTTPException(status_code=500, detail="Failed to save attendance")
            
        stored["_id"] = str(stored["_id"])
        
        await invalidate_attendance_related_cache(cache, student_code, payload.date)
        
        background_tasks.add_task(send_sms_if_needed, payload, db, cache)
        logger.info(f"✅ Attendance marked successfully: {student_code} - {payload.date} - {payload.status}")
        
        return AttendanceRecord(**stored)
    except HTTPException:
        raise
    except Exception as e:
        error_logger.error(f"Failed to mark attendance for {student_code}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/attendance", response_model=List[AttendanceRecord])
async def list_attendance(
    date: Optional[str] = None,
    student_id: Optional[str] = None,
    db=Depends(get_db),
    cache=Depends(get_cache)
):
    cache_key = attendance_list_cache_key(date=date, student_id=student_id)
    
    try:
        cached = await cache.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [AttendanceRecord(**item) for item in data]
    except Exception:
        pass
    
    query: dict = {}
    if date:
        query["date"] = date
    if student_id:
        query["student_id"] = student_id
    
    out: List[dict] = []
    async for doc in db["attendance"].find(query).sort([("date", 1)]):
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    
    try:
        await cache.setex(cache_key, settings.cache_ttl_seconds, json.dumps(out))
    except Exception:
        pass
    
    return [AttendanceRecord(**doc) for doc in out]


# ============================================================================
# Admin UI
# ============================================================================

def require_admin(request: Request) -> None:
    api_key = request.cookies.get("admin_api_key") or request.headers.get("X-Admin-Key")
    if api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/admin/login")
async def admin_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/admin/login")
async def admin_login(request: Request, api_key: str = Form(...)):
    if api_key != settings.admin_api_key:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid API key"},
            status_code=401
        )
    
    resp = RedirectResponse(url="/admin", status_code=302)
    resp.set_cookie("admin_api_key", api_key, httponly=True, samesite="lax", max_age=86400)
    return resp


@app.post("/admin/logout")
async def admin_logout():
    """Logout admin user and clear session"""
    resp = RedirectResponse(url="/admin/login", status_code=302)
    resp.delete_cookie("admin_api_key")
    return resp


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db=Depends(get_db), cache=Depends(get_cache)):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    total_students = db["students"].count_documents({})
    today_attendance = db["attendance"].count_documents({"date": today})
    present_count = db["attendance"].count_documents({"date": today, "status": "present"})
    absent_count = db["attendance"].count_documents({"date": today, "status": "absent"})
    late_count = db["attendance"].count_documents({"date": today, "status": "late"})
    
    total_students_val = await total_students
    today_attendance_val = await today_attendance
    present_count_val = await present_count
    absent_count_val = await absent_count
    late_count_val = await late_count
    
    stats = {
        "total_students": total_students_val,
        "today_attendance": today_attendance_val,
        "present_count": present_count_val,
        "absent_count": absent_count_val,
        "late_count": late_count_val,
        "attendance_rate": round((present_count_val / total_students_val * 100) if total_students_val > 0 else 0, 2)
    }
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats, "today": today})


async def get_students_list(db, cache) -> List[Student]:
    """Shared function to get students list with caching"""
    cache_key = students_list_cache_key()
    
    try:
        cached = await cache.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [Student(**item) for item in data]
    except Exception:
        pass
    
    docs = []
    async for doc in db["students"].find({}).sort("last_name"):
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    
    try:
        await cache.setex(cache_key, settings.cache_ttl_seconds * 2, json.dumps(docs))
    except Exception:
        pass
    
    return [Student(**doc) for doc in docs]


@app.get("/admin/attendance")
async def admin_attendance_page(request: Request, db=Depends(get_db), cache=Depends(get_cache)):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    students = await get_students_list(db, cache)
    today = datetime.now().strftime("%Y-%m-%d")
    
    return templates.TemplateResponse("attendance.html", {"request": request, "students": students, "today": today})


@app.get("/admin/students")
async def admin_students_page(request: Request, db=Depends(get_db), cache=Depends(get_cache)):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    students = await get_students_list(db, cache)
    
    return templates.TemplateResponse("students.html", {"request": request, "students": students})


@app.get("/admin/stats")
async def admin_stats_page(request: Request, db=Depends(get_db), cache=Depends(get_cache)):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    stats_data = {
        "today": today,
        "total_students": await db["students"].count_documents({}),
        "recent_attendance": []
    }
    
    recent_docs = []
    async for doc in db["attendance"].find({}).sort("date", -1).limit(50):
        doc["_id"] = str(doc["_id"])
        recent_docs.append(doc)
    
    stats_data["recent_attendance"] = recent_docs
    
    return templates.TemplateResponse("reports.html", {"request": request, "stats": stats_data})


@app.post("/admin/attendance/mark")
async def admin_mark_attendance(request: Request, background_tasks: BackgroundTasks, db=Depends(get_db), cache=Depends(get_cache)):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    form = await request.form()
    date = str(form.get("date") or "")
    
    students_list = await get_students_list(db, cache)
    student_code_map = {str(s.id): s.student_code for s in students_list if hasattr(s, 'id')}
    student_code_map.update({s.student_code: s.student_code for s in students_list})
    
    for key, value in form.items():
        if not key.startswith("status_"):
            continue
        
        student_key = key[len("status_"):]
        # Try to find student_code from map, otherwise use the key itself
        student_code = student_code_map.get(student_key, student_key)
        status = str(value)
        
        payload = AttendanceMarkIn(
            student_id=student_code,
            student_code=student_code,
            date=date,
            status=status,
            note=None,
            recorded_by=None
        )
        await mark_attendance(
            payload,
            background_tasks,
            db=db,
            cache=cache
        )
    
    return RedirectResponse(url="/admin/attendance?success=true", status_code=302)


# ============================================================================
# Statistics Endpoints
# ============================================================================

@app.get("/stats/today")
async def get_today_stats(cache=Depends(get_cache)):
    """Get today's usage statistics"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Cache is not initialized")
    
    rc = cast(Any, redis_client)
    today = datetime.now().strftime("%Y-%m-%d")
    
    total = await rc.get(f"usage:total:{today}")
    total = int(total) if total else 0
    
    unique_ips = await rc.scard(f"usage:ips:{today}")
    status_codes = await rc.hgetall(f"usage:status_codes:{today}")
    endpoints = await rc.hgetall(f"usage:endpoints:{today}")
    
    top_endpoints = sorted(endpoints.items(), key=lambda x: int(x[1]), reverse=True)[:10]
    
    return {
        "date": today,
        "total_requests": total,
        "unique_visitors": unique_ips,
        "status_codes": {k: int(v) for k, v in status_codes.items()},
        "top_endpoints": [{"endpoint": ep, "count": int(count)} for ep, count in top_endpoints]
    }


@app.get("/stats/slowest")
async def get_slowest_endpoints(cache=Depends(get_cache), limit: int = 10):
    """Get slowest endpoints by response time"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Cache is not initialized")
    
    rc = cast(Any, redis_client)
    today = datetime.now().strftime("%Y-%m-%d")
    
    slowest = await rc.zrange(
        f"usage:response_times:{today}",
        0,
        limit - 1,
        withscores=True,
        desc=True
    )
    
    result = []
    if isinstance(slowest, list):
        for item in slowest:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                result.append({
                    "endpoint": item[0],
                    "avg_response_time_ms": int(item[1])
                })
    
    return {
        "date": today,
        "slowest_endpoints": result
    }


@app.get("/stats/recent")
async def get_recent_requests(cache=Depends(get_cache), limit: int = 20):
    """Get recent API requests"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Cache is not initialized")
    
    rc = cast(Any, redis_client)
    
    recent = await rc.zrange(
        "usage:recent_requests",
        -limit,
        -1,
        withscores=False
    )
    
    result = []
    if isinstance(recent, list):
        for item in recent:
            try:
                data = json.loads(item)
                result.append(data)
            except Exception:
                pass
    
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "recent_requests": result[:limit]
    }


@app.get("/stats/endpoints/{date}")
async def get_endpoints_stats(date: str, cache=Depends(get_cache)):
    """Get endpoint statistics for a specific date"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Cache is not initialized")
    
    rc = cast(Any, redis_client)
    
    endpoints = await rc.hgetall(f"usage:endpoints:{date}")
    status_codes = await rc.hgetall(f"usage:status_codes:{date}")
    
    return {
        "date": date,
        "endpoints": {k: int(v) for k, v in endpoints.items()},
        "status_codes": {k: int(v) for k, v in status_codes.items()}
    }


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import sys
    
    print("\n" + "="*70)
    print("🚀 School Management System - Starting Server")
    print("="*70)
    print(f"📋 App Name: {settings.app_name}")
    print(f"📦 Version: {settings.app_version}")
    print(f"🌐 Server: http://127.0.0.1:8000")
    print(f"📚 API Docs: http://127.0.0.1:8000/api/docs")
    print(f"👤 Admin Panel: http://127.0.0.1:8000/admin/login")
    print(f"💾 MongoDB: {settings.mongo_uri}")
    print(f"⚡ Redis: {settings.redis_url}")
    print("="*70)
    print("✅ Press CTRL+C to stop the server\n")
    sys.stdout.flush()
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

## School Management API (FastAPI + MongoDB + Redis)

Run locally:

1) Create and activate a virtualenv (optional but recommended)
2) Install deps:
```
pip install -r requirements.txt
```
3) Set env vars (defaults are fine if services run locally):
```
set MONGO_URI=mongodb://localhost:27017
set MONGO_DB=school_db
set REDIS_URL=redis://localhost:6379/0
set CACHE_TTL_SECONDS=60
```
4) Start API:
```
uvicorn main:app --reload
```

Endpoints:
- GET /health
- GET /readiness
- POST /students  (body includes student_code; stored as _id)
- GET /students
- GET /students/{student_code}
- PUT /students/{student_code}
- DELETE /students/{student_code}
- POST /attendance/mark  (student_code + date + status)
- GET /attendance?date=YYYY-MM-DD&student_id={student_code}



# راه‌اندازی MongoDB و Redis با Docker

## مراحل نصب و راه‌اندازی

### 1. نصب Docker Desktop
- اگر Docker Desktop نصب نشده، از لینک زیر دانلود و نصب کنید:
  https://www.docker.com/products/docker-desktop

### 2. راه‌اندازی Docker Desktop
- Docker Desktop را از منوی Start اجرا کنید
- منتظر بمانید تا Docker Desktop به طور کامل راه‌اندازی شود (آیکون Docker در System Tray باید سبز شود)

### 3. راه‌اندازی MongoDB و Redis

**روش 1: استفاده از اسکریپت PowerShell (پیشنهادی)**
```powershell
.\start-services.ps1
```

**روش 2: استفاده مستقیم از Docker Compose**
```powershell
docker-compose up -d
```

### 4. بررسی وضعیت سرویس‌ها
```powershell
docker-compose ps
```

### 5. مشاهده لاگ‌ها
```powershell
docker-compose logs -f
```

### 6. توقف سرویس‌ها
```powershell
docker-compose down
```

## تنظیمات Environment Variables

بعد از راه‌اندازی سرویس‌ها، می‌توانید متغیرهای محیطی زیر را تنظیم کنید:

```powershell
$env:MONGO_URI="mongodb://localhost:27017"
$env:MONGO_DB="school_db"
$env:REDIS_URL="redis://localhost:6379/0"
```

یا یک فایل `.env` در ریشه پروژه ایجاد کنید:
```
MONGO_URI=mongodb://localhost:27017
MONGO_DB=school_db
REDIS_URL=redis://localhost:6379/0
```

## اجرای برنامه
بعد از راه‌اندازی MongoDB و Redis:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## عیب‌یابی

### مشکل: Docker command not found
- Docker Desktop را راه‌اندازی کنید
- PowerShell یا Terminal را بسته و دوباره باز کنید
- اگر مشکل ادامه داشت، سیستم را Restart کنید

### مشکل: Cannot connect to Docker daemon
- Docker Desktop را راه‌اندازی کنید
- مطمئن شوید که Docker Desktop به طور کامل شروع شده (آیکون باید سبز باشد)

### مشکل: Port already in use
- اگر پورت 27017 یا 6379 قبلاً استفاده شده، باید سرویس قبلی را متوقف کنید
- یا پورت‌های دیگری در `docker-compose.yml` تنظیم کنید


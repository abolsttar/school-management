# اسکریپت ساده برای راه‌اندازی MongoDB و Redis
Write-Host "بررسی Docker..." -ForegroundColor Cyan

$dockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (-not (Test-Path $dockerExe)) {
    Write-Host "❌ Docker پیدا نشد!" -ForegroundColor Red
    exit 1
}

# بررسی آماده بودن Docker
Write-Host "بررسی وضعیت Docker..." -ForegroundColor Yellow
$check = & $dockerExe info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker Desktop آماده نیست!" -ForegroundColor Red
    Write-Host "لطفاً Docker Desktop را باز کنید و منتظر بمانید تا آماده شود." -ForegroundColor Yellow
    Write-Host "سپس دوباره این اسکریپت را اجرا کنید." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Docker آماده است!" -ForegroundColor Green

# راه‌اندازی سرویس‌ها
Write-Host "`nراه‌اندازی MongoDB و Redis..." -ForegroundColor Cyan
& $dockerExe compose -f docker-compose.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ سرویس‌ها با موفقیت راه‌اندازی شدند!" -ForegroundColor Green
    Write-Host "MongoDB: mongodb://localhost:27017" -ForegroundColor Yellow
    Write-Host "Redis: redis://localhost:6379" -ForegroundColor Yellow
    Write-Host "`nبرای مشاهده وضعیت: docker compose ps" -ForegroundColor Cyan
    Write-Host "برای توقف: docker compose down" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ خطا در راه‌اندازی سرویس‌ها" -ForegroundColor Red
    exit 1
}


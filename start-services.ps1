# Script to start MongoDB and Redis using Docker Compose

Write-Host "Checking Docker installation..." -ForegroundColor Cyan

# Try to find Docker in common locations
$dockerPaths = @(
    "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
    "$env:ProgramFiles\Docker\Docker\resources\bin\docker-compose.exe",
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    "C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"
)

$dockerExe = $null
$dockerComposeExe = $null

foreach ($path in $dockerPaths) {
    if (Test-Path $path) {
        $dockerExe = $path
        $dockerComposeExe = $path.Replace("docker.exe", "docker-compose.exe")
        if (Test-Path $dockerComposeExe) {
            break
        }
    }
}

# If not found, try using docker command directly (if in PATH)
if (-not $dockerExe) {
    try {
        $dockerCheck = Get-Command docker -ErrorAction Stop
        $dockerExe = $dockerCheck.Source
        $dockerComposeExe = "docker-compose"
    } catch {
        Write-Host "Docker not found. Please:" -ForegroundColor Yellow
        Write-Host "1. Install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        Write-Host "2. Start Docker Desktop and wait for it to be ready" -ForegroundColor Yellow
        Write-Host "3. Restart this terminal or PowerShell" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Found Docker at: $dockerExe" -ForegroundColor Green

# Check if Docker daemon is running
Write-Host "Checking Docker daemon..." -ForegroundColor Cyan
$dockerRunning = & $dockerExe info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker daemon is not running. Please start Docker Desktop first." -ForegroundColor Red
    Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    Write-Host "Waiting for Docker Desktop to start (this may take 30-60 seconds)..." -ForegroundColor Yellow
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 2
        $elapsed += 2
        $test = & $dockerExe info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Docker is ready!" -ForegroundColor Green
            break
        }
    }
    if ($elapsed -ge $timeout) {
        Write-Host "Timeout waiting for Docker. Please start Docker Desktop manually." -ForegroundColor Red
        exit 1
    }
}

# Start services
Write-Host "Starting MongoDB and Redis with Docker Compose..." -ForegroundColor Cyan
if ($dockerComposeExe -like "*docker-compose.exe") {
    & $dockerComposeExe -f docker-compose.yml up -d
} else {
    & $dockerExe compose -f docker-compose.yml up -d
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host "MongoDB: mongodb://localhost:27017" -ForegroundColor Cyan
    Write-Host "Redis: redis://localhost:6379" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To stop services, run:" -ForegroundColor Yellow
    Write-Host "  docker-compose down" -ForegroundColor White
} else {
    Write-Host "Failed to start services." -ForegroundColor Red
    exit 1
}


@echo off
REM Quick start script for Retail AI MVP (Windows)

echo.
echo ========================================
echo   Retail AI MVP - Quick Start (Windows)
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose is not installed.
    pause
    exit /b 1
)

echo [OK] Docker and Docker Compose are installed
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [INFO] Creating .env file from template...
    copy .env.mvp .env
    echo [OK] .env file created. Please review and update if needed.
    echo.
)

REM Create necessary directories
echo [INFO] Creating directories...
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
echo [OK] Directories created
echo.

REM Start Docker Compose services
echo [INFO] Starting Docker services...
docker-compose -f docker-compose-mvp.yml up -d

echo.
echo [INFO] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Run database migrations
echo.
echo [INFO] Running database migrations...
docker-compose -f docker-compose-mvp.yml exec -T app alembic upgrade head

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Services are running at:
echo   - API:      http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo   - pgAdmin:  http://localhost:5050 (admin@retailai.com / admin)
echo.
echo View logs:
echo   docker-compose -f docker-compose-mvp.yml logs -f app
echo.
echo Stop services:
echo   docker-compose -f docker-compose-mvp.yml down
echo.
echo Happy coding!
echo.
pause

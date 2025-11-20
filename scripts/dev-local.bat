@echo off
REM Local development script (without Docker) for Windows

echo.
echo ========================================
echo   Retail AI MVP - Local Development
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.11+ first.
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
    echo.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [INFO] Installing dependencies...
pip install -r requirements-mvp.txt

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo.
    echo [INFO] Creating .env file from template...
    copy .env.mvp .env
    echo [OK] .env file created
    echo.
    echo [WARNING] Please configure your database connection in .env file
    echo.
)

REM Create directories
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs

echo.
echo ========================================
echo   Ready to start development!
echo ========================================
echo.
echo Before starting the server:
echo   1. Make sure PostgreSQL is running
echo   2. Make sure Redis is running (optional)
echo   3. Update DATABASE_URL in .env file
echo.
echo To start the server:
echo   uvicorn app.main_mvp:app --reload --host 0.0.0.0 --port 8000
echo.
echo To run database migrations:
echo   alembic upgrade head
echo.
pause

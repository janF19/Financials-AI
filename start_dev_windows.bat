@echo off
echo Starting Development Environment...

REM Ensure Docker Desktop is running before executing this script.

REM Get the directory of the script
SET SCRIPT_DIR=%~dp0
echo Project Root: %SCRIPT_DIR%

REM 1. Start Redis using Docker Compose (in detached mode)
echo Starting Redis container...
cd /d "%SCRIPT_DIR%"
docker-compose up -d redis
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to start Redis. Please check Docker and docker-compose.yml.
    pause
    exit /b %ERRORLEVEL%
) ELSE (
    echo Redis container started or already running.
)
timeout /t 3 >nul

REM 2. Start Celery Worker (in a new command prompt window)
echo Starting Celery worker...
start "Celery Worker" cmd /k "cd /d "%SCRIPT_DIR%" && echo Starting Celery using Poetry... && poetry run celery -A backend.celery_app worker -l info -P solo"
timeout /t 3 >nul

REM 3. Start FastAPI Backend (in a new command prompt window)
echo Starting FastAPI backend...
start "FastAPI Backend" cmd /k "cd /d "%SCRIPT_DIR%" && echo Using Poetry to run Uvicorn... && poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
REM If you don't use a virtual environment named 'venv', remove "CALL venv\Scripts\activate &&"
REM or adjust to your virtual environment activation command.
timeout /t 3 >nul

REM 4. Start Frontend (in a new command prompt window)
echo Starting Frontend development server...
start "Frontend Dev Server" cmd /k "cd /d "%SCRIPT_DIR%\frontend" && npm run dev"

echo All services are starting in separate windows.
echo.
echo To stop services:
echo - Close each command prompt window.
echo - To stop Redis: docker-compose down
echo.
pause 
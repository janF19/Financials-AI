@echo off
echo Starting Docker services (backend, worker, redis)...
echo Make sure Docker Desktop is running.

REM Create data/temp directory if it doesn't exist, for the volume mount
if not exist ".\\data\\temp" (
    echo Creating .\\data\\temp directory for temporary file storage...
    mkdir ".\\data\\temp"
)

docker-compose up --build

echo.
echo To see logs, run:
echo   docker-compose logs -f backend
echo   docker-compose logs -f worker
echo.
echo To stop services, run:
echo   docker-compose down
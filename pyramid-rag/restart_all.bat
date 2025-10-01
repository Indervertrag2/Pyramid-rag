@echo off
echo Restarting Pyramid RAG System...
echo.

echo Stopping all containers...
docker-compose down

echo.
echo Waiting 5 seconds...
timeout /t 5 /nobreak > nul

echo.
echo Starting containers...
docker-compose up -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak > nul

echo.
echo Checking health...
curl -s http://localhost:18000/health

echo.
echo.
echo System restart complete!
echo Frontend: http://localhost:3002
echo Backend: http://localhost:18000
echo.
pause
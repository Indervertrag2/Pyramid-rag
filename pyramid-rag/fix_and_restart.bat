@echo off
echo ================================================
echo Fixing and Restarting Pyramid RAG System
echo ================================================
echo.

echo Step 1: Stopping all containers...
docker-compose down
timeout /t 3 /nobreak > nul

echo.
echo Step 2: Cleaning up Docker volumes (keeping data)...
docker system prune -f
timeout /t 2 /nobreak > nul

echo.
echo Step 3: Starting containers fresh...
docker-compose up -d
timeout /t 10 /nobreak > nul

echo.
echo Step 4: Checking container status...
docker ps --format "table {{.Names}}\t{{.Status}}"

echo.
echo Step 5: Testing backend health...
curl -s http://localhost:18000/health || echo Backend not ready yet

echo.
echo ================================================
echo System restart complete!
echo ================================================
echo.
echo Frontend: http://localhost:3002
echo Backend API: http://localhost:18000
echo.
echo Login credentials:
echo Email: admin@pyramid-computer.de
echo Password: admin123
echo.
echo The upload system has been fixed to use the simplified endpoint.
echo Files will be uploaded without hanging on document processing.
echo.
pause
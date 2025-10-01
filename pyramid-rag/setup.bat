@echo off
REM Pyramid RAG Platform - Windows Setup Script
REM ============================================

echo ============================================
echo Pyramid RAG Platform - Installationsskript
echo ============================================
echo.

REM Check for Docker
echo Ueberpruefe Systemanforderungen...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker ist nicht installiert. Bitte installieren Sie Docker Desktop.
    echo     Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker ist installiert

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker Compose ist nicht installiert.
    pause
    exit /b 1
)
echo [OK] Docker Compose ist installiert

REM Check for NVIDIA GPU
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] NVIDIA GPU erkannt
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
) else (
    echo [!] Keine NVIDIA GPU erkannt - System laeuft auf CPU ^(langsamer^)
)

echo.
echo Konfiguriere Umgebungsvariablen...

REM Create .env file if not exists
if not exist backend\.env (
    copy backend\.env.example backend\.env
    echo [OK] Backend .env Datei erstellt
) else (
    echo [!] Backend .env existiert bereits
)

REM Create directories
echo.
echo Erstelle Verzeichnisse...
if not exist data mkdir data
if not exist data\documents mkdir data\documents
if not exist data\postgres mkdir data\postgres
if not exist data\redis mkdir data\redis
if not exist data\ollama mkdir data\ollama
if not exist data\grafana mkdir data\grafana
if not exist data\prometheus mkdir data\prometheus
if not exist docker mkdir docker
if not exist docker\postgres mkdir docker\postgres
if not exist docker\prometheus mkdir docker\prometheus
if not exist docker\grafana mkdir docker\grafana
if not exist docker\grafana\provisioning mkdir docker\grafana\provisioning
if not exist docker\grafana\provisioning\datasources mkdir docker\grafana\provisioning\datasources
if not exist docker\grafana\provisioning\dashboards mkdir docker\grafana\provisioning\dashboards
if not exist backend\migrations mkdir backend\migrations
if not exist backend\migrations\versions mkdir backend\migrations\versions
echo [OK] Verzeichnisse erstellt

REM Create Prometheus configuration
echo.
echo Erstelle Prometheus-Konfiguration...
(
echo global:
echo   scrape_interval: 15s
echo   evaluation_interval: 15s
echo.
echo scrape_configs:
echo   - job_name: 'pyramid-backend'
echo     static_configs:
echo       - targets: ['backend:8000']
echo     metrics_path: '/metrics'
echo.
echo   - job_name: 'postgres'
echo     static_configs:
echo       - targets: ['postgres:5432']
echo.
echo   - job_name: 'redis'
echo     static_configs:
echo       - targets: ['redis:6379']
echo.
echo   - job_name: 'ollama'
echo     static_configs:
echo       - targets: ['ollama:11434']
) > docker\prometheus\prometheus.yml
echo [OK] Prometheus konfiguriert

REM Create Grafana datasource
echo.
echo Erstelle Grafana-Konfiguration...
(
echo apiVersion: 1
echo.
echo datasources:
echo   - name: Prometheus
echo     type: prometheus
echo     access: proxy
echo     url: http://prometheus:9090
echo     isDefault: true
echo     editable: true
) > docker\grafana\provisioning\datasources\prometheus.yml
echo [OK] Grafana konfiguriert

REM Set document storage path
set DOCUMENT_STORAGE_PATH=%cd%\data\documents
echo [OK] Dokumentenspeicher: %DOCUMENT_STORAGE_PATH%

echo.
echo Lade Docker-Images herunter...
docker-compose pull

echo.
echo Starte Dienste...
docker-compose up -d postgres redis

echo.
echo Warte auf Datenbankinitialisierung...
timeout /t 10 /nobreak >nul

echo.
echo Starte Ollama und lade Qwen 2.5 Modell...
docker-compose up -d ollama
timeout /t 5 /nobreak >nul

REM Pull Qwen model
echo Lade Qwen 2.5 14B Modell (dies kann einige Minuten dauern)...
docker exec pyramid-ollama ollama pull qwen2.5:14b

echo.
echo Starte alle Dienste...
docker-compose up -d

echo.
echo Warte auf Systemstart...
timeout /t 20 /nobreak >nul

REM Check services
echo.
echo Ueberpruefe Dienststatus...
echo.

curl -s -o nul -w "%%{http_code}" http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend API ist erreichbar
) else (
    echo [X] Backend API ist nicht erreichbar
)

curl -s -o nul -w "%%{http_code}" http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Frontend ist erreichbar
) else (
    echo [X] Frontend ist nicht erreichbar
)

echo.
echo ============================================
echo Installation abgeschlossen!
echo ============================================
echo.
echo Zugriff auf die Anwendung:
echo   Hauptanwendung: http://localhost
echo   Grafana: http://localhost:3001 (admin/admin)
echo   Prometheus: http://localhost:9090
echo   Flower: http://localhost:5555
echo.
echo Admin-Zugangsdaten:
echo   E-Mail: admin@pyramid-computer.de
echo   Passwort: PyramidAdmin2024!
echo.
echo Erste Schritte:
echo   1. Oeffnen Sie http://localhost im Browser
echo   2. Melden Sie sich mit den Admin-Zugangsdaten an
echo   3. Erstellen Sie Benutzerkonten fuer Ihre Mitarbeiter
echo   4. Beginnen Sie mit dem Upload von Dokumenten
echo.
echo Befehle:
echo   Logs anzeigen: docker-compose logs -f [service]
echo   Dienste stoppen: docker-compose down
echo   Dienste neustarten: docker-compose restart
echo   System aktualisieren: git pull ^&^& docker-compose up -d --build
echo.
pause
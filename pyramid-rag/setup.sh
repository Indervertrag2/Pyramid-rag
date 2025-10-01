#!/bin/bash

# Pyramid RAG Platform - Setup Script
# ====================================

set -e

echo "============================================"
echo "Pyramid RAG Platform - Installationsskript"
echo "============================================"
echo ""

# Check for required tools
echo "Überprüfe Systemanforderungen..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker ist nicht installiert. Bitte installieren Sie Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose."
    exit 1
fi

# Check for NVIDIA GPU (optional but recommended)
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU erkannt"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

    # Check for NVIDIA Container Toolkit
    if ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo "⚠️  NVIDIA Container Toolkit nicht installiert oder konfiguriert"
        echo "   Für GPU-Unterstützung installieren Sie: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    else
        echo "✅ NVIDIA Container Toolkit installiert"
    fi
else
    echo "⚠️  Keine NVIDIA GPU erkannt - System läuft auf CPU (langsamer)"
fi

echo ""
echo "Konfiguriere Umgebungsvariablen..."

# Create .env file from example if not exists
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Backend .env Datei erstellt"

    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your-super-secret-key-change-this-in-production-minimum-32-chars/$SECRET_KEY/g" backend/.env
    echo "✅ Sicherer Secret Key generiert"
else
    echo "⚠️  Backend .env existiert bereits"
fi

# Create necessary directories
echo ""
echo "Erstelle Verzeichnisse..."
mkdir -p data/{documents,postgres,redis,ollama,grafana,prometheus}
mkdir -p docker/{postgres,prometheus,grafana/provisioning/datasources,grafana/provisioning/dashboards}
mkdir -p backend/migrations/versions
chmod -R 755 data
echo "✅ Verzeichnisse erstellt"

# Create Prometheus configuration
echo ""
echo "Erstelle Prometheus-Konfiguration..."
cat > docker/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'pyramid-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'ollama'
    static_configs:
      - targets: ['ollama:11434']
EOF
echo "✅ Prometheus konfiguriert"

# Create Grafana datasource configuration
echo ""
echo "Erstelle Grafana-Konfiguration..."
cat > docker/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
echo "✅ Grafana konfiguriert"

# Set document storage path
export DOCUMENT_STORAGE_PATH="$(pwd)/data/documents"
echo "✅ Dokumentenspeicher: $DOCUMENT_STORAGE_PATH"

echo ""
echo "Lade Docker-Images herunter..."
docker-compose pull

echo ""
echo "Starte Dienste..."
docker-compose up -d postgres redis

echo ""
echo "Warte auf Datenbankinitialisierung..."
sleep 10

echo ""
echo "Starte Ollama und lade Qwen 2.5 Modell..."
docker-compose up -d ollama
sleep 5

# Pull Qwen model
echo "Lade Qwen 2.5 14B Modell (dies kann einige Minuten dauern)..."
docker exec pyramid-ollama ollama pull qwen2.5:14b

echo ""
echo "Starte alle Dienste..."
docker-compose up -d

echo ""
echo "Warte auf Systemstart..."
sleep 20

# Check service health
echo ""
echo "Überprüfe Dienststatus..."
echo ""

# Function to check service
check_service() {
    local service=$1
    local url=$2
    if curl -s -o /dev/null -w "%{http_code}" $url | grep -q "200\|301\|302"; then
        echo "✅ $service ist erreichbar"
    else
        echo "❌ $service ist nicht erreichbar"
    fi
}

check_service "Backend API" "http://localhost:8000/health"
check_service "Frontend" "http://localhost:3000"
check_service "Flower (Celery Monitor)" "http://localhost:5555"
check_service "Prometheus" "http://localhost:9090"
check_service "Grafana" "http://localhost:3001"
check_service "Ollama" "http://localhost:11434/api/version"

echo ""
echo "============================================"
echo "Installation abgeschlossen!"
echo "============================================"
echo ""
echo "Zugriff auf die Anwendung:"
echo "  🌐 Hauptanwendung: http://localhost"
echo "  📊 Grafana: http://localhost:3001 (admin/admin)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  🌻 Flower: http://localhost:5555"
echo ""
echo "Admin-Zugangsdaten:"
echo "  📧 E-Mail: admin@pyramid-computer.de"
echo "  🔑 Passwort: PyramidAdmin2024!"
echo ""
echo "Erste Schritte:"
echo "  1. Öffnen Sie http://localhost im Browser"
echo "  2. Melden Sie sich mit den Admin-Zugangsdaten an"
echo "  3. Erstellen Sie Benutzerkonten für Ihre Mitarbeiter"
echo "  4. Beginnen Sie mit dem Upload von Dokumenten"
echo ""
echo "Befehle:"
echo "  Logs anzeigen: docker-compose logs -f [service]"
echo "  Dienste stoppen: docker-compose down"
echo "  Dienste neustarten: docker-compose restart"
echo "  System aktualisieren: git pull && docker-compose up -d --build"
echo ""
echo "Bei Problemen siehe: docs/TROUBLESHOOTING.md"
echo ""
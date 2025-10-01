# Pyramid RAG Platform

Enterprise-Grade Retrieval-Augmented Generation Platform für Pyramid Computer GmbH

## 🎯 Überblick

Die Pyramid RAG Platform ist eine vollständig on-premise betriebene KI-gestützte Dokumentenmanagement- und Wissensdatenbank-Lösung. Sie ermöglicht es Mitarbeitern, Unternehmensdokumente hochzuladen, zu durchsuchen und über einen KI-Assistenten zu befragen.

### Hauptfunktionen

- 🤖 **KI-Chat-Assistent** mit Qwen 2.5 14B Modell
- 📄 **Dokumentenverarbeitung** für alle gängigen Geschäftsdateiformate (PDF, Word, Excel, CAD, etc.)
- 🔍 **Hybride Suche** (Semantisch + Stichwort)
- 🔐 **Abteilungsbasierte Zugriffskontrolle**
- 📊 **Monitoring & Metriken** mit Prometheus/Grafana
- 🚀 **GPU-beschleunigt** für optimale Performance
- 🏢 **100% On-Premise** ohne Cloud-Abhängigkeiten

## 📋 Systemanforderungen

### Minimum
- CPU: 8 Cores
- RAM: 32 GB
- Storage: 500 GB SSD (für 50-100 TB Dokumentenspeicher empfohlen: NAS/SAN)
- GPU: NVIDIA GPU mit 8GB VRAM (RTX 2070 oder besser)

### Empfohlen
- CPU: 16+ Cores
- RAM: 64 GB
- Storage: 2 TB NVMe SSD + Network Storage
- GPU: NVIDIA RTX 3090/4090 oder A100

### Software
- Docker 24.0+
- Docker Compose 2.20+
- NVIDIA Container Toolkit (für GPU-Support)
- Windows (später Windows Server) oder Linux (Ubuntu 20.04+ empfohlen)

## 🚀 Schnellstart

### 1. Repository klonen
```bash
git clone https://github.com/pyramid-computer/pyramid-rag.git
cd pyramid-rag
```

### 2. Installation ausführen
```bash
chmod +x setup.sh
./setup.sh
```

Das Setup-Skript:
- Überprüft Systemvoraussetzungen
- Erstellt Konfigurationsdateien
- Lädt Docker-Images herunter
- Installiert das Qwen 2.5 14B Modell
- Startet alle Dienste

### 3. Zugriff auf die Anwendung
- **Hauptanwendung**: http://localhost
- **Admin-Login**: admin@pyramid-computer.de / PyramidAdmin2024!

## 🏗️ Architektur

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│    Nginx    │────▶│   Backend   │
│   (React)   │     │   (Proxy)   │     │  (FastAPI)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐          ┌────────▼────────┐         ┌───────▼───────┐
              │PostgreSQL │          │     Redis       │         │    Ollama     │
              │+ pgvector │          │  (Queue/Cache)  │         │   (LLM/GPU)   │
              └───────────┘          └─────────────────┘         └───────────────┘
                    │                          │                          │
              ┌─────▼─────┐          ┌────────▼────────┐         ┌───────▼───────┐
              │  Storage  │          │ Celery Worker   │         │  Embeddings   │
              │  (Docs)   │          │  (Processing)   │         │   Service     │
              └───────────┘          └─────────────────┘         └───────────────┘
```

## 📁 Projektstruktur

```
pyramid-rag/
├── backend/               # FastAPI Backend
│   ├── app/
│   │   ├── api/          # API Endpoints
│   │   ├── core/         # Kernkonfiguration
│   │   ├── models/       # Datenbankmodelle
│   │   ├── services/     # Business Logic
│   │   └── workers/      # Celery Tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React Frontend
│   ├── src/
│   │   ├── components/   # UI-Komponenten
│   │   ├── pages/        # Seitenkomponenten
│   │   ├── services/     # API-Services
│   │   └── locales/      # Übersetzungen (DE/EN)
│   ├── package.json
│   └── Dockerfile
├── docker/               # Docker-Konfigurationen
│   ├── nginx/
│   ├── prometheus/
│   └── grafana/
├── docker-compose.yml    # Orchestrierung
├── setup.sh             # Installationsskript
└── README.md            # Diese Datei
```

## 🔧 Konfiguration

### Umgebungsvariablen

Wichtige Konfigurationen in `backend/.env`:

```env
# LLM Konfiguration
OLLAMA_MODEL=qwen2.5:14b
MAX_TOKENS=4096
TEMPERATURE=0.7

# Speicher-Sharding (für 50-100TB)
STORAGE_SHARDS=10

# Dokumentenverarbeitung
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Abteilungen

Vorkonfigurierte Abteilungen:
- PM (Projektmanagement)
- Technik
- QM (Qualitätsmanagement)
- Sales (Vertrieb)
- Marketing
- Purchasing (Einkauf)
- Buchhaltung
- Management (Geschäftsführung)
- Human Resource (Personalwesen)

## 📊 Monitoring

### Grafana Dashboards
Zugriff über http://localhost:3001 (admin/admin)

Verfügbare Dashboards:
- System Overview
- Document Processing Metrics
- LLM Performance
- Search Analytics
- User Activity

### Prometheus Metriken
Zugriff über http://localhost:9090

Wichtige Metriken:
- `api_requests_total` - API-Anfragen
- `document_processing_duration` - Verarbeitungszeit
- `llm_inference_time` - KI-Antwortzeit
- `search_latency` - Suchlatenz

## 🔐 Sicherheit

### Implementierte Sicherheitsmaßnahmen

- **JWT-basierte Authentifizierung** mit Refresh Tokens
- **Abteilungsbasierte Zugriffskontrolle** (RBAC)
- **Audit-Logging** aller kritischen Operationen
- **Rate Limiting** für API-Endpunkte
- **Input-Validierung** und Sanitization
- **Verschlüsselte Kommunikation** (TLS ready)
- **Sichere Passwort-Policies** (min. 8 Zeichen, Komplexität)

### Benutzerrollen

1. **Superuser**: Vollzugriff auf alle Funktionen
2. **Abteilungsleiter**: Verwaltung der Abteilungsdokumente
3. **Mitarbeiter**: Zugriff auf persönliche und freigegebene Dokumente

## 🛠️ Wartung

### Backup
```bash
# Datenbank-Backup
docker exec pyramid-postgres pg_dump -U pyramid pyramid_rag > backup_$(date +%Y%m%d).sql

# Dokumente-Backup
tar -czf documents_backup_$(date +%Y%m%d).tar.gz data/documents/
```

### Updates
```bash
git pull
docker-compose down
docker-compose up -d --build
```

### Logs
```bash
# Alle Logs
docker-compose logs -f

# Spezifische Services
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

## 📈 Performance-Optimierung

### GPU-Optimierung
```bash
# GPU-Auslastung prüfen
nvidia-smi

# VRAM-Nutzung optimieren
# In backend/.env:
EMBEDDING_BATCH_SIZE=16  # Bei wenig VRAM reduzieren
```

### Skalierung
```yaml
# docker-compose.yml - Mehrere Worker
celery-worker:
  deploy:
    replicas: 4
```

## 🐛 Fehlerbehebung

### Häufige Probleme

1. **LLM antwortet nicht**
   ```bash
   docker-compose restart ollama
   docker exec pyramid-ollama ollama list
   ```

2. **Dokumente werden nicht verarbeitet**
   ```bash
   docker-compose logs celery-worker
   docker-compose restart celery-worker
   ```

3. **Speicherprobleme**
   ```bash
   docker system prune -a
   ```

## 📚 API-Dokumentation

Die vollständige API-Dokumentation ist verfügbar unter:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Wichtige Endpoints

```http
POST   /api/v1/auth/login           # Anmeldung
GET    /api/v1/documents            # Dokumente abrufen
POST   /api/v1/documents/upload     # Dokument hochladen
POST   /api/v1/chat/message         # Chat-Nachricht senden
POST   /api/v1/search               # Dokumentensuche
```

## 🚀 Zukünftige Integrationen

- [ ] Microsoft Teams SSO
- [ ] SharePoint Connector
- [ ] Dynamics NAV/365 Integration
- [ ] E-Mail-Archivierung
- [ ] OCR für gescannte Dokumente
- [ ] Multi-Tenant-Unterstützung

## 📄 Lizenz

Proprietär - Pyramid Computer GmbH

## 🤝 Support

Für Support und Fragen:
- **E-Mail**: support@pyramid-computer.de
- **Intern**: IT-Helpdesk #7777

## 🙏 Credits

Entwickelt mit:
- FastAPI, React, PostgreSQL
- Ollama & Qwen 2.5
- Docker & Docker Compose
- Und viel ☕

---

**Version**: 1.0.0
**Datum**: 2024
**Entwickelt für**: Pyramid Computer GmbH
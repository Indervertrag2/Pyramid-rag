# GEMINI.md: Project Overview and Development Guide

## Project Overview

This project is the **Pyramid RAG Platform**, an enterprise-grade, on-premise retrieval-augmented generation (RAG) platform. It enables users to upload, search, and query company documents using an AI assistant.

### Main Technologies

*   **Backend:** Python with FastAPI
*   **Frontend:** React with TypeScript and Material-UI
*   **Database:** PostgreSQL with the `pgvector` extension for semantic search
*   **LLM Engine:** Qwen 2.5 14B served via Ollama, with GPU acceleration
*   **Document Processing:** Celery for asynchronous task handling
*   **Orchestration:** Docker and Docker Compose
*   **Monitoring:** Prometheus and Grafana

### Architecture

The system is composed of several microservices orchestrated by Docker Compose:

*   **`frontend`**: A React-based user interface.
*   **`nginx`**: A reverse proxy that routes traffic to the frontend and backend services.
*   **`backend`**: A FastAPI application that provides the core business logic and API.
*   **`postgres`**: A PostgreSQL database for storing metadata and vector embeddings.
*   **`redis`**: A Redis instance for caching and as a message broker for Celery.
*   **`celery-worker`**: A Celery worker that processes documents asynchronously.
*   **`celery-beat`**: A Celery scheduler for periodic tasks.
*   **`ollama`**: The service that runs the large language model.
*   **`prometheus`**: A service for collecting metrics.
*   **`grafana`**: A service for visualizing metrics.

## Building and Running

The project is designed to be run with Docker and Docker Compose.

### Prerequisites

*   Docker
*   Docker Compose
*   NVIDIA Container Toolkit (for GPU support)

### Setup and Execution

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pyramid-computer/pyramid-rag.git
    cd pyramid-rag
    ```

2.  **Run the setup script:**
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    This script will:
    *   Check for dependencies.
    *   Create configuration files.
    *   Download Docker images.
    *   Start all services.
    *   Pull the required LLM model.

3.  **Access the application:**
    *   **Main Application:** [http://localhost](http://localhost)
    *   **Admin Login:** `admin@pyramid-computer.de` / `PyramidAdmin2024!`
    *   **Grafana:** [http://localhost:3001](http://localhost:3001) (admin/admin)
    *   **Prometheus:** [http://localhost:9090](http://localhost:9090)
    *   **Flower (Celery Monitor):** [http://localhost:5555](http://localhost:5555)
    *   **API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

### Key `docker-compose` commands:

*   **Start all services:** `docker-compose up -d`
*   **Stop all services:** `docker-compose down`
*   **View logs:** `docker-compose logs -f [service_name]`
*   **Rebuild and restart:** `docker-compose up -d --build`

## Development Conventions

### Backend (Python/FastAPI)

*   **Dependency Management:** `pip` and `requirements.txt`.
*   **Code Style:** `black` for formatting, `flake8` for linting, and `mypy` for type checking.
*   **Testing:** `pytest` is used for unit and integration tests.
*   **Database Migrations:** `alembic` is used for managing database schema changes.
*   **Environment Variables:** Configuration is managed through a `.env` file.

### Frontend (React/TypeScript)

*   **Dependency Management:** `npm`.
*   **Build Tool:** `vite`.
*   **Code Style:** `prettier` for formatting and `eslint` for linting.
*   **Testing:** `vitest` and `react-testing-library`.
*   **UI Framework:** Material-UI (MUI).
*   **State Management:** Redux Toolkit.
*   **Data Fetching:** React Query and Axios.

### Key `npm` scripts (run from the `frontend` directory):

*   **Start development server:** `npm run dev`
*   **Build for production:** `npm run build`
*   **Run tests:** `npm run test`
*   **Lint and format:** `npm run lint` and `npm run format`

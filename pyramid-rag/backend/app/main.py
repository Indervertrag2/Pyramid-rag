from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("PYRAMID RAG PLATFORM - STARTING UP")
logger.info("=" * 80)

app = FastAPI(
    title="Pyramid RAG Platform",
    version="1.0.0",
    description="Enterprise RAG Platform für Pyramid Computer GmbH"
)

logger.info("✓ FastAPI application created")

# CORS configuration
logger.info("Configuring CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:4000",
        "http://localhost:8080",
        "http://localhost:18000",
        "http://127.0.0.1",
        "http://127.0.0.1:80"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)
logger.info("✓ CORS middleware configured")

# Include API routers
logger.info("Loading API routers (this may take some time for ML dependencies)...")
router_start = time.time()

logger.info("  - Loading system router...")
from app.api.endpoints import system
logger.info("  ✓ System router loaded")

logger.info("  - Loading auth router...")
from app.api.endpoints import auth
logger.info("  ✓ Auth router loaded")

logger.info("  - Loading documents router (heavy ML libraries - please wait)...")
doc_start = time.time()
from app.api.endpoints import documents
logger.info(f"  ✓ Documents router loaded ({time.time() - doc_start:.1f}s)")

logger.info("  - Loading chat router...")
from app.api.endpoints import chat
logger.info("  ✓ Chat router loaded")

logger.info("  - Loading sessions router...")
from app.api.endpoints import sessions
logger.info("  ✓ Sessions router loaded")

logger.info("  - Loading search router...")
from app.api.endpoints import search
logger.info("  ✓ Search router loaded")

logger.info("  - Loading admin router...")
from app.api.endpoints import admin
logger.info("  ✓ Admin router loaded")

logger.info("  - Loading users router...")
from app.api.endpoints import users
logger.info("  ✓ Users router loaded")

logger.info("  - Loading MCP router...")
from app.api.endpoints import mcp
logger.info("  ✓ MCP router loaded")

logger.info(f"✓ All routers loaded in {time.time() - router_start:.1f}s")

# Register all routers
logger.info("Registering routers with FastAPI...")
app.include_router(system.router)          # Root, health, metrics, stats
app.include_router(auth.router)            # /api/v1/auth/*
app.include_router(documents.router)       # /api/v1/documents/*
app.include_router(chat.router)            # /api/v1/chat/*
app.include_router(sessions.router)        # /api/v1/chat/sessions/*
app.include_router(search.router)          # /api/v1/search/*
app.include_router(admin.router)           # /api/v1/admin/*
app.include_router(users.router)           # /api/v1/users/*
app.include_router(mcp.router)             # /api/v1/mcp/*
logger.info("✓ All routers registered")

logger.info("=" * 80)
logger.info("PYRAMID RAG PLATFORM - READY TO ACCEPT CONNECTIONS")
logger.info("=" * 80)


@app.on_event("startup")
async def startup_event():
    """Initialize database and create admin user on startup."""
    from app.utils.startup import initialize_database, create_admin_user

    logger.info("Running startup initialization...")
    try:
        await initialize_database()
        await create_admin_user()
        logger.info("Startup initialization completed successfully")
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        # Don't raise - allow app to start even if initialization has issues


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

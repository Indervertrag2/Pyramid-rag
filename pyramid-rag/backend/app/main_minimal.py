from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Pyramid RAG Platform",
    version="1.0.0",
    description="Enterprise RAG Platform für Pyramid Computer GmbH"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002", "http://localhost:4000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models for demo
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

@app.get("/")
async def root():
    return {
        "name": "Pyramid RAG Platform",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "api": "healthy"
        }
    }

# Simple demo login endpoint
@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Demo admin credentials
    if request.email == "admin@pyramid-computer.de" and request.password == "PyramidAdmin2024!":
        return LoginResponse(
            access_token="demo-access-token-12345",
            refresh_token="demo-refresh-token-12345",
            user={
                "id": "1",
                "email": request.email,
                "username": "admin",
                "full_name": "System Administrator",
                "primary_department": "Management",
                "is_superuser": True
            }
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültige E-Mail oder Passwort"
    )

@app.get("/api/v1/auth/me")
async def get_current_user():
    # Demo user info
    return {
        "id": "1",
        "email": "admin@pyramid-computer.de",
        "username": "admin",
        "full_name": "System Administrator",
        "primary_department": "Management",
        "is_superuser": True
    }
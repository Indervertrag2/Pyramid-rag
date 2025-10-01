# Pyramid RAG Platform - Complete Codebase Review & Variable Documentation
# Date: 2025-09-26
# CRITICAL: This document MUST be checked before ANY code changes!

## 🔴 CRITICAL ISSUES TO FIX

### 1. Authentication System Issues
- **Problem**: Bcrypt password hashing is broken
- **Root Cause**: passlib/bcrypt version incompatibility
- **Files Affected**:
  - app/auth.py
  - app/main.py (login endpoint)
  - app/api/endpoints/auth.py

### 2. Import Path Inconsistencies
- **Problem**: Mixed imports (app.models vs app.models.models)
- **Status**: NEEDS SYSTEMATIC FIX
- **Files to Check**: ALL Python files

### 3. Database Field Naming Issues
- **Problem**: Inconsistent field names across models and schemas
- **Critical Fields**:
  - `hashed_password` vs `password_hash`
  - `meta_data` vs `metadata` (SQLAlchemy reserved)
  - `created_at` vs `created`
  - `updated_at` vs `updated`

## 📋 COMPLETE VARIABLE MAPPING

### User Authentication Variables
| Location | Variable Name | Type | Value/Format | Notes |
|----------|--------------|------|--------------|-------|
| .env | ADMIN_EMAIL | string | admin@pyramid-computer.de | Admin login email |
| .env | ADMIN_PASSWORD | string | PyramidAdmin2024! | Admin login password |
| models.py | hashed_password | Column(String) | bcrypt hash | MUST use this name |
| schemas.py | password | str | plain text | Input field |
| auth.py | pwd_context | CryptContext | bcrypt handler | Password hashing |

### Database Connection Variables
| Location | Variable Name | Type | Value/Format | Notes |
|----------|--------------|------|--------------|-------|
| .env | DATABASE_URL | string | postgresql+asyncpg://... | Full connection string |
| docker-compose.yml | POSTGRES_USER | string | pyramid | PostgreSQL superuser |
| docker-compose.yml | POSTGRES_PASSWORD | string | pyramid_secure_pass | PostgreSQL superuser pass |
| init.sql | pyramid_user | DB user | - | Application user |
| init.sql | pyramid_pass | password | - | Application password |
| .env | pyramid_user | in URL | pyramid_user | MUST match init.sql |
| .env | pyramid_pass | in URL | pyramid_pass | MUST match init.sql |

### Model Field Names (SQLAlchemy)
| Model | Field | Type | Schema Field | API Field |
|-------|-------|------|--------------|-----------|
| User | id | UUID | id | id |
| User | email | String | email | email |
| User | hashed_password | String | - | - |
| User | username | String | username | username |
| User | full_name | String | full_name | full_name |
| User | primary_department | Enum | department | department |
| User | is_superuser | Boolean | is_superuser | is_superuser |
| User | is_active | Boolean | is_active | is_active |
| User | created_at | DateTime | created_at | created_at |
| User | updated_at | DateTime | updated_at | updated_at |

### Department Enum Values
| Database | Python Enum | Frontend | API |
|----------|-------------|----------|-----|
| MANAGEMENT | Department.MANAGEMENT | "Management" | "MANAGEMENT" |
| SUPPORT | Department.SUPPORT | "Support" | "SUPPORT" |
| DEVELOPMENT | Department.DEVELOPMENT | "Development" | "DEVELOPMENT" |
| SALES | Department.SALES | "Sales" | "SALES" |
| MARKETING | Department.MARKETING | "Marketing" | "MARKETING" |
| FINANCE | Department.FINANCE | "Finance" | "FINANCE" |
| HR | Department.HR | "HR" | "HR" |
| LEGAL | Department.LEGAL | "Legal" | "LEGAL" |
| OPERATIONS | Department.OPERATIONS | "Operations" | "OPERATIONS" |

### API Endpoints
| Method | Path | Auth | Purpose | Request Body |
|--------|------|------|---------|--------------|
| POST | /api/v1/auth/login | No | User login | {email, password} |
| POST | /api/v1/auth/refresh | Yes | Refresh token | {refresh_token} |
| GET | /api/v1/auth/me | Yes | Get current user | - |
| POST | /api/v1/auth/logout | Yes | Logout | - |

### Environment Variables (.env)
| Variable | Current Value | Required | Notes |
|----------|---------------|----------|-------|
| SECRET_KEY | your-super-secret-key... | Yes | JWT signing key |
| ALGORITHM | HS256 | Yes | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Yes | Should be 259200 (6 months) |
| DATABASE_URL | postgresql+asyncpg://... | Yes | MUST match docker user |
| OLLAMA_BASE_URL | http://ollama:11434 | Yes | Docker service name |
| ADMIN_EMAIL | admin@pyramid-computer.de | Yes | Default admin |
| ADMIN_PASSWORD | PyramidAdmin2024! | Yes | Default admin pass |

## 🔍 FILE-BY-FILE REVIEW CHECKLIST

### ✅ Files Reviewed and Fixed
- [ ] app/auth.py - Password hashing logic
- [ ] app/models.py - Database models
- [ ] app/schemas.py - Pydantic schemas
- [ ] app/main.py - FastAPI application
- [ ] app/database.py - Database connection
- [ ] app/api/deps.py - Dependencies
- [ ] app/api/endpoints/auth.py - Auth endpoints
- [ ] app/api/endpoints/admin.py - Admin endpoints
- [ ] app/api/endpoints/chat.py - Chat endpoints
- [ ] app/api/endpoints/documents.py - Document endpoints
- [ ] app/api/endpoints/search.py - Search endpoints
- [ ] app/api/endpoints/users.py - User endpoints

### ⚠️ Known Issues by File

#### app/auth.py
- Line 17-22: verify_password needs bcrypt fix
- Line 24-29: get_password_hash needs bcrypt fix
- Missing: Password truncation for bcrypt 72-byte limit

#### app/main.py
- Line 360: authenticate_user call fails due to bcrypt
- Line 801: pwd_context not imported
- Line 917: password_hash should be hashed_password

#### app/models.py
- Line 110: metadata field conflicts with SQLAlchemy
- Must use: meta_data instead

#### app/schemas.py
- Check all response models match database fields
- Ensure department enum matches

#### app/api/deps.py
- Import paths need verification
- Should import from app.models not app.models.models

## 🚨 IMMEDIATE FIXES NEEDED

1. **Fix Bcrypt Password Hashing**
```python
# In app/auth.py
from passlib.context import CryptContext
import bcrypt

# Use direct bcrypt instead of passlib
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
```

2. **Fix All Import Paths**
```python
# WRONG:
from app.models.models import User
from app.core.database import get_db

# CORRECT:
from app.models import User
from app.database import get_db
```

3. **Fix Field Name Consistency**
```python
# In all files, use:
hashed_password  # NOT password_hash
meta_data       # NOT metadata
created_at      # NOT created
updated_at      # NOT updated
```

4. **Fix Department Enum**
```python
# Ensure consistency:
class Department(str, Enum):
    MANAGEMENT = "MANAGEMENT"  # All uppercase
    SUPPORT = "SUPPORT"
    # etc...
```

## 📝 TESTING CHECKLIST

After fixes, test in this order:
1. [ ] Database connection: `docker exec pyramid-postgres psql -U pyramid_user -d pyramid_rag -c '\dt'`
2. [ ] Backend health: `curl http://localhost:18000/health`
3. [ ] Login endpoint: `curl -X POST http://localhost:18000/api/v1/auth/login ...`
4. [ ] Frontend access: Open http://localhost:3002
5. [ ] Create user via API
6. [ ] Upload document
7. [ ] Chat functionality
8. [ ] Search functionality

## 🔧 DOCKER SERVICES STATUS

| Service | Port | Health Check | Current Status |
|---------|------|--------------|----------------|
| pyramid-postgres | 15432 | pg_isready | Check needed |
| pyramid-redis | 16379 | redis-cli ping | Check needed |
| pyramid-ollama | 11434 | ollama list | Check needed |
| pyramid-backend | 18000 | /health endpoint | Degraded |
| pyramid-frontend | 3002 | HTTP 200 | Check needed |

## ⚡ QUICK FIX COMMANDS

```bash
# Restart all services
docker-compose -f pyramid-rag/docker-compose.yml restart

# Check logs
docker logs pyramid-backend --tail 50

# Fix database user
docker exec pyramid-postgres psql -U pyramid -d pyramid_rag -c "CREATE USER pyramid_user WITH PASSWORD 'pyramid_pass';"

# Test login
curl -X POST http://localhost:18000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email": "admin@pyramid-computer.de", "password": "admin123"}'
```

## 📌 REMEMBER
- ALWAYS check this document before making changes
- ALWAYS use the exact variable names listed here
- NEVER assume a variable name - check this document
- ALWAYS test after each change
- DOCUMENT any new variables or changes here
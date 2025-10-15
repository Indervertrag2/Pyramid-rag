# Developer Guidelines

This document outlines the key architectural patterns and development conventions for the Pyramid RAG project. All future development must adhere to these guidelines to ensure the codebase remains secure, maintainable, and performant.

## Backend (Python/FastAPI)

### 1. Architecture
- **API Routers:** All API endpoints MUST be organized into domain-specific router files within the `app/api/endpoints/` directory. The main `app/main.py` file is strictly for application startup, middleware configuration, and including these routers.
- **Service Layer:** Complex business logic should be encapsulated in service classes within the `app/services/` directory (e.g., `MCPGateway`). Endpoints should be lightweight and delegate complex work to these services.
- **Background Tasks:** Any long-running (>1 second) or resource-intensive operations (like file processing, embeddings, or external API calls) MUST be implemented as asynchronous Celery tasks in the `app/workers/` directory. This keeps the API responsive.

### 2. Database (SQLAlchemy)
- **Asynchronous Sessions:** All `async def` API endpoints that access the database MUST use the `get_async_db` dependency to get an `AsyncSession`. Do not use synchronous sessions in async code.
- **Indexing:** All `ForeignKey` columns in `app/models.py` MUST include `index=True` to ensure efficient query performance.
- **Vector Storage:** All vector embedding columns MUST use the `Vector` type from the `pgvector-sqlalchemy` library (e.g., `Column(Vector(384))`). Do not store vectors as JSON.

### 3. Security
- **Configuration:** No secrets, keys, or URLs should be hardcoded. All configuration MUST be loaded from environment variables.
- **Password Hashing:** All user passwords MUST be hashed using the `get_password_hash` function in `app/auth.py`, which uses a secure SHA-256 pre-hash followed by bcrypt.
- **File Uploads:** All user-provided filenames MUST be sanitized using the `sanitize_filename` utility in `app/utils/file_security.py` before being used in any filesystem operations to prevent path traversal attacks.

## Frontend (React/TypeScript)

### 1. Component Architecture
- **Composition over Monoliths:** Avoid creating large, monolithic "god components". UI should be broken down into smaller, single-purpose, reusable components located in `src/components/`.
- **State Management:**
    - For simple, local UI state, use `useState`.
    - For complex state shared across the application, use React Context (e.g., `AuthContext`).
    - Do not introduce new global state management libraries without a team decision.
- **Type Definitions:** All shared TypeScript interfaces and types MUST be defined in `src/types/index.ts` to serve as a single source of truth.

### 2. API Communication
- **Centralized API Client:** All HTTP requests to the backend MUST be made through the central `apiClient` instance located at `src/services/apiClient.ts`.
- **No Hardcoded URLs:** Do not use `fetch` or raw `axios` with hardcoded URLs in components. The `apiClient` is pre-configured with the correct base URL from environment variables.
- **Authentication:** The `apiClient` automatically handles adding the `Authorization` header to all requests. You do not need to do this manually in components.

### 3. State Persistence
- **Avoid Direct `localStorage` Writes:** Do not call `localStorage.setItem()` directly from within component event handlers (like `onClick`). This can cause race conditions.
- **Use `useEffect` for Synchronization:** To persist React state to `localStorage`, use a `useEffect` hook that triggers whenever the state variable changes. This ensures the persisted data is always in sync with the rendered state.

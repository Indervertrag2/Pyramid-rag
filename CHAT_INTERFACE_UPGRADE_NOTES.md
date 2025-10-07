# Chat Interface Upgrade Notes (2025-10-06)

## Overview
The current chat UI remains intact and is backed up as rontend/src/pages/ChatInterface.legacy.tsx. The following notes capture the required context and tasks for extending the chat experience so that uploaded documents are fully usable in prompts and previewable within the UI.

## Key Files To Review
- ackend/app/main.py
- ackend/app/schemas.py
- ackend/app/services/document_processor.py
- rontend/src/services/MCPClient.ts
- rontend/src/pages/ChatInterface.tsx
- Optional build helpers (rontend/Dockerfile, .env.local, rontend/build/*) for rebuilds

## Backend Objectives
1. **Upload Response Enhancements**
   - Include extracted content, content length, MIME type, processing stats, and stored filenames when returning from POST /api/v1/documents/upload for both GLOBAL and CHAT scopes.

2. **Chat File Detail Endpoint**
   - Add GET /api/v1/chat/files/{file_id} returning ChatFileDetailResponse with permission checks.
   - Ensure response includes content excerpt, metadata, timestamps, and MIME type.

3. **Schema Updates**
   - Expand DocumentResponse and ChatFileDetailResponse to align with the richer payload (optional fields with safe defaults).

## Frontend Objectives
1. **Service Layer (MCPClient.ts)**
   - Use getBaseUrl() instead of hard-coded URLs.
   - Pass structured uploaded_documents when streaming messages.

2. **Chat Interface (ChatInterface.tsx)**
   - Introduce UploadedDocumentInfo type and normalize saved sessions (timestamps, uploaded docs) on load.
   - Refactor createNewSession, handleFileUpload, and sendMessage to:
     - Persist sessions via functional state updates + LocalStorage sync.
     - Upload files through the backend endpoint, capture returned content and metadata, and make it available to prompts.
     - Render document chips below the input and open a preview dialog when clicked.
   - Implement a Dialog-based preview showing text excerpts; fallback to simple description for unsupported formats.

3. **UI Adjustments**
   - Add chips with InsertDriveFileIcon referencing uploaded documents.
   - Display the actual titles in the “Verfuegbare Dateien” section instead of placeholder dots.
   - Remove lingering mojibake (VerfA�gbare → Verfuegbare, etc.).

## Testing Checklist
- Upload documents (GLOBAL/CHAT) and ensure they appear in the chip list.
- Send prompts referencing uploads and verify the LLM sees injected content.
- Open the preview dialog and confirm the document excerpt renders.
- Refresh and switch sessions: confirm LocalStorage normalization works.
- Rebuild frontend (
pm run build or Docker) after changes.

## Notes
- Original chat UI is preserved at rontend/src/pages/ChatInterface.legacy.tsx.
- Work incrementally; each major change should be verified before moving on.
- Use functional state updates whenever syncing sessions with LocalStorage.

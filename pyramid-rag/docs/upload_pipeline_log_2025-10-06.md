# Upload Pipeline Check - 2025-10-06 19:36:38 +02:00

- Queried chat_files and documents: recent PDF uploads showed meta_data.extraction_method = text_latin-1, meaning the extractor fell back to raw text decoding.
- Inspected ackend/app/services/document_processor.py: without PyMuPDF the code used _extract_plain_text, which explains the gibberish output.
- equirements.txt doesn’t install PyMuPDF, so I added a pypdf.PdfReader fallback and applied shared sanitizing logic before storing/returning content.
- Added pp/services/text_utils.py and reuse it when shaping upload responses, chat-file detail endpoints, and SSE metadata.
- Updated MCP streaming (mcp_network_server.py / main.py) to cache upload + search hits and send them with the final done event.
- Frontend (ChatInterface.tsx) now normalizes citations, renders preview chips, and opens detail dialogs via /api/v1/chat/files/{id} or /api/v1/documents/{id}.
- Verified with pytest backend/test_upload_response.py -q and 
pm test -- chatDocuments; sample PDF uploads now produce readable summaries and clickable previews.

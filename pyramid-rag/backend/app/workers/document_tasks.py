from pathlib import Path
import asyncio
import logging
from typing import Any, Dict, List, Optional

from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import Document, DocumentChunk, DocumentEmbedding
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

document_processor = DocumentProcessor()


def _clear_existing_chunks(session, document_id: str) -> None:
    session.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete(synchronize_session=False)
    session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)


def _store_chunks_and_embeddings(
    session,
    document: Document,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    embedding_model: Optional[str],
) -> None:
    resolved_model = embedding_model or (document.meta_data or {}).get("embedding_model")

    for index, chunk_info in enumerate(chunks):
        content = chunk_info.get("content", "")
        if not content.strip():
            continue

        word_count = chunk_info.get("word_count")
        metadata = {
            "word_count": word_count,
            "start_word": chunk_info.get("start_word"),
            "end_word": chunk_info.get("end_word"),
        }

        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            content=content,
            content_length=chunk_info.get("character_count"),
            embedding=embeddings[index] if index < len(embeddings) else None,
            meta_data=metadata,
            token_count=word_count,
        )
        session.add(chunk)
        session.flush()

        if index < len(embeddings) and embeddings[index] is not None:
            embedding_row = DocumentEmbedding(
                document_id=document.id,
                chunk_id=chunk.id,
                embedding=embeddings[index],
                model_name=resolved_model,
            )
            session.add(embedding_row)


def _mark_document_error(document_id: str, message: str) -> None:
    retry_session = SessionLocal()
    try:
        doc = retry_session.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_error = message
            doc.processed = False
            retry_session.commit()
    except Exception:
        retry_session.rollback()
        logger.exception("Failed to persist error state for document %s", document_id)
    finally:
        retry_session.close()


@shared_task
def process_document(document_id: str):
    """Process a document asynchronously using the shared document processor."""
    session = SessionLocal()
    logger.info("Processing document %s", document_id)

    try:
        document: Optional[Document] = (
            session.query(Document).filter(Document.id == document_id).first()
        )

        if document is None:
            logger.warning("Document %s not found", document_id)
            return {"status": "not_found", "document_id": document_id}

        if not document.file_path:
            logger.error("Document %s has no file path", document_id)
            document.processing_error = "Missing file path"
            document.processed = False
            session.commit()
            return {"status": "error", "document_id": document_id, "error": "missing_file_path"}

        file_path = Path(document.file_path)
        if not file_path.exists():
            logger.error("File for document %s does not exist at %s", document_id, file_path)
            document.processing_error = f"File not found: {file_path}"
            document.processed = False
            session.commit()
            return {
                "status": "error",
                "document_id": document_id,
                "error": "file_not_found",
            }

        async def _run_processing():
            return await document_processor.process_document(
                file_path=file_path,
                original_filename=document.original_filename,
            )

        result = asyncio.run(_run_processing())

        if not result.get("success"):
            error_message = "; ".join(result.get("errors") or ["Unknown processing error"])
            document.processing_error = error_message
            document.processed = False
            session.commit()
            logger.error("Processing failed for document %s: %s", document_id, error_message)
            return {
                "status": "error",
                "document_id": document_id,
                "error": error_message,
            }

        chunks: List[Dict[str, Any]] = result.get("chunks") or []
        embeddings: List[List[float]] = result.get("embeddings") or []
        metadata: Dict[str, Any] = result.get("metadata") or {}

        _clear_existing_chunks(session, document.id)

        document.content = result.get("content", "")
        document.language = result.get("language")
        document.meta_data = {**(document.meta_data or {}), **metadata}
        document.processing_error = None
        document.processed = True

        _store_chunks_and_embeddings(session, document, chunks, embeddings, metadata.get("embedding_model"))

        session.commit()
        logger.info("Document %s processed successfully", document_id)
        return {"status": "success", "document_id": document_id, "chunks": len(chunks)}

    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Database error while processing document %s", document_id)
        _mark_document_error(document_id, str(exc))
        return {"status": "error", "document_id": document_id, "error": str(exc)}
    except Exception as exc:
        session.rollback()
        logger.exception("Unexpected error while processing document %s", document_id)
        _mark_document_error(document_id, str(exc))
        return {"status": "error", "document_id": document_id, "error": str(exc)}
    finally:
        session.close()

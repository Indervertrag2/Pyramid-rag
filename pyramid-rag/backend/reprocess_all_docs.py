from contextlib import suppress

from app.database import SessionLocal
from app.models import Document
from app.workers.document_tasks import process_document


def main() -> None:
    session = SessionLocal()
    try:
        documents = session.query(Document.id, Document.original_filename).all()
        if not documents:
            print("No documents found to reprocess.")
            return

        for doc_id, original_filename in documents:
            process_document.delay(str(doc_id))
            name = original_filename or "(unnamed document)"
            print(f"Queued document {doc_id} - {name} for reprocessing")
    finally:
        with suppress(Exception):
            session.close()


if __name__ == "__main__":
    main()

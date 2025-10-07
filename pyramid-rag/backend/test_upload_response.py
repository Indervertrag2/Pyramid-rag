from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models import Department, FileType
from app.schemas import FileScopeEnum
from app.services.upload_response import prepare_upload_response


@pytest.fixture
def processing_result_base():
    return {
        "content": "A" * 9000,
        "language": "de",
        "processing_time": 0.42,
        "chunks": [{"content": "chunk-1"}, {"content": "chunk-2"}],
        "embeddings": [[0.1], [0.2]],
    }


def test_prepare_upload_response_global(processing_result_base):
    document_id = uuid4()
    uploader_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        filename="stored.pdf",
        original_filename="report.pdf",
        file_type=FileType.PDF,
        file_size=2048,
        mime_type="application/pdf",
        title="Quartalsbericht",
        department=Department.MANAGEMENT,
        processed=True,
        uploaded_by=uploader_id,
        created_at=datetime(2024, 1, 1, 10, 0, 0),
        updated_at=datetime(2024, 1, 2, 11, 0, 0),
    )

    metadata = {
        "allowed_departments": ["ALL"],
        "title": "Quartalsbericht",
    }

    current_user = SimpleNamespace(
        id=uuid4(),
        primary_department=Department.MANAGEMENT,
    )

    response = prepare_upload_response(
        document=document,
        processing_result=processing_result_base,
        metadata=metadata,
        scope=FileScopeEnum.GLOBAL,
        current_user=current_user,
        session_id=None,
    )

    assert response["success"] is True
    assert response["message"] == "Dokument in der Firmendatenbank gespeichert."
    assert response["scope"] == "GLOBAL"
    assert response["session_id"] is None
    assert response["document_id"] == str(document_id)
    assert response["filename"] == "stored.pdf"
    assert response["original_filename"] == "report.pdf"
    assert response["file_type"] == FileType.PDF.value
    assert response["chunks_created"] == 2
    assert response["embeddings_generated"] is True
    assert response["content_length"] == len(processing_result_base["content"])
    assert len(response["content"]) == 8000
    assert response["content"].endswith("A")
    assert response["content_preview"].startswith("AA")
    assert response["content_preview"].endswith("...")
    assert response["meta_data"]["allowed_departments"] == ["ALL"]
    assert response["meta_data"]["scope"] == "GLOBAL"
    assert response["department"] == Department.MANAGEMENT.value
    assert response["processed"] is True
    assert response["uploaded_by"] == str(uploader_id)
    assert response["created_at"].startswith("2024-01-01T10:00:00")
    assert response["updated_at"].startswith("2024-01-02T11:00:00")


def test_prepare_upload_response_chat_scope(processing_result_base):
    document_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        filename="chat-file.txt",
        original_filename="chat-file.txt",
        file_type="text",
        file_size=512,
        mime_type="text/plain",
        title=None,
        department=None,
        processed=False,
        uploaded_by=None,
        created_at=None,
        updated_at=None,
    )

    metadata = {}

    current_user = SimpleNamespace(
        id=uuid4(),
        primary_department=Department.ENTWICKLUNG,
    )

    response = prepare_upload_response(
        document=document,
        processing_result=processing_result_base,
        metadata=metadata,
        scope=FileScopeEnum.CHAT,
        current_user=current_user,
        session_id="session-123",
    )

    assert response["message"] == "Datei im Chat-Kontext verfuegbar."
    assert response["scope"] == "CHAT"
    assert response["session_id"] == "session-123"
    assert response["processed"] is False
    assert response["file_type"] == "text"
    assert response["department"] == Department.ENTWICKLUNG.value
    assert response["access_departments"] == [Department.ENTWICKLUNG.value]
    assert response["meta_data"]["allowed_departments"] == [Department.ENTWICKLUNG.value]
    assert response["meta_data"]["scope"] == "CHAT"
    assert response["uploaded_by"] == str(current_user.id)
    assert response["created_at"] is None
    assert response["updated_at"] is None
    assert response["content_length"] == len(processing_result_base["content"])
    assert len(response["content"]) == 8000

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.schemas import FileScopeEnum
from app.services.text_utils import sanitize_document_text


def _to_enum_value(value: Any) -> Optional[str]:
    """Return the underlying value for enum-like objects."""
    if value is None:
        return None
    return getattr(value, "value", value)


def _department_name(document: Any, current_user: Any) -> Optional[str]:
    department_attr = getattr(document, "department", None)
    if hasattr(department_attr, "value"):
        return department_attr.value
    if isinstance(department_attr, str):
        return department_attr

    user_department = getattr(current_user, "primary_department", None)
    if hasattr(user_department, "value"):
        return user_department.value
    if isinstance(user_department, str):
        return user_department
    return None


def _stringify_uuid(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None


def prepare_upload_response(
    *,
    document: Any,
    processing_result: Dict[str, Any],
    metadata: Optional[Dict[str, Any]],
    scope: FileScopeEnum,
    current_user: Any,
    session_id: Optional[str],
) -> Dict[str, Any]:
    """Format the unified upload response payload for both GLOBAL and CHAT scopes."""

    full_content = processing_result.get("content") or ""
    sanitized_content = sanitize_document_text(full_content)
    content_length = len(sanitized_content)
    content_excerpt = sanitized_content[:8000]
    content_preview = sanitized_content[:200] + "..." if content_length > 200 else sanitized_content

    stored_filename = getattr(document, "filename", None)
    original_filename = (
        getattr(document, "original_filename", None)
        or getattr(document, "filename", None)
        or ""
    )

    metadata_payload: Dict[str, Any] = dict(metadata or {})
    allowed_departments = metadata_payload.get("allowed_departments")
    if not isinstance(allowed_departments, list):
        allowed_departments = []
    access_departments = [dep for dep in allowed_departments if isinstance(dep, str)]

    user_department = getattr(current_user, "primary_department", None)
    if not access_departments and user_department is not None:
        if hasattr(user_department, "value"):
            access_departments = [user_department.value]
        elif isinstance(user_department, str):
            access_departments = [user_department]

    metadata_payload["allowed_departments"] = access_departments

    scope_value = scope.value if isinstance(scope, FileScopeEnum) else str(scope)
    metadata_payload.setdefault("scope", scope_value)

    department_name = _department_name(document, current_user)
    processed_flag = bool(getattr(document, "processed", True))
    uploaded_by_value = getattr(document, "uploaded_by", None)
    uploaded_by = _stringify_uuid(uploaded_by_value) or _stringify_uuid(getattr(current_user, "id", None))

    created_ts: Optional[datetime] = getattr(document, "created_at", None)
    updated_ts: Optional[datetime] = getattr(document, "updated_at", None)

    file_type_attr = getattr(document, "file_type", None)
    file_type_value = _to_enum_value(file_type_attr) or "unknown"

    message = (
        "Dokument in der Firmendatenbank gespeichert."
        if scope_value == FileScopeEnum.GLOBAL.value
        else "Datei im Chat-Kontext verfuegbar."
    )

    session_reference = session_id if scope_value == FileScopeEnum.CHAT.value else None

    return {
        "success": True,
        "message": message,
        "duplicate": False,
        "document_id": str(getattr(document, "id")),
        "title": getattr(document, "title", None) or original_filename,
        "filename": stored_filename or original_filename,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_type": file_type_value,
        "file_size": getattr(document, "file_size", None),
        "mime_type": getattr(document, "mime_type", None),
        "language": processing_result.get("language"),
        "scope": scope_value,
        "session_id": session_reference,
        "processing_time": processing_result.get("processing_time"),
        "chunks_created": len(processing_result.get("chunks") or []),
        "embeddings_generated": bool(processing_result.get("embeddings")),
        "content_preview": content_preview,
        "content": content_excerpt,
        "content_length": content_length,
        "meta_data": metadata_payload,
        "department": department_name,
        "access_departments": access_departments,
        "processed": processed_flag,
        "uploaded_by": uploaded_by,
        "created_at": created_ts.isoformat() if isinstance(created_ts, datetime) else None,
        "updated_at": (
            updated_ts.isoformat() if isinstance(updated_ts, datetime)
            else (created_ts.isoformat() if isinstance(created_ts, datetime) else None)
        ),
    }

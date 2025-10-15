
"""Utilities for securely handling user-provided filenames."""

import os
import re
import unicodedata
import uuid
from pathlib import Path

SAFE_FILENAME_PATTERN = re.compile(r'[^A-Za-z0-9._-]')
MAX_FILENAME_LENGTH = 140


def sanitize_filename(filename: str, fallback_prefix: str = 'upload') -> str:
    """Return a filesystem-safe version of the provided filename.

    The function removes directory components, normalises to ASCII, replaces
    unsafe characters, and enforces a maximum length. A fallback name is
    generated when the input is empty or unsafe.
    """
    if not filename:
        return f'{fallback_prefix}-{uuid.uuid4().hex}'

    name = Path(filename).name  # drop any provided path components
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii', errors='ignore')
    name = name.replace(' ', '_')
    name = SAFE_FILENAME_PATTERN.sub('_', name)
    name = name.strip('._')

    if not name:
        return f'{fallback_prefix}-{uuid.uuid4().hex}'

    if len(name) > MAX_FILENAME_LENGTH:
        stem, ext = os.path.splitext(name)
        ext = ext[:15]
        stem = stem[: MAX_FILENAME_LENGTH - len(ext)]
        name = f'{stem}{ext}'

    return name or f'{fallback_prefix}-{uuid.uuid4().hex}'


def ensure_within_directory(base_dir: Path, target_path: Path) -> Path:
    """Ensure target_path is within base_dir, raising ValueError otherwise."""
    base_resolved = base_dir.resolve()
    target_resolved = target_path.resolve()
    if not target_resolved.is_relative_to(base_resolved):
        raise ValueError('Attempted path traversal outside permitted directory')
    return target_resolved


def secure_join(base_dir: Path, filename: str, fallback_prefix: str = 'upload') -> Path:
    """Create a safe path inside base_dir for the provided filename."""
    sanitized = sanitize_filename(filename, fallback_prefix=fallback_prefix)
    candidate = base_dir / sanitized
    return ensure_within_directory(base_dir, candidate)

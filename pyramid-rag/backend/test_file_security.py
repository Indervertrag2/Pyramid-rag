
from pathlib import Path

from app.utils.file_security import sanitize_filename, secure_join


def test_sanitize_filename_removes_traversal_sequences():
    sanitized = sanitize_filename(r"..\..//evil name?.pdf")
    assert sanitized.endswith('.pdf')
    assert '/' not in sanitized
    assert chr(92) not in sanitized
    assert 'evil' in sanitized


def test_sanitize_filename_generates_fallback_for_empty_input():
    sanitized = sanitize_filename('...')
    assert sanitized.startswith('upload-')
    assert len(sanitized) > len('upload-')


def test_secure_join_keeps_files_within_base(tmp_path: Path):
    base_dir = tmp_path / 'uploads'
    base_dir.mkdir()

    secure_path = secure_join(base_dir, '../../outside.txt')
    assert secure_path.parent == base_dir
    assert secure_path.name == 'outside.txt'


import importlib
import sys
from types import SimpleNamespace
from pathlib import Path

import bcrypt
import pytest


def _import_auth(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, env_value=None, file_contents=None, preserve_existing=False):
    module_name = 'app.auth'
    secret_file = tmp_path / 'secret.key'
    secret_file.parent.mkdir(parents=True, exist_ok=True)

    if file_contents is not None:
        secret_file.write_text(file_contents, encoding='utf-8')
    elif not preserve_existing and secret_file.exists():
        secret_file.unlink()

    monkeypatch.setenv('SECRET_KEY_FILE', str(secret_file))
    if env_value is None:
        monkeypatch.delenv('SECRET_KEY', raising=False)
    else:
        monkeypatch.setenv('SECRET_KEY', env_value)

    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    return module, secret_file


def _cleanup_auth_module():
    sys.modules.pop('app.auth', None)


def test_secret_key_prefers_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    auth_module, secret_file = _import_auth(monkeypatch, tmp_path, env_value='super-secret-key-1234567890-abcdef')
    try:
        assert auth_module.SECRET_KEY == 'super-secret-key-1234567890-abcdef'
        assert not secret_file.exists()
    finally:
        _cleanup_auth_module()


def test_secret_key_generated_and_persisted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    auth_module, secret_file = _import_auth(monkeypatch, tmp_path)
    try:
        generated = auth_module.SECRET_KEY
        assert len(generated) >= 32
        assert secret_file.exists()
        assert secret_file.read_text(encoding='utf-8') == generated
    finally:
        _cleanup_auth_module()

    auth_module_again, _ = _import_auth(monkeypatch, tmp_path, preserve_existing=True)
    try:
        assert auth_module_again.SECRET_KEY == generated
    finally:
        _cleanup_auth_module()


def test_password_hash_round_trip_handles_long_passwords():
    from app import auth

    long_password = 's' * 100
    hashed = auth.get_password_hash(long_password)

    assert hashed.startswith(auth.BCRYPT_SHA256_PREFIX)
    assert auth.verify_password(long_password, hashed)
    assert not auth.verify_password(long_password[:72], hashed)


def test_verify_password_accepts_legacy_bcrypt_hash():
    from app import auth

    password = 'legacy-pass'
    legacy_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    assert auth.verify_password(password, legacy_hash)


def test_authenticate_user_upgrades_legacy_hash(monkeypatch: pytest.MonkeyPatch):
    from app import auth
    from unittest.mock import MagicMock

    password = 'legacy-pass'
    legacy_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = SimpleNamespace(
        email='user@example.com',
        hashed_password=legacy_hash,
        last_login=None,
        id=1,
        primary_department=None,
    )

    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value.first.return_value = user
    session.commit.return_value = None
    session.refresh.return_value = None
    session.rollback.return_value = None

    result = auth.authenticate_user(session, user.email, password)

    assert result is user
    assert user.hashed_password.startswith(auth.BCRYPT_SHA256_PREFIX)
    assert session.commit.called

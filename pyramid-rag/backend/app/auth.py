
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)

BCRYPT_SHA256_PREFIX = 'bcrypt_sha256$'
SECRET_KEY_ENV = 'SECRET_KEY'
SECRET_KEY_FILE_ENV = 'SECRET_KEY_FILE'
DEFAULT_SECRET_KEY_PATH = Path('data') / 'secret.key'


def _load_secret_key() -> str:
    """Load the JWT secret key without falling back to a predictable default."""
    env_value = os.getenv(SECRET_KEY_ENV)
    if env_value and len(env_value) >= 32:
        return env_value

    secret_path = Path(os.getenv(SECRET_KEY_FILE_ENV, DEFAULT_SECRET_KEY_PATH))
    try:
        if secret_path.exists():
            stored_value = secret_path.read_text(encoding='utf-8').strip()
            if stored_value:
                logger.warning(
                    'SECRET_KEY environment variable is unset; using value from %s.',
                    secret_path,
                )
                return stored_value
    except OSError as exc:
        logger.warning('Could not read secret key file %s: %s', secret_path, exc)

    generated_value = secrets.token_urlsafe(64)
    try:
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        secret_path.write_text(generated_value, encoding='utf-8')
        logger.warning(
            'Generated a new SECRET_KEY and stored it in %s. Set SECRET_KEY in the '
            'environment to control this value explicitly.',
            secret_path,
        )
    except OSError as exc:
        logger.error('Failed to persist generated SECRET_KEY to %s: %s', secret_path, exc)

    return generated_value


SECRET_KEY = _load_secret_key()
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 259200  # 6 months
REFRESH_TOKEN_EXPIRE_DAYS = 180


def _normalize_hashed_password(hashed_password: Union[str, bytes]) -> str:
    """Ensure hashed passwords are handled as UTF-8 strings."""
    if isinstance(hashed_password, bytes):
        return hashed_password.decode('utf-8')
    return hashed_password


# Direct bcrypt implementation to avoid passlib issues
def verify_password(plain_password: str, hashed_password: Union[str, bytes]) -> bool:
    """Verify a plain password against its stored hash."""
    if plain_password is None or hashed_password is None:
        return False

    password_bytes = plain_password.encode('utf-8')
    stored_hash = _normalize_hashed_password(hashed_password)

    try:
        if stored_hash.startswith(BCRYPT_SHA256_PREFIX):
            digest = hashlib.sha256(password_bytes).digest()
            hash_bytes = stored_hash[len(BCRYPT_SHA256_PREFIX):].encode('utf-8')
            return bcrypt.checkpw(digest, hash_bytes)

        hash_bytes = stored_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as exc:
        logger.error('Password verification error: %s', exc)
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt with a SHA-256 prehash to avoid truncation."""
    if password is None:
        raise ValueError('Password must not be None')

    password_bytes = password.encode('utf-8')
    digest = hashlib.sha256(password_bytes).digest()
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(digest, salt).decode('utf-8')
    return f'{BCRYPT_SHA256_PREFIX}{hashed}'


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire, 'type': 'access'})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({'exp': expire, 'type': 'refresh'})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Union[User, None]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    # Upgrade legacy hashes to the stronger scheme automatically
    hashed_value = _normalize_hashed_password(user.hashed_password)
    if not hashed_value.startswith(BCRYPT_SHA256_PREFIX):
        try:
            user.hashed_password = get_password_hash(password)
            db.commit()
            db.refresh(user)
        except Exception as exc:
            logger.warning('Could not upgrade password hash for user %s: %s', email, exc)
            db.rollback()

    user.last_login = datetime.utcnow()
    db.commit()

    return user


def get_current_user(db: Session, token: str) -> Union[User, None]:
    """Get current user from JWT token."""
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get('type') != 'access':
        return None

    user_id = payload.get('sub')
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


def create_user(
    db: Session,
    email: str,
    password: str,
    username: str,
    full_name: str,
    department: str,
    is_superuser: bool = False,
) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        primary_department=department,
        is_superuser=is_superuser,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

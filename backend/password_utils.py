# password_utils.py
import hashlib

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(plain: str) -> str:
    """
    Új felhasználók hash-elése: PBKDF2.
    """
    return generate_password_hash(plain, method="pbkdf2:sha256", salt_length=16)


def verify_password(plain: str, stored: str) -> bool:
    """
    Dual-verify:
      - ha PBKDF2 (pbkdf2: prefix), akkor werkzeug verify
      - ha régi MD5 (32 hosszú hexa, kettőspont nélkül), akkor MD5
    """
    # PBKDF2 / werkzeug formátum
    if stored.startswith("pbkdf2:"):
        return check_password_hash(stored, plain)

    # Legacy MD5 (seed + régi userek)
    if len(stored) == 32 and ":" not in stored:
        return hashlib.md5(plain.encode("utf-8")).hexdigest() == stored

    return False

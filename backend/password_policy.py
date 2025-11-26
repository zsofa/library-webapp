import re
from typing import List, Tuple


def is_strong_password(password: str) -> Tuple[bool, List[str]]:
    """
    Minimal password policy:
      - at least 8 characters
      - contains at least one letter
      - contains at least one digit
    Returns (ok, errors) where errors is a list of violation codes:
      min_length_8
      must_include_letter
      must_include_digit
    """
    errors: List[str] = []
    if not isinstance(password, str) or len(password) < 8:
        errors.append("min_length_8")
    if not re.search(r"[A-Za-z]", password or ""):
        errors.append("must_include_letter")
    if not re.search(r"\d", password or ""):
        errors.append("must_include_digit")
    return (len(errors) == 0, errors)

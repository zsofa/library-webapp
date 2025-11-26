from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class ParseError(Exception):
    """
    Lightweight exception for input parsing errors that should become JSON error responses.
    """

    error_code: str
    message: str
    status: int = 400


def parse_int(
    value: object,
    *,
    field: str,
    error_code: Optional[str] = None,
    message: Optional[str] = None,
) -> int:
    """
    Parse an integer value, raising ParseError on failure.

    Parameters:
      - value: the raw input (string/number)
      - field: logical field name (used for default codes/messages)
      - error_code: optional custom error code (default: f"invalid_{field}" or "invalid_ids")
      - message: optional custom message (default: f"{field} must be an integer.")

    Returns: int
    """
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ParseError(
            error_code=error_code or f"invalid_{field}",
            message=message or f"{field} must be an integer.",
            status=400,
        )


def parse_date(
    value: object,
    *,
    field: str,
    fmt: str = "%Y-%m-%d",
    error_code: Optional[str] = None,
    message: Optional[str] = None,
) -> date:
    """
    Parse a date from a string with the given format, raising ParseError on failure.

    Parameters:
      - value: the raw input (string)
      - field: logical field name (used for default codes/messages)
      - fmt: datetime format (default: YYYY-MM-DD)
      - error_code: optional custom error code (default: f"invalid_{field}")
      - message: optional custom message (default: f"{field} must be in {fmt} format.")

    Returns: datetime.date
    """
    try:
        text = str(value).strip()
        return datetime.strptime(text, fmt).date()
    except Exception:
        raise ParseError(
            error_code=error_code or f"invalid_{field}",
            message=message or f"{field} must be in {fmt} format.",
            status=400,
        )


def require_fields(data: dict, fields: list[str]) -> None:
    """
    Ellenőrzi, hogy a megadott mezők nem üresek a data dict-ben.
    Ha hiányzik valami, ParseError-t dob "missing_fields" kóddal.
    """
    missing = [f for f in fields if not data.get(f)]
    if missing:
        raise ParseError(
            error_code="missing_fields",
            message=f"Missing required fields: {', '.join(missing)}.",
            status=400,
        )

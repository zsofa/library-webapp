"""
Config values used across the backend.

Most of these are simple defaults. If an env var is present we use that instead.
"""

import os

# Default loan length in days
DEFAULT_LOAN_DAYS: int = int(os.getenv("DEFAULT_LOAN_DAYS", "14"))

# How long a reservation is valid in days
RESERVATION_EXPIRY_DAYS: int = int(os.getenv("RESERVATION_EXPIRY_DAYS", "7"))

# Default library and role for new users created via /register
DEFAULT_LIBRARY_ID: int = int(os.getenv("DEFAULT_LIBRARY_ID", "1"))
DEFAULT_MEMBER_ROLE_ID: int = int(os.getenv("DEFAULT_MEMBER_ROLE_ID", "2"))

# Basic brute-force protection for /login
LOGIN_RATE_LIMIT_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", 5))
LOGIN_RATE_LIMIT_WINDOW_S = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_S", 900))  # 15 min

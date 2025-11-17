"""
Input validation functions for restaurant booking system.

Validates user inputs for safety and correctness.
"""

import re
from datetime import datetime
from typing import Optional


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.

    Accepts:
    - +91-XXXXXXXXXX
    - +91XXXXXXXXXX
    - XXXXXXXXXX

    Args:
        phone: Phone number string

    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False

    # Remove spaces and dashes for validation
    cleaned = phone.replace(" ", "").replace("-", "")

    # Check if starts with +91
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]

    # Should be 10 digits
    if not cleaned.isdigit():
        return False

    if len(cleaned) != 10:
        return False

    # First digit should be 6-9 (Indian mobile numbers)
    if cleaned[0] not in "6789":
        return False

    return True


def validate_date(date_str: str) -> bool:
    """
    Validate date string and check if it's today or future.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        True if valid and not in past, False otherwise
    """
    if not date_str:
        return False

    try:
        # Parse date
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Check if today or future
        today = datetime.now().date()

        return date >= today

    except ValueError:
        return False


def validate_time_slot(time_str: str) -> bool:
    """
    Validate time slot (must be in 30-minute intervals).

    Accepts: HH:00 or HH:30 (24-hour format)

    Args:
        time_str: Time in HH:MM format

    Returns:
        True if valid 30-minute slot, False otherwise
    """
    if not time_str:
        return False

    try:
        # Parse time
        time_obj = datetime.strptime(time_str, "%H:%M").time()

        # Check if minutes are 00 or 30
        if time_obj.minute not in [0, 30]:
            return False

        return True

    except ValueError:
        return False


def validate_party_size(size: int) -> bool:
    """
    Validate party size.

    Args:
        size: Number of people

    Returns:
        True if valid (1-20), False otherwise
    """
    return 1 <= size <= 20


def validate_rating(rating: int) -> bool:
    """
    Validate rating value.

    Args:
        rating: Rating value

    Returns:
        True if valid (1-5), False otherwise
    """
    return 1 <= rating <= 5


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address

    Returns:
        True if valid format, False otherwise
    """
    if not email:
        return False

    # Simple email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    return bool(re.match(pattern, email))


def sanitize_string(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input string.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not text:
        return ""

    # Strip whitespace
    text = text.strip()

    # Limit length
    text = text[:max_length]

    return text

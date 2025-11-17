"""
Test suite for input validation functions.
"""

import pytest
from datetime import datetime, timedelta
from utils.validators import (
    validate_phone_number,
    validate_date,
    validate_time_slot,
    validate_party_size,
    validate_rating
)


class TestPhoneValidation:
    """Test phone number validation."""

    def test_validate_phone_valid_formats(self):
        """Test valid phone number formats."""
        valid_numbers = [
            "+91-9876543210",
            "+919876543210",
            "9876543210",
            "+91 9876543210"
        ]

        for number in valid_numbers:
            assert validate_phone_number(number) is True

    def test_validate_phone_invalid(self):
        """Test invalid phone numbers."""
        invalid_numbers = [
            "123",  # Too short
            "abcd1234567890",  # Contains letters
            "+91-12345",  # Too short
            ""  # Empty
        ]

        for number in invalid_numbers:
            assert validate_phone_number(number) is False


class TestDateValidation:
    """Test date validation."""

    def test_validate_date_future(self):
        """Test that future dates are valid."""
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        assert validate_date(future_date) is True

    def test_validate_date_today(self):
        """Test that today is valid."""
        today = datetime.now().strftime("%Y-%m-%d")

        assert validate_date(today) is True

    def test_validate_date_past(self):
        """Test that past dates are invalid."""
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        assert validate_date(past_date) is False

    def test_validate_date_invalid_format(self):
        """Test invalid date formats."""
        invalid_dates = [
            "2025/10/29",  # Wrong separator
            "29-10-2025",  # Wrong order
            "not-a-date",
            "2025-13-01",  # Invalid month
            ""
        ]

        for date in invalid_dates:
            assert validate_date(date) is False


class TestTimeSlotValidation:
    """Test time slot validation."""

    def test_validate_time_slot_valid_30min(self):
        """Test valid 30-minute interval slots."""
        valid_times = [
            "11:00", "11:30", "12:00", "12:30",
            "18:00", "18:30", "20:00", "20:30"
        ]

        for time in valid_times:
            assert validate_time_slot(time) is True

    def test_validate_time_slot_invalid(self):
        """Test invalid time slots."""
        invalid_times = [
            "11:15",  # Not 30-min interval
            "12:45",  # Not 30-min interval
            "25:00",  # Invalid hour
            "12:60",  # Invalid minute
            "not-a-time",
            ""
        ]

        for time in invalid_times:
            assert validate_time_slot(time) is False


class TestPartySizeValidation:
    """Test party size validation."""

    def test_validate_party_size_valid(self):
        """Test valid party sizes."""
        valid_sizes = [1, 2, 4, 6, 8, 10]

        for size in valid_sizes:
            assert validate_party_size(size) is True

    def test_validate_party_size_invalid(self):
        """Test invalid party sizes."""
        invalid_sizes = [0, -1, 21, 100]  # Max typically 20

        for size in invalid_sizes:
            assert validate_party_size(size) is False


class TestRatingValidation:
    """Test rating validation."""

    def test_validate_rating_valid(self):
        """Test valid ratings."""
        valid_ratings = [1, 2, 3, 4, 5]

        for rating in valid_ratings:
            assert validate_rating(rating) is True

    def test_validate_rating_invalid(self):
        """Test invalid ratings."""
        invalid_ratings = [0, -1, 6, 10]

        for rating in invalid_ratings:
            assert validate_rating(rating) is False

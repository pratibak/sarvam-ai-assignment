"""
Pytest configuration and fixtures for restaurant booking system tests.

Provides reusable test fixtures for database testing.
"""

import pytest
import sqlite3
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def test_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    db_path = tmp_path / "test_restaurants.db"
    yield str(db_path)
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def db_connection(test_db_path):
    """Provide a database connection for testing."""
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    yield conn
    conn.close()


@pytest.fixture
def sample_customer():
    """Provide sample customer data for testing."""
    return {
        "name": "Priya Narayanan",
        "phone": "+91-9840012345",
        "email": "priya@goodfoods.co"
    }


@pytest.fixture
def sample_restaurant():
    """Provide sample restaurant data for testing."""
    return {
        "name": "GoodFoods Italian Piazza",
        "cuisine": "Handmade Italian",
        "latitude": 13.0418,
        "longitude": 80.2337,
        "address": "123 Cathedral Road, Chennai",
        "city": "Chennai",
        "total_capacity": 80,
        "available_tables": 12,
        "price_range": "₹₹₹",
        "rating": 4.6,
        "opening_time": "12:00",
        "closing_time": "23:30",
        "has_parking": 1,
        "has_outdoor_seating": 1
    }


@pytest.fixture
def sample_reservation():
    """Provide sample reservation data for testing."""
    return {
        "customer_id": 1,
        "restaurant_id": 1,
        "reservation_date": "2025-10-30",
        "reservation_time": "20:00",
        "party_size": 2,
        "special_requests": "Window seat please"
    }

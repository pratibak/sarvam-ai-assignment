"""
Test suite for geospatial utility functions.

Tests haversine distance calculations and filtering.
"""

import pytest
from utils.geo_utils import (
    calculate_distance,
    filter_by_distance,
    get_nearest_restaurants
)


class TestHaversineDistance:
    """Test haversine distance calculations."""

    def test_calculate_distance_same_point(self):
        """Test distance between same point is 0."""
        lat, lon = 13.0418, 80.2337  # Chennai - T. Nagar anchor

        distance = calculate_distance(lat, lon, lat, lon)

        assert distance == 0.0

    def test_calculate_distance_known_locations(self):
        """Test distance between known locations."""
        # T. Nagar to Besant Nagar (approximately 5-6 km)
        t_nagar = (13.0418, 80.2337)
        besant_nagar = (13.0008, 80.2668)

        distance = calculate_distance(
            t_nagar[0], t_nagar[1],
            besant_nagar[0], besant_nagar[1]
        )

        # Should be around 5-6 km
        assert 5.0 <= distance <= 7.0

    def test_calculate_distance_returns_positive(self):
        """Test that distance is always positive."""
        distance = calculate_distance(12.0, 77.0, 13.0, 78.0)

        assert distance > 0


class TestFilterByDistance:
    """Test filtering restaurants by distance."""

    def test_filter_by_distance_all_within(self):
        """Test when all restaurants are within range."""
        user_location = (13.0418, 80.2337)  # T. Nagar

        restaurants = [
            {"id": 1, "name": "Rest1", "latitude": 13.0418, "longitude": 80.2337},  # 0 km
            {"id": 2, "name": "Rest2", "latitude": 13.0450, "longitude": 80.2370},  # ~0.5 km
        ]

        filtered = filter_by_distance(
            restaurants,
            user_location[0],
            user_location[1],
            max_distance_km=5.0
        )

        assert len(filtered) == 2
        # Should have distance field
        assert "distance_km" in filtered[0]

    def test_filter_by_distance_some_outside(self):
        """Test filtering when some restaurants are outside range."""
        user_location = (13.0418, 80.2337)

        restaurants = [
            {"id": 1, "name": "Near", "latitude": 13.0418, "longitude": 80.2337},  # 0 km
            {"id": 2, "name": "Far", "latitude": 13.2618, "longitude": 80.4537},  # ~30 km
        ]

        filtered = filter_by_distance(
            restaurants,
            user_location[0],
            user_location[1],
            max_distance_km=5.0
        )

        assert len(filtered) == 1
        assert filtered[0]["name"] == "Near"

    def test_filter_by_distance_sorted(self):
        """Test that results are sorted by distance."""
        user_location = (13.0418, 80.2337)

        restaurants = [
            {"id": 1, "name": "Medium", "latitude": 13.02, "longitude": 80.24},
            {"id": 2, "name": "Nearest", "latitude": 13.0418, "longitude": 80.2337},
            {"id": 3, "name": "Far", "latitude": 12.98, "longitude": 80.28},
        ]

        filtered = filter_by_distance(
            restaurants,
            user_location[0],
            user_location[1],
            max_distance_km=10.0
        )

        # Should be sorted by distance
        assert filtered[0]["name"] == "Nearest"
        assert filtered[0]["distance_km"] < filtered[1]["distance_km"]


class TestGetNearestRestaurants:
    """Test getting nearest N restaurants."""

    def test_get_nearest_restaurants_limit(self):
        """Test limiting number of results."""
        user_location = (13.0418, 80.2337)

        restaurants = [
            {"id": i, "name": f"Rest{i}", "latitude": 13.04 + i*0.008, "longitude": 80.23 + i*0.008}
            for i in range(10)
        ]

        nearest = get_nearest_restaurants(
            restaurants,
            user_location[0],
            user_location[1],
            limit=3
        )

        assert len(nearest) == 3

    def test_get_nearest_restaurants_sorted(self):
        """Test that results are sorted by distance."""
        user_location = (13.0418, 80.2337)

        restaurants = [
            {"id": 1, "name": "Rest1", "latitude": 13.05, "longitude": 80.24},
            {"id": 2, "name": "Rest2", "latitude": 13.0418, "longitude": 80.2337},  # Nearest
            {"id": 3, "name": "Rest3", "latitude": 13.00, "longitude": 80.20},
        ]

        nearest = get_nearest_restaurants(
            restaurants,
            user_location[0],
            user_location[1],
            limit=5
        )

        # First should be nearest (id=2)
        assert nearest[0]["id"] == 2
        assert nearest[0]["distance_km"] == 0.0

"""
Geospatial utility functions for restaurant booking system.

Provides distance calculations and filtering based on location.
"""

from typing import List, Dict, Any, Tuple
from geopy.distance import geodesic


def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    point1 = (lat1, lon1)
    point2 = (lat2, lon2)

    distance = geodesic(point1, point2).kilometers

    return round(distance, 2)


def filter_by_distance(
    restaurants: List[Dict[str, Any]],
    user_lat: float,
    user_lon: float,
    max_distance_km: float = 5.0
) -> List[Dict[str, Any]]:
    """
    Filter restaurants by maximum distance from user.

    Args:
        restaurants: List of restaurant dicts with latitude/longitude
        user_lat: User's latitude
        user_lon: User's longitude
        max_distance_km: Maximum distance in kilometers

    Returns:
        List of restaurants within range, sorted by distance
    """
    results = []

    for restaurant in restaurants:
        distance = calculate_distance(
            user_lat,
            user_lon,
            restaurant['latitude'],
            restaurant['longitude']
        )

        if distance <= max_distance_km:
            # Add distance to restaurant dict
            restaurant_with_distance = restaurant.copy()
            restaurant_with_distance['distance_km'] = distance
            results.append(restaurant_with_distance)

    # Sort by distance
    results.sort(key=lambda x: x['distance_km'])

    return results


def get_nearest_restaurants(
    restaurants: List[Dict[str, Any]],
    user_lat: float,
    user_lon: float,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get N nearest restaurants to user location.

    Args:
        restaurants: List of restaurant dicts
        user_lat: User's latitude
        user_lon: User's longitude
        limit: Maximum number of results

    Returns:
        List of nearest restaurants with distance, sorted
    """
    # Calculate distance for all
    restaurants_with_distance = []

    for restaurant in restaurants:
        distance = calculate_distance(
            user_lat,
            user_lon,
            restaurant['latitude'],
            restaurant['longitude']
        )

        restaurant_with_distance = restaurant.copy()
        restaurant_with_distance['distance_km'] = distance
        restaurants_with_distance.append(restaurant_with_distance)

    # Sort by distance
    restaurants_with_distance.sort(key=lambda x: x['distance_km'])

    # Return top N
    return restaurants_with_distance[:limit]


def format_distance(distance_km: float) -> str:
    """
    Format distance for display.

    Args:
        distance_km: Distance in kilometers

    Returns:
        Formatted string (e.g., "2.5 km" or "850 m")
    """
    if distance_km < 1.0:
        meters = int(distance_km * 1000)
        return f"{meters} m"
    else:
        return f"{distance_km:.1f} km"

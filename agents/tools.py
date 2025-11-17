"""
Tool implementations and schemas for AI agents.

Each tool has:
1. OpenAI function schema (for LLM)
2. Implementation function (actual logic)
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    get_restaurants,
    get_restaurant_by_id,
    create_reservation,
    cancel_reservation as db_cancel_reservation,
    get_customer_reservations,
    get_active_offers,
    create_feedback,
    get_connection
)
from utils.geo_utils import filter_by_distance
from utils.validators import (
    validate_date,
    validate_time_slot,
    validate_party_size,
    validate_rating
)

# Pricing heuristics and fees
PRICE_BAND_ESTIMATES = {
    "₹": 600,
    "₹₹": 1200,
    "₹₹₹": 1800,
    "₹₹₹₹": 2500
}
RESERVATION_FEE = 50  # ₹50 convenience/holding charge


def annotate_revenue_ops(restaurant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add dynamic yield, sponsorship, and enterprise-fit hints.

    Returns a copy with additional keys:
      - yield_signal: surge | discount | steady
      - yield_hint: short recommendation
      - sponsored_bid: optional pay-per-booking bid (₹)
      - enterprise_fit: bool
      - enterprise_hint: optional text
    """
    result = restaurant.copy()

    capacity = max(result.get("total_capacity", 60), 1)
    available = result.get("available_tables", 0)
    utilisation = 1 - (available / capacity)

    if available <= max(2, int(capacity * 0.1)):
        result["yield_signal"] = "surge"
        result["yield_hint"] = "High demand window – consider premium pricing or two-turn seating."
    elif available >= int(capacity * 0.5):
        result["yield_signal"] = "discount"
        result["yield_hint"] = "Plenty of inventory – trigger lunch bundles or limited-time discounts."
    else:
        result["yield_signal"] = "steady"
        result["yield_hint"] = "Steady flow – standard pricing applies."

    rating = result.get("rating", 0)
    if rating >= 4.7 and available >= 4:
        result["sponsored_bid"] = 80  # ₹ per confirmed reservation
    elif rating >= 4.5:
        result["sponsored_bid"] = 60
    else:
        result["sponsored_bid"] = None

    cuisine = (result.get("cuisine") or "").lower()
    enterprise_fit = (
        result.get("total_capacity", 0) >= 90
        or "dinner" in cuisine
        or "wine" in cuisine
    )
    result["enterprise_fit"] = enterprise_fit
    if enterprise_fit:
        result["enterprise_hint"] = "Suitable for corporate dining or private events."
    else:
        result["enterprise_hint"] = None

    # Estimated spend guidance
    price_key = result.get("price_range", "₹₹")
    estimated_per_person = PRICE_BAND_ESTIMATES.get(price_key, 1200)
    result["estimated_spend_per_person"] = estimated_per_person
    result["estimated_spend_for_two"] = estimated_per_person * 2
    result["estimated_spend_hint"] = (
        f"Typical spend ~₹{estimated_per_person} per guest (₹{estimated_per_person * 2} for two)."
    )

    return result


# ============================================================
# Tool Schemas for OpenAI
# ============================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "find_restaurants_by_area",
            "description": "Search for GoodFoods destinations in a SPECIFIC CHENNAI NEIGHBOURHOOD. Use when the guest cites areas like 'Besant Nagar', 'Alwarpet', 'OMR', 'Anna Nagar', etc. Examples: 'destinations in Besant Nagar', 'Any lounges in Alwarpet?', 'Book at OMR'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area_name": {
                        "type": "string",
                        "description": "Area/location name (e.g., 'Besant Nagar', 'Adyar', 'Anna Nagar', 'Velachery'). System will surface ALL GoodFoods destinations in this neighbourhood."
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "Minimum rating (1.0-5.0). Optional."
                    },
                    "has_parking": {
                        "type": "boolean",
                        "description": "Filter for destinations with parking. Optional."
                    },
                    "has_offers": {
                        "type": "boolean",
                        "description": "Filter for destinations with active offers. Optional."
                    }
                },
                "required": ["area_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_restaurants",
            "description": "Search for GoodFoods destinations by distance from the guest's anchor. Use this when they ask for 'nearby', 'closest', or 'around me' experiences WITHOUT naming an area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_distance_km": {
                        "type": "number",
                        "description": "Maximum distance from user in kilometers. Default 10km."
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "Minimum rating (1.0-5.0). Optional."
                    },
                    "price_range": {
                        "type": "string",
                        "enum": ["₹", "₹₹", "₹₹₹", "₹₹₹₹"],
                        "description": "Price range filter. Optional."
                    },
                    "has_parking": {
                        "type": "boolean",
                        "description": "Filter for destinations with parking. Optional."
                    },
                    "has_offers": {
                        "type": "boolean",
                        "description": "Filter for destinations with active offers. Optional."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "make_reservation",
            "description": "Create a restaurant reservation. Always confirm details with user before calling this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "integer",
                        "description": "ID of the restaurant to book"
                    },
                    "reservation_date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format. CRITICAL: Must be TODAY or a FUTURE date ONLY. NEVER accept past dates. Validate before calling this function."
                    },
                    "reservation_time": {
                        "type": "string",
                        "description": "Time in HH:MM format (24-hour). Must be 30-minute intervals (e.g., 18:00, 18:30, 19:00)."
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of people (1-20)"
                    },
                    "special_requests": {
                        "type": "string",
                        "description": "Any special requests (e.g., 'window seat', 'birthday celebration'). Optional."
                    }
                },
                "required": ["restaurant_id", "reservation_date", "reservation_time", "party_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "Cancel an existing reservation by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "integer",
                        "description": "ID of the reservation to cancel"
                    }
                },
                "required": ["reservation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_bookings",
            "description": "Retrieve customer's reservations",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["confirmed", "cancelled", "completed", "all"],
                        "description": "Filter by status. Default 'confirmed' for upcoming bookings."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_offers",
            "description": "Get current offers and deals for a specific restaurant",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "integer",
                        "description": "ID of the restaurant"
                    }
                },
                "required": ["restaurant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_feedback",
            "description": "Submit customer feedback and rating for a restaurant",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "integer",
                        "description": "ID of the restaurant"
                    },
                    "rating": {
                        "type": "integer",
                        "description": "Rating from 1-5 stars"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Feedback comment. Optional."
                    }
                },
                "required": ["restaurant_id", "rating"]
            }
        }
    }
]


# ============================================================
# Tool Implementations
# ============================================================

def find_restaurants(
    db_path: str,
    user_lat: float,
    user_lon: float,
    location_name: str = None,
    cuisine: str = None,
    max_distance_km: float = 10.0,
    min_rating: float = None,
    price_range: str = None,
    has_parking: bool = None,
    has_offers: bool = None
) -> Dict[str, Any]:
    """
    Find restaurants based on criteria.

    Args:
        location_name: Area/location name to search (e.g., "Besant Nagar")

    Returns:
        Dict with status, message, and results
    """
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT restaurant_id, offer_title
            FROM daily_offers
            WHERE is_active = 1
              AND valid_from <= ?
              AND valid_until >= ?
        """, (today, today))
        offer_rows = cursor.fetchall()
        conn.close()

        offers_map: Dict[int, List[str]] = {}
        for restaurant_id, title in offer_rows:
            offers_map.setdefault(restaurant_id, []).append(title)

        # Get restaurants from database with filters
        base_restaurants = get_restaurants(
            db_path,
            cuisine=cuisine,
            min_rating=min_rating,
            price_range=price_range
        )

        for r in base_restaurants:
            offer_titles = offers_map.get(r["id"])
            r["has_active_offers"] = bool(offer_titles)
            r["offer_preview"] = offer_titles[0] if offer_titles else None

        restaurants = base_restaurants

        if not restaurants:
            return {
                "status": "success",
                "message": f"No {cuisine or ''} destinations found. Try expanding your search.",
                "results": []
            }

        # Filter by location_name if provided (area-based search)
        if location_name:
            location_name_lower = location_name.lower()
            restaurants = [r for r in restaurants if location_name_lower in r['name'].lower()]

            if len(restaurants) < 3:
                from utils.geo_utils import calculate_distance
                existing_ids = {r["id"] for r in restaurants}
                fallback_candidates = []
                for candidate in base_restaurants:
                    if candidate["id"] in existing_ids:
                        continue
                    distance = calculate_distance(user_lat, user_lon, candidate["latitude"], candidate["longitude"])
                    candidate_copy = candidate.copy()
                    candidate_copy["distance_km"] = round(distance, 2)
                    candidate_copy["fallback_reason"] = f"Nearby alternative (~{distance:.1f} km)"
                    fallback_candidates.append((distance, candidate_copy))

                fallback_candidates.sort(key=lambda x: x[0])
                needed = 3 - len(restaurants)
                for _, candidate in fallback_candidates[:needed]:
                    restaurants.append(candidate)

            if not restaurants:
                return {
                    "status": "success",
                    "message": f"No GoodFoods destinations found in {location_name}. Shall we look at adjacent neighbourhoods?",
                    "results": []
                }

        # Filter by offers if requested
        if has_offers:
            restaurants = [r for r in restaurants if r.get("has_active_offers")]
            if not restaurants:
                return {
                    "status": "success",
                    "message": f"No {cuisine or ''} destinations with active offers found. Try expanding your search.",
                    "results": []
                }

        # Filter by parking if requested
        if has_parking:
            restaurants = [r for r in restaurants if r.get('has_parking') == 1]
            if not restaurants:
                return {
                    "status": "success",
                    "message": f"No {cuisine or ''} destinations with parking found. Try expanding your search.",
                    "results": []
                }

        # Filter by distance
        # BUT: If searching by location_name, don't filter by distance - show ALL outlets in that area
        if location_name:
            # Just add distance without filtering
            from utils.geo_utils import calculate_distance
            restaurants_with_distance = []
            for r in restaurants:
                distance_km = r.get("distance_km")
                if distance_km is None:
                    distance_km = calculate_distance(user_lat, user_lon, r['latitude'], r['longitude'])
                r_copy = r.copy()
                r_copy['distance_km'] = round(distance_km, 2)
                restaurants_with_distance.append(annotate_revenue_ops(r_copy))

            # Sort by distance for convenience
            restaurants_with_distance.sort(key=lambda x: x['distance_km'])
        else:
            # For proximity search, filter by max_distance_km
            restaurants_with_distance = filter_by_distance(
                restaurants,
                user_lat,
                user_lon,
                max_distance_km
            )
            restaurants_with_distance = [annotate_revenue_ops(r) for r in restaurants_with_distance]

            if not restaurants_with_distance:
                return {
                    "status": "success",
                    "message": f"No restaurants found within {max_distance_km}km. Try increasing the distance.",
                    "results": [],
                    "suggestion": f"Expand search to {max_distance_km + 5}km"
                }

        # When searching by location_name, show ALL outlets in that area
        # Otherwise, show top 5 to avoid overwhelming users
        result_limit = len(restaurants_with_distance) if location_name else 5

        return {
            "status": "success",
            "message": f"Found {len(restaurants_with_distance)} restaurants",
            "results": restaurants_with_distance[:result_limit],
            "count": len(restaurants_with_distance)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error searching restaurants: {str(e)}",
            "results": []
        }


def make_reservation(
    db_path: str,
    customer_id: int,
    restaurant_id: int,
    reservation_date: str,
    reservation_time: str,
    party_size: int,
    special_requests: str = None
) -> Dict[str, Any]:
    """
    Create a new reservation.

    Returns:
        Dict with status, message, and reservation details
    """
    try:
        # Validate inputs
        if not validate_date(reservation_date):
            return {
                "status": "error",
                "message": "Invalid date. Please provide a date today or in the future (YYYY-MM-DD format)."
            }

        if not validate_time_slot(reservation_time):
            return {
                "status": "error",
                "message": "Invalid time slot. Please use 30-minute intervals (e.g., 18:00, 18:30, 19:00)."
            }

        if not validate_party_size(party_size):
            return {
                "status": "error",
                "message": "Invalid party size. Please specify 1-20 people."
            }

        # Check if restaurant exists and has tables
        restaurant = get_restaurant_by_id(db_path, restaurant_id)

        if not restaurant:
            return {
                "status": "error",
                "message": f"Restaurant ID {restaurant_id} not found."
            }

        if restaurant['available_tables'] <= 0:
            return {
                "status": "error",
                "message": f"{restaurant['name']} is fully booked. Please try a different time or restaurant."
            }

        # Create reservation
        reservation_data = {
            "customer_id": customer_id,
            "restaurant_id": restaurant_id,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "party_size": party_size,
            "special_requests": special_requests
        }

        reservation_id = create_reservation(db_path, reservation_data)

        # Get full reservation details
        reservation_data['id'] = reservation_id
        reservation_data['status'] = 'confirmed'

        # Re-fetch restaurant to get UPDATED available_tables count
        restaurant = get_restaurant_by_id(db_path, restaurant_id)

        # Check for offers
        offers = get_active_offers(db_path, restaurant_id)
        offer_message = ""
        if offers:
            offer = offers[0]
            offer_message = f"\n\n💰 **Special Offer Available:** {offer['offer_title']} - {offer['offer_description']}"

        price_key = restaurant.get("price_range", "₹₹")
        estimated_per_person = PRICE_BAND_ESTIMATES.get(price_key, 1200)
        estimated_subtotal = estimated_per_person * party_size
        total_with_fee = estimated_subtotal + RESERVATION_FEE

        return {
            "status": "success",
            "message": (
                f"Reservation confirmed at {restaurant['name']}! "
                f"A ₹{RESERVATION_FEE} reservation fee has been added.{offer_message}"
            ),
            "reservation": reservation_data,
            "restaurant": restaurant,
            "has_offers": len(offers) > 0,
            "reservation_fee": RESERVATION_FEE,
            "estimated_spend_per_person": estimated_per_person,
            "estimated_subtotal": estimated_subtotal,
            "estimated_total_with_fee": total_with_fee
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating reservation: {str(e)}"
        }


def cancel_reservation(
    db_path: str,
    customer_id: int,
    reservation_id: int
) -> Dict[str, Any]:
    """
    Cancel an existing reservation.

    Returns:
        Dict with status and message
    """
    try:
        # Verify reservation belongs to customer
        reservations = get_customer_reservations(db_path, customer_id)
        reservation = next((r for r in reservations if r['id'] == reservation_id), None)

        if not reservation:
            return {
                "status": "error",
                "message": f"Reservation #{reservation_id} not found or doesn't belong to you."
            }

        if reservation['status'] == 'cancelled':
            return {
                "status": "error",
                "message": f"Reservation #{reservation_id} is already cancelled."
            }

        # Cancel reservation
        success = db_cancel_reservation(db_path, reservation_id)

        if success:
            return {
                "status": "success",
                "message": f"Reservation #{reservation_id} at {reservation['restaurant_name']} has been cancelled.",
                "reservation": reservation
            }
        else:
            return {
                "status": "error",
                "message": "Failed to cancel reservation."
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error cancelling reservation: {str(e)}"
        }


def get_my_bookings(
    db_path: str,
    customer_id: int,
    status: str = "confirmed"
) -> Dict[str, Any]:
    """
    Get customer's reservations.

    Returns:
        Dict with status, message, and bookings
    """
    try:
        # Get reservations
        if status == "all":
            reservations = get_customer_reservations(db_path, customer_id)
        else:
            reservations = get_customer_reservations(db_path, customer_id, status)

        if not reservations:
            return {
                "status": "success",
                "message": f"No {status} reservations found.",
                "bookings": []
            }

        return {
            "status": "success",
            "message": f"Found {len(reservations)} reservation(s)",
            "bookings": reservations,
            "count": len(reservations)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving bookings: {str(e)}",
            "bookings": []
        }


def get_daily_offers_func(
    db_path: str,
    restaurant_id: int
) -> Dict[str, Any]:
    """
    Get active offers for a restaurant.

    Returns:
        Dict with status, message, and offers
    """
    try:
        offers = get_active_offers(db_path, restaurant_id)

        if not offers:
            restaurant = get_restaurant_by_id(db_path, restaurant_id)
            restaurant_name = restaurant['name'] if restaurant else f"Restaurant #{restaurant_id}"

            return {
                "status": "success",
                "message": f"No active offers at {restaurant_name} right now.",
                "offers": []
            }

        return {
            "status": "success",
            "message": f"Found {len(offers)} active offer(s)",
            "offers": offers,
            "count": len(offers)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving offers: {str(e)}",
            "offers": []
        }


def submit_feedback_func(
    db_path: str,
    customer_id: int,
    restaurant_id: int,
    rating: int,
    comment: str = None
) -> Dict[str, Any]:
    """
    Submit customer feedback.

    Returns:
        Dict with status and message
    """
    try:
        # Validate rating
        if not validate_rating(rating):
            return {
                "status": "error",
                "message": "Invalid rating. Please provide a rating from 1-5 stars."
            }

        # Create feedback
        feedback_data = {
            "customer_id": customer_id,
            "restaurant_id": restaurant_id,
            "rating": rating,
            "comment": comment
        }

        feedback_id = create_feedback(db_path, feedback_data)

        restaurant = get_restaurant_by_id(db_path, restaurant_id)
        restaurant_name = restaurant['name'] if restaurant else f"Restaurant #{restaurant_id}"

        return {
            "status": "success",
            "message": f"Thank you for your {rating}-star feedback on {restaurant_name}! Your review helps others discover great dining experiences.",
            "feedback_id": feedback_id
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error submitting feedback: {str(e)}"
        }


# ============================================================
# Tool Execution Router
# ============================================================

def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    db_path: str,
    customer_id: int,
    user_lat: float,
    user_lon: float
) -> Dict[str, Any]:
    """
    Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        db_path: Database path
        customer_id: Current customer ID
        user_lat: User latitude
        user_lon: User longitude

    Returns:
        Tool execution result
    """
    if tool_name == "find_restaurants_by_area":
        # Dedicated tool for area-based search
        return find_restaurants(
            db_path,
            user_lat,
            user_lon,
            location_name=arguments.get("area_name"),  # REQUIRED parameter
            min_rating=arguments.get("min_rating"),
            has_parking=arguments.get("has_parking"),
            has_offers=arguments.get("has_offers")
        )

    elif tool_name == "find_restaurants":
        return find_restaurants(
            db_path,
            user_lat,
            user_lon,
            max_distance_km=arguments.get("max_distance_km", 10.0),
            min_rating=arguments.get("min_rating"),
            price_range=arguments.get("price_range"),
            has_parking=arguments.get("has_parking"),
            has_offers=arguments.get("has_offers")
        )

    elif tool_name == "make_reservation":
        return make_reservation(
            db_path,
            customer_id,
            arguments["restaurant_id"],
            arguments["reservation_date"],
            arguments["reservation_time"],
            arguments["party_size"],
            arguments.get("special_requests")
        )

    elif tool_name == "cancel_reservation":
        return cancel_reservation(
            db_path,
            customer_id,
            arguments["reservation_id"]
        )

    elif tool_name == "get_my_bookings":
        return get_my_bookings(
            db_path,
            customer_id,
            arguments.get("status", "confirmed")
        )

    elif tool_name == "get_daily_offers":
        return get_daily_offers_func(
            db_path,
            arguments["restaurant_id"]
        )

    elif tool_name == "submit_feedback":
        return submit_feedback_func(
            db_path,
            customer_id,
            arguments["restaurant_id"],
            arguments["rating"],
            arguments.get("comment")
        )

    else:
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}"
        }

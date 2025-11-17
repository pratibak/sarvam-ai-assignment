"""
Seed the GoodFoods Chennai collection with vibrant, diverse data.

Creates:
- 75 GoodFoods destinations across Chennai covering cafés, breakfast clubs,
  handmade Italian kitchens, fine-dining dinner studios, wine lounges, and dessert ateliers.
- 15 seed guests representing the local community.
- 25 experiential reservations from sunrise tiffin to late-night tastings.
- 20 themed offers tuned to Chennai's culinary culture.
"""

import random
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    initialize_database,
    create_customer,
    create_restaurant,
    create_reservation,
    create_daily_offer
)


# ============================================================
# GoodFoods Chennai Collection Data Model
# ============================================================

CHAIN_NAME = "GoodFoods"
CITY_NAME = "Chennai"

# Core neighbourhoods we want to feature across the city
CHENNAI_DISTRICTS = [
    "T. Nagar", "Nungambakkam", "Anna Nagar", "Velachery",
    "Adyar", "Besant Nagar", "Mylapore", "Alwarpet",
    "OMR", "ECR", "Guindy", "Kilpauk",
    "Tambaram", "Porur", "Pallavaram"
]

# Additional descriptors to create unique destination names
LOCATION_DESCRIPTORS = [
    "", " Social House", " Courtyard", " Pavilion", " Promenade",
    " Atelier", " Terrace", " Harbour", " Conservatory"
]

# Service themes to guarantee coverage across all requested concepts
SERVICE_THEMES = [
    {
        "name_suffix": "Café District",
        "cuisine": "Artisan Café & Brunch",
        "price_range": "₹₹",
        "opening_time": "07:00",
        "closing_time": "22:30",
        "parking_probability": 0.35,
        "outdoor_probability": 0.65
    },
    {
        "name_suffix": "Sunrise Tiffin Club",
        "cuisine": "South Indian Breakfast",
        "price_range": "₹",
        "opening_time": "06:00",
        "closing_time": "15:00",
        "parking_probability": 0.25,
        "outdoor_probability": 0.20
    },
    {
        "name_suffix": "Italian Piazza",
        "cuisine": "Handmade Italian",
        "price_range": "₹₹₹",
        "opening_time": "12:00",
        "closing_time": "23:30",
        "parking_probability": 0.55,
        "outdoor_probability": 0.40
    },
    {
        "name_suffix": "Heritage Dinner Studio",
        "cuisine": "Coastal & Chettinad Dinner",
        "price_range": "₹₹₹",
        "opening_time": "13:00",
        "closing_time": "23:45",
        "parking_probability": 0.60,
        "outdoor_probability": 0.25
    },
    {
        "name_suffix": "Madras Cellar",
        "cuisine": "Wine & Dine Lounge",
        "price_range": "₹₹₹₹",
        "opening_time": "17:00",
        "closing_time": "01:00",
        "parking_probability": 0.80,
        "outdoor_probability": 0.35
    },
    {
        "name_suffix": "Sugar Works Lab",
        "cuisine": "Dessert Tasting Room",
        "price_range": "₹₹",
        "opening_time": "11:00",
        "closing_time": "23:00",
        "parking_probability": 0.30,
        "outdoor_probability": 0.50
    }
]

# Chennai coordinates range
LAT_MIN, LAT_MAX = 12.90, 13.15
LON_MIN, LON_MAX = 80.10, 80.32

CHENNAI_AREAS = [
    ("T. Nagar", 13.0418, 80.2337),
    ("Nungambakkam", 13.0615, 80.2425),
    ("Anna Nagar", 13.0879, 80.2128),
    ("Velachery", 12.9801, 80.2209),
    ("Adyar", 13.0067, 80.2570),
    ("Besant Nagar", 13.0008, 80.2668),
    ("Mylapore", 13.0300, 80.2680),
    ("Alwarpet", 13.0310, 80.2500),
    ("OMR", 12.9279, 80.2340),
    ("ECR", 12.9455, 80.2487),
    ("Guindy", 13.0065, 80.2203),
    ("Kilpauk", 13.0790, 80.2470),
    ("Tambaram", 12.9229, 80.1279),
    ("Porur", 13.0492, 80.1764),
    ("Pallavaram", 12.9676, 80.1521)
]

STREET_NAMES = [
    "Cathedral Road", "Mount Road", "Tamarind Lane", "Whites Road",
    "Beach View Drive", "Canal Street", "Temple Street", "Mint Street",
    "Mahabalipuram Road", "Kotturpuram High Road"
]


def generate_restaurants(db_path: str, count: int = 75) -> list:
    """Generate GoodFoods destinations across Chennai."""

    print(f"\n🍽️  Generating {count} GoodFoods destinations...")

    restaurants = []
    used_names = set()

    for i in range(count):
        location = CHENNAI_DISTRICTS[i % len(CHENNAI_DISTRICTS)]
        descriptor = LOCATION_DESCRIPTORS[i // len(CHENNAI_DISTRICTS) % len(LOCATION_DESCRIPTORS)]
        theme = SERVICE_THEMES[i % len(SERVICE_THEMES)]

        name = f"{CHAIN_NAME} {theme['name_suffix']} - {location}{descriptor}"

        # Ensure uniqueness
        counter = 1
        original_name = name
        while name in used_names:
            name = f"{original_name} #{counter}"
            counter += 1
        used_names.add(name)

        # Get coordinates for neighbourhood
        area_data = [a for a in CHENNAI_AREAS if a[0] == location]
        if area_data:
            _, base_lat, base_lon = area_data[0]
        else:
            _, base_lat, base_lon = random.choice(CHENNAI_AREAS)

        # Subtle variance to keep geo spread believable
        lat = max(LAT_MIN, min(base_lat + random.uniform(-0.015, 0.015), LAT_MAX))
        lon = max(LON_MIN, min(base_lon + random.uniform(-0.015, 0.015), LON_MAX))

        street = random.choice(STREET_NAMES)
        address = f"{random.randint(10, 299)} {street}, {location}, {CITY_NAME}"

        # Ensure every restaurant looks available and lively
        total_capacity = random.randint(40, 140)
        available_tables = max(8, min(total_capacity // random.randint(4, 6), total_capacity - 10))

        rating = round(random.uniform(4.1, 4.9), 1)
        has_parking = 1 if random.random() < theme["parking_probability"] else 0
        has_outdoor_seating = 1 if random.random() < theme["outdoor_probability"] else 0

        restaurant_data = {
            "name": name,
            "cuisine": theme["cuisine"],
            "latitude": lat,
            "longitude": lon,
            "address": address,
            "city": CITY_NAME,
            "total_capacity": total_capacity,
            "available_tables": available_tables,
            "price_range": theme["price_range"],
            "rating": rating,
            "opening_time": theme["opening_time"],
            "closing_time": theme["closing_time"],
            "has_parking": has_parking,
            "has_outdoor_seating": has_outdoor_seating
        }

        restaurant_id = create_restaurant(db_path, restaurant_data)
        restaurants.append(restaurant_id)

        if (i + 1) % 10 == 0:
            print(f"   Created {i + 1} destinations...")

    print(f"✅ Created {count} destinations!\n")
    return restaurants


def generate_customers(db_path: str, count: int = 15) -> list:
    """Generate mock guests representing Chennai locals."""

    print(f"👤 Generating {count} guests...")

    first_names = [
        "Sridhar", "Karthik", "Harini", "Aishwarya", "Pradeep", "Divya",
        "Vignesh", "Shruti", "Rahul", "Yamini", "Aravind", "Meenakshi",
        "Sanjay", "Nandhini", "Varun", "Keerthi"
    ]

    last_names = [
        "Iyer", "Narayanan", "Subramaniam", "Sundaram", "Raman", "Bala",
        "Parthiban", "Swaminathan", "Krishnan", "Lakshmanan", "Raghavan", "Balaji"
    ]

    customers = []

    for _ in range(count):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = f"+91-{random.randint(8200000000, 9899999999)}"

        # 70% have email
        email = None
        if random.random() < 0.7:
            first = name.split()[0].lower()
            email = f"{first}{random.randint(1, 99)}@goodfoods.co"

        customer_id = create_customer(db_path, name, phone, email)
        customers.append(customer_id)

    print(f"✅ Created {count} guests!\n")
    return customers


def generate_reservations(
    db_path: str,
    customers: list,
    restaurants: list,
    count: int = 25
) -> list:
    """Generate mock reservations spanning breakfast to late-night lounges."""

    print(f"📅 Generating {count} reservations...")

    reservations = []
    today = datetime.now()

    time_slots = [
        "07:30", "08:00", "09:30", "11:00", "12:30", "13:00",
        "17:30", "18:30", "19:30", "20:00", "21:00", "22:00",
        "23:00"
    ]

    special_requests_options = [
        None, None, None,
        "Need a quiet table for a client meeting",
        "Celebrating a golden jubilee anniversary",
        "Require Jain-friendly menu options",
        "Prefer a sea-facing table",
        "Bringing kids, need booster seat",
        "Wine pairing recommendation please"
    ]

    for _ in range(count):
        customer_id = random.choice(customers)
        restaurant_id = random.choice(restaurants)

        rand = random.random()
        if rand < 0.55:
            date = today + timedelta(days=random.randint(2, 12))
        elif rand < 0.85:
            date = today + timedelta(days=random.randint(0, 1))
        else:
            date = today - timedelta(days=random.randint(1, 5))

        reservation_date = date.strftime("%Y-%m-%d")
        reservation_time = random.choice(time_slots)
        party_size = random.choice([2, 2, 3, 4, 4, 5, 6, 7])
        special_requests = random.choice(special_requests_options)

        reservation_data = {
            "customer_id": customer_id,
            "restaurant_id": restaurant_id,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "party_size": party_size,
            "special_requests": special_requests
        }

        try:
            reservation_id = create_reservation(db_path, reservation_data)
            reservations.append(reservation_id)
        except Exception as e:
            print(f"   Warning: Could not create reservation: {e}")

    print(f"✅ Created {len(reservations)} reservations!\n")
    return reservations


def generate_offers(db_path: str, restaurants: list, count: int = 20) -> list:
    """Generate themed daily offers for different service styles."""

    print(f"💰 Generating {count} offers...")

    offer_templates = [
        ("Filter Coffee Sunrise", "Unlimited degree coffee with any breakfast platter", 25),
        ("Marina Brunch Board", "Brunch board for two with fresh catch specials", 20),
        ("Pasta e Vino Night", "Handmade pasta with complimentary prosecco pairings", 22),
        ("Sangria Sundowner", "Buy two sangrias, get the third on the house", 33),
        ("Chettinad Feast", "Four-course spice trail dinner menu", 18),
        ("Gelato Flights", "Pick any 4 tasting scoops for the price of 3", 25),
        ("Wine Library Access", "Access reserve cellar with curated cheese board", 28),
        ("Early Bird Breakfast", "Flat 30% off on tiffin combos before 9 AM", 30),
        ("Madras High Tea", "Assorted savouries and desserts for evening tea", 24),
        ("Dessert Degustation", "Six-course plated dessert experience", 26)
    ]

    offers = []

    for _ in range(count):
        restaurant_id = random.choice(restaurants)
        title, description, discount = random.choice(offer_templates)

        start_date = datetime.now() - timedelta(days=random.randint(0, 3))
        end_date = start_date + timedelta(days=random.randint(10, 28))

        offer_data = {
            "restaurant_id": restaurant_id,
            "offer_title": title,
            "offer_description": description,
            "discount_percentage": discount,
            "valid_from": start_date.strftime("%Y-%m-%d"),
            "valid_until": end_date.strftime("%Y-%m-%d")
        }

        offer_id = create_daily_offer(db_path, offer_data)
        offers.append(offer_id)

    print(f"✅ Created {count} offers!\n")
    return offers


def main():
    """Main function to seed database."""

    db_path = os.getenv("DATABASE_PATH", "data/restaurants.db")
    Path(db_path).parent.mkdir(exist_ok=True)

    print("=" * 64)
    print("🌱 SEEDING GOODFOODS CHENNAI DATABASE")
    print("=" * 64)

    print("\n📦 Initializing database...")
    initialize_database(db_path)
    print("✅ Database initialized!\n")

    restaurants = generate_restaurants(db_path, count=75)
    customers = generate_customers(db_path, count=15)
    reservations = generate_reservations(db_path, customers, restaurants, count=25)
    offers = generate_offers(db_path, restaurants, count=20)

    print("=" * 64)
    print("✅ GOODFOODS CHENNAI DATA READY!")
    print("=" * 64)
    print(f"\n📊 Summary:")
    print(f"   • Destinations: {len(restaurants)}")
    print(f"   • Guests: {len(customers)}")
    print(f"   • Reservations: {len(reservations)}")
    print(f"   • Offers: {len(offers)}")
    print(f"\n📍 Database location: {db_path}\n")


if __name__ == "__main__":
    random.seed(42)
    main()

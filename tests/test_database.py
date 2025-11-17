"""
Test suite for database layer.

Tests CRUD operations, constraints, and edge cases.
Following TDD approach - tests written before implementation.
"""

import pytest
import sqlite3
from database.db_manager import (
    initialize_database,
    create_customer,
    get_customer_by_phone,
    create_restaurant,
    get_restaurant_by_id,
    get_restaurants,
    create_reservation,
    get_reservation_by_id,
    update_reservation_status,
    get_customer_reservations,
    cancel_reservation,
    create_daily_offer,
    get_active_offers,
    create_feedback
)


class TestDatabaseInitialization:
    """Test database schema creation."""

    def test_initialize_database_creates_tables(self, test_db_path):
        """Test that initialize_database creates all required tables."""
        initialize_database(test_db_path)

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Check if all tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        assert 'customers' in tables
        assert 'restaurants' in tables
        assert 'reservations' in tables
        assert 'daily_offers' in tables
        assert 'feedback' in tables

        conn.close()

    def test_initialize_database_creates_indexes(self, test_db_path):
        """Test that indexes are created for performance."""
        initialize_database(test_db_path)

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]

        assert 'idx_customers_phone' in indexes
        assert 'idx_reservations_customer' in indexes

        conn.close()


class TestCustomerOperations:
    """Test customer CRUD operations."""

    def test_create_customer_success(self, test_db_path, sample_customer):
        """Test creating a new customer."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )

        assert customer_id is not None
        assert customer_id > 0

    def test_create_customer_duplicate_phone(self, test_db_path, sample_customer):
        """Test that duplicate phone numbers are rejected."""
        initialize_database(test_db_path)

        # Create first customer
        create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )

        # Try to create duplicate - should raise error
        with pytest.raises(sqlite3.IntegrityError):
            create_customer(
                test_db_path,
                "Jane Doe",
                sample_customer['phone'],  # Same phone
                "jane@example.com"
            )

    def test_get_customer_by_phone_found(self, test_db_path, sample_customer):
        """Test retrieving customer by phone number."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )

        customer = get_customer_by_phone(test_db_path, sample_customer['phone'])

        assert customer is not None
        assert customer['id'] == customer_id
        assert customer['name'] == sample_customer['name']
        assert customer['phone'] == sample_customer['phone']

    def test_get_customer_by_phone_not_found(self, test_db_path):
        """Test that non-existent customer returns None."""
        initialize_database(test_db_path)

        customer = get_customer_by_phone(test_db_path, "+91-0000000000")

        assert customer is None

    def test_create_customer_without_email(self, test_db_path):
        """Test creating customer without optional email."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            "Jane Doe",
            "+91-9999999999",
            None  # No email
        )

        assert customer_id is not None
        customer = get_customer_by_phone(test_db_path, "+91-9999999999")
        assert customer['email'] is None


class TestRestaurantOperations:
    """Test restaurant CRUD operations."""

    def test_create_restaurant_success(self, test_db_path, sample_restaurant):
        """Test creating a new restaurant."""
        initialize_database(test_db_path)

        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        assert restaurant_id is not None
        assert restaurant_id > 0

    def test_get_restaurant_by_id(self, test_db_path, sample_restaurant):
        """Test retrieving restaurant by ID."""
        initialize_database(test_db_path)

        restaurant_id = create_restaurant(test_db_path, sample_restaurant)
        restaurant = get_restaurant_by_id(test_db_path, restaurant_id)

        assert restaurant is not None
        assert restaurant['id'] == restaurant_id
        assert restaurant['name'] == sample_restaurant['name']
        assert restaurant['cuisine'] == sample_restaurant['cuisine']
        assert restaurant['rating'] == sample_restaurant['rating']

    def test_get_restaurants_all(self, test_db_path, sample_restaurant):
        """Test retrieving all restaurants."""
        initialize_database(test_db_path)

        # Create multiple restaurants
        create_restaurant(test_db_path, sample_restaurant)

        sample_restaurant2 = sample_restaurant.copy()
        sample_restaurant2['name'] = "Dragon Den"
        sample_restaurant2['cuisine'] = "Chinese"
        create_restaurant(test_db_path, sample_restaurant2)

        restaurants = get_restaurants(test_db_path)

        assert len(restaurants) == 2

    def test_get_restaurants_by_cuisine(self, test_db_path, sample_restaurant):
        """Test filtering restaurants by cuisine."""
        initialize_database(test_db_path)

        # Create Italian restaurant
        create_restaurant(test_db_path, sample_restaurant)

        # Create Chinese restaurant
        sample_restaurant2 = sample_restaurant.copy()
        sample_restaurant2['name'] = "Dragon Den"
        sample_restaurant2['cuisine'] = "Chinese"
        create_restaurant(test_db_path, sample_restaurant2)

        italian_restaurants = get_restaurants(
            test_db_path,
            cuisine="Italian"
        )

        assert len(italian_restaurants) == 1
        assert italian_restaurants[0]['cuisine'] == "Italian"


class TestReservationOperations:
    """Test reservation CRUD operations."""

    def test_create_reservation_success(self, test_db_path, sample_customer,
                                       sample_restaurant, sample_reservation):
        """Test creating a new reservation."""
        initialize_database(test_db_path)

        # Setup: Create customer and restaurant
        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        # Create reservation
        sample_reservation['customer_id'] = customer_id
        sample_reservation['restaurant_id'] = restaurant_id

        reservation_id = create_reservation(test_db_path, sample_reservation)

        assert reservation_id is not None
        assert reservation_id > 0

    def test_create_reservation_decrements_available_tables(
        self, test_db_path, sample_customer, sample_restaurant, sample_reservation
    ):
        """Test that creating reservation decrements available tables."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        initial_tables = sample_restaurant['available_tables']

        # Create reservation
        sample_reservation['customer_id'] = customer_id
        sample_reservation['restaurant_id'] = restaurant_id
        create_reservation(test_db_path, sample_reservation)

        # Check that available_tables decreased
        restaurant = get_restaurant_by_id(test_db_path, restaurant_id)
        assert restaurant['available_tables'] == initial_tables - 1

    def test_get_reservation_by_id(self, test_db_path, sample_customer,
                                   sample_restaurant, sample_reservation):
        """Test retrieving reservation by ID."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        sample_reservation['customer_id'] = customer_id
        sample_reservation['restaurant_id'] = restaurant_id
        reservation_id = create_reservation(test_db_path, sample_reservation)

        reservation = get_reservation_by_id(test_db_path, reservation_id)

        assert reservation is not None
        assert reservation['id'] == reservation_id
        assert reservation['customer_id'] == customer_id
        assert reservation['restaurant_id'] == restaurant_id
        assert reservation['status'] == 'confirmed'

    def test_update_reservation_status(self, test_db_path, sample_customer,
                                      sample_restaurant, sample_reservation):
        """Test updating reservation status."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        sample_reservation['customer_id'] = customer_id
        sample_reservation['restaurant_id'] = restaurant_id
        reservation_id = create_reservation(test_db_path, sample_reservation)

        # Update status
        success = update_reservation_status(
            test_db_path,
            reservation_id,
            'completed'
        )

        assert success is True

        reservation = get_reservation_by_id(test_db_path, reservation_id)
        assert reservation['status'] == 'completed'

    def test_cancel_reservation_increments_tables(
        self, test_db_path, sample_customer, sample_restaurant, sample_reservation
    ):
        """Test that cancelling reservation increments available tables."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        sample_reservation['customer_id'] = customer_id
        sample_reservation['restaurant_id'] = restaurant_id
        reservation_id = create_reservation(test_db_path, sample_reservation)

        # Get tables after booking
        restaurant = get_restaurant_by_id(test_db_path, restaurant_id)
        tables_after_booking = restaurant['available_tables']

        # Cancel reservation
        success = cancel_reservation(test_db_path, reservation_id)

        assert success is True

        # Check tables increased
        restaurant = get_restaurant_by_id(test_db_path, restaurant_id)
        assert restaurant['available_tables'] == tables_after_booking + 1

        # Check status updated
        reservation = get_reservation_by_id(test_db_path, reservation_id)
        assert reservation['status'] == 'cancelled'

    def test_get_customer_reservations(self, test_db_path, sample_customer,
                                      sample_restaurant, sample_reservation):
        """Test retrieving all reservations for a customer."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        # Create multiple reservations
        sample_reservation['customer_id'] = customer_id
        sample_reservation['restaurant_id'] = restaurant_id
        create_reservation(test_db_path, sample_reservation)

        sample_reservation2 = sample_reservation.copy()
        sample_reservation2['reservation_date'] = "2025-10-31"
        create_reservation(test_db_path, sample_reservation2)

        reservations = get_customer_reservations(test_db_path, customer_id)

        assert len(reservations) >= 2


class TestDailyOffers:
    """Test daily offers operations."""

    def test_create_daily_offer(self, test_db_path, sample_restaurant):
        """Test creating a daily offer."""
        initialize_database(test_db_path)

        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        offer_data = {
            "restaurant_id": restaurant_id,
            "offer_title": "20% Off Pasta",
            "offer_description": "Get 20% off on all pasta dishes",
            "discount_percentage": 20,
            "valid_from": "2025-10-29",
            "valid_until": "2025-10-31"
        }

        offer_id = create_daily_offer(test_db_path, offer_data)

        assert offer_id is not None
        assert offer_id > 0

    def test_get_active_offers(self, test_db_path, sample_restaurant):
        """Test retrieving active offers for a restaurant."""
        initialize_database(test_db_path)

        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        offer_data = {
            "restaurant_id": restaurant_id,
            "offer_title": "20% Off Pasta",
            "offer_description": "Get 20% off on all pasta dishes",
            "discount_percentage": 20,
            "valid_from": "2025-10-29",
            "valid_until": "2025-12-31"  # Valid for a while
        }

        create_daily_offer(test_db_path, offer_data)

        offers = get_active_offers(test_db_path, restaurant_id)

        assert len(offers) > 0
        assert offers[0]['offer_title'] == "20% Off Pasta"


class TestFeedback:
    """Test feedback operations."""

    def test_create_feedback(self, test_db_path, sample_customer, sample_restaurant):
        """Test creating customer feedback."""
        initialize_database(test_db_path)

        customer_id = create_customer(
            test_db_path,
            sample_customer['name'],
            sample_customer['phone'],
            sample_customer['email']
        )
        restaurant_id = create_restaurant(test_db_path, sample_restaurant)

        feedback_data = {
            "customer_id": customer_id,
            "restaurant_id": restaurant_id,
            "rating": 5,
            "comment": "Amazing pasta! Will visit again."
        }

        feedback_id = create_feedback(test_db_path, feedback_data)

        assert feedback_id is not None
        assert feedback_id > 0

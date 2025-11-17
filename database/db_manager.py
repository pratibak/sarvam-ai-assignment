"""
Database manager for restaurant booking system.

Handles all database operations including CRUD for:
- Customers
- Restaurants
- Reservations
- Daily offers
- Feedback
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Create and return a database connection with timeout and WAL mode.

    Args:
        db_path: Path to SQLite database file

    Returns:
        sqlite3.Connection with row_factory set to Row
    """
    conn = sqlite3.connect(db_path, timeout=10.0)  # 10 second timeout
    conn.row_factory = sqlite3.Row  # Access columns by name

    # Enable WAL mode for better concurrent access
    conn.execute('PRAGMA journal_mode=WAL')

    return conn


def initialize_database(db_path: str) -> None:
    """
    Initialize database with schema.

    Args:
        db_path: Path to SQLite database file
    """
    # Read schema from file
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Execute schema
    cursor.executescript(schema_sql)

    conn.commit()
    conn.close()


# ============================================================
# Customer Operations
# ============================================================

def create_customer(
    db_path: str,
    name: str,
    phone: str,
    email: Optional[str] = None
) -> int:
    """
    Create a new customer.

    Args:
        db_path: Path to database
        name: Customer name
        phone: Phone number (unique)
        email: Email address (optional)

    Returns:
        Customer ID

    Raises:
        sqlite3.IntegrityError: If phone already exists
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO customers (name, phone, email)
        VALUES (?, ?, ?)
    """, (name, phone, email))

    customer_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return customer_id


def get_customer_by_phone(db_path: str, phone: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve customer by phone number.

    Args:
        db_path: Path to database
        phone: Phone number to search

    Returns:
        Customer dict or None if not found
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM customers WHERE phone = ?
    """, (phone,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_or_create_customer(
    db_path: str,
    name: str,
    phone: str,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get existing customer or create new one.

    Args:
        db_path: Path to database
        name: Customer name
        phone: Phone number
        email: Email address (optional)

    Returns:
        Customer dict
    """
    customer = get_customer_by_phone(db_path, phone)

    if customer:
        # Update name if different
        if customer['name'] != name:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE customers SET name = ? WHERE phone = ?
            """, (name, phone))
            conn.commit()
            conn.close()
            customer['name'] = name

        return customer

    # Create new customer
    customer_id = create_customer(db_path, name, phone, email)
    return get_customer_by_phone(db_path, phone)


# ============================================================
# Restaurant Operations
# ============================================================

def create_restaurant(db_path: str, restaurant_data: Dict[str, Any]) -> int:
    """
    Create a new restaurant.

    Args:
        db_path: Path to database
        restaurant_data: Dictionary with restaurant details

    Returns:
        Restaurant ID
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO restaurants (
            name, cuisine, latitude, longitude, address, city,
            total_capacity, available_tables, price_range, rating,
            opening_time, closing_time, has_parking, has_outdoor_seating
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        restaurant_data['name'],
        restaurant_data['cuisine'],
        restaurant_data['latitude'],
        restaurant_data['longitude'],
        restaurant_data['address'],
        restaurant_data.get('city', 'Chennai'),
        restaurant_data['total_capacity'],
        restaurant_data['available_tables'],
        restaurant_data.get('price_range', '₹₹'),
        restaurant_data.get('rating', 4.0),
        restaurant_data.get('opening_time', '11:00'),
        restaurant_data.get('closing_time', '23:00'),
        restaurant_data.get('has_parking', 0),
        restaurant_data.get('has_outdoor_seating', 0)
    ))

    restaurant_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return restaurant_id


def get_restaurant_by_id(db_path: str, restaurant_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve restaurant by ID.

    Args:
        db_path: Path to database
        restaurant_id: Restaurant ID

    Returns:
        Restaurant dict or None if not found
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM restaurants WHERE id = ?
    """, (restaurant_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_restaurants(
    db_path: str,
    cuisine: Optional[str] = None,
    min_rating: Optional[float] = None,
    price_range: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve restaurants with optional filters.

    Args:
        db_path: Path to database
        cuisine: Filter by cuisine type
        min_rating: Minimum rating
        price_range: Filter by price range

    Returns:
        List of restaurant dicts
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM restaurants WHERE 1=1"
    params = []

    if cuisine:
        query += " AND cuisine = ?"
        params.append(cuisine)

    if min_rating is not None:
        query += " AND rating >= ?"
        params.append(min_rating)

    if price_range:
        query += " AND price_range = ?"
        params.append(price_range)

    query += " ORDER BY rating DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_restaurant_tables(
    db_path: str,
    restaurant_id: int,
    increment: int
) -> bool:
    """
    Update available tables count.

    Args:
        db_path: Path to database
        restaurant_id: Restaurant ID
        increment: Amount to add (negative to subtract)

    Returns:
        True if successful
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE restaurants
        SET available_tables = available_tables + ?
        WHERE id = ?
    """, (increment, restaurant_id))

    success = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return success


# ============================================================
# Reservation Operations
# ============================================================

def create_reservation(db_path: str, reservation_data: Dict[str, Any]) -> int:
    """
    Create a new reservation and decrement available tables.

    Args:
        db_path: Path to database
        reservation_data: Dictionary with reservation details

    Returns:
        Reservation ID
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        # Create reservation
        cursor.execute("""
            INSERT INTO reservations (
                customer_id, restaurant_id, reservation_date,
                reservation_time, party_size, special_requests
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            reservation_data['customer_id'],
            reservation_data['restaurant_id'],
            reservation_data['reservation_date'],
            reservation_data['reservation_time'],
            reservation_data['party_size'],
            reservation_data.get('special_requests')
        ))

        reservation_id = cursor.lastrowid

        # Decrement available tables
        cursor.execute("""
            UPDATE restaurants
            SET available_tables = available_tables - 1
            WHERE id = ?
        """, (reservation_data['restaurant_id'],))

        conn.commit()
        return reservation_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


def get_reservation_by_id(
    db_path: str,
    reservation_id: int
) -> Optional[Dict[str, Any]]:
    """
    Retrieve reservation by ID.

    Args:
        db_path: Path to database
        reservation_id: Reservation ID

    Returns:
        Reservation dict or None if not found
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reservations WHERE id = ?
    """, (reservation_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_reservation_status(
    db_path: str,
    reservation_id: int,
    status: str
) -> bool:
    """
    Update reservation status.

    Args:
        db_path: Path to database
        reservation_id: Reservation ID
        status: New status (confirmed, cancelled, completed, no_show)

    Returns:
        True if successful
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reservations
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, reservation_id))

    success = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return success


def cancel_reservation(db_path: str, reservation_id: int) -> bool:
    """
    Cancel a reservation and increment available tables.

    Args:
        db_path: Path to database
        reservation_id: Reservation ID

    Returns:
        True if successful
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        # Get reservation details
        cursor.execute("""
            SELECT restaurant_id, status FROM reservations WHERE id = ?
        """, (reservation_id,))

        row = cursor.fetchone()

        if not row or row['status'] == 'cancelled':
            return False

        restaurant_id = row['restaurant_id']

        # Update status
        cursor.execute("""
            UPDATE reservations
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reservation_id,))

        # Increment available tables
        cursor.execute("""
            UPDATE restaurants
            SET available_tables = available_tables + 1
            WHERE id = ?
        """, (restaurant_id,))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


def get_customer_reservations(
    db_path: str,
    customer_id: int,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all reservations for a customer.

    Args:
        db_path: Path to database
        customer_id: Customer ID
        status: Filter by status (optional)

    Returns:
        List of reservation dicts with restaurant details
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT
            r.*,
            rest.name as restaurant_name,
            rest.cuisine,
            rest.address
        FROM reservations r
        JOIN restaurants rest ON r.restaurant_id = rest.id
        WHERE r.customer_id = ?
    """

    params = [customer_id]

    if status:
        query += " AND r.status = ?"
        params.append(status)

    query += " ORDER BY r.reservation_date DESC, r.reservation_time DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ============================================================
# Daily Offers Operations
# ============================================================

def create_daily_offer(db_path: str, offer_data: Dict[str, Any]) -> int:
    """
    Create a new daily offer.

    Args:
        db_path: Path to database
        offer_data: Dictionary with offer details

    Returns:
        Offer ID
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_offers (
            restaurant_id, offer_title, offer_description,
            discount_percentage, valid_from, valid_until
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        offer_data['restaurant_id'],
        offer_data['offer_title'],
        offer_data['offer_description'],
        offer_data.get('discount_percentage'),
        offer_data['valid_from'],
        offer_data['valid_until']
    ))

    offer_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return offer_id


def get_active_offers(
    db_path: str,
    restaurant_id: int,
    current_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get active offers for a restaurant.

    Args:
        db_path: Path to database
        restaurant_id: Restaurant ID
        current_date: Date to check (default: today)

    Returns:
        List of offer dicts
    """
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d')

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM daily_offers
        WHERE restaurant_id = ?
        AND is_active = 1
        AND valid_from <= ?
        AND valid_until >= ?
    """, (restaurant_id, current_date, current_date))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ============================================================
# Feedback Operations
# ============================================================

def create_feedback(db_path: str, feedback_data: Dict[str, Any]) -> int:
    """
    Create customer feedback.

    Args:
        db_path: Path to database
        feedback_data: Dictionary with feedback details

    Returns:
        Feedback ID
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO feedback (
            customer_id, restaurant_id, reservation_id, rating, comment
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        feedback_data['customer_id'],
        feedback_data['restaurant_id'],
        feedback_data.get('reservation_id'),
        feedback_data['rating'],
        feedback_data.get('comment')
    ))

    feedback_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return feedback_id


def get_restaurant_feedback(
    db_path: str,
    restaurant_id: int
) -> List[Dict[str, Any]]:
    """
    Get all feedback for a restaurant.

    Args:
        db_path: Path to database
        restaurant_id: Restaurant ID

    Returns:
        List of feedback dicts
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            f.*,
            c.name as customer_name
        FROM feedback f
        JOIN customers c ON f.customer_id = c.id
        WHERE f.restaurant_id = ?
        ORDER BY f.created_at DESC
    """, (restaurant_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ============================================================
# Conversation Logging Operations
# ============================================================

def save_conversation_message(
    db_path: str,
    customer_id: int,
    role: str,
    message: str,
    tool_used: Optional[str] = None
) -> int:
    """
    Save a conversation message to the conversation_logs table.

    Args:
        db_path: Path to database
        customer_id: Customer ID
        role: Message role ('user' or 'assistant')
        message: Message text
        tool_used: Name of tool used (optional, for assistant messages)

    Returns:
        Message ID

    Raises:
        Exception: If role is not 'user' or 'assistant'
    """
    if role not in ('user', 'assistant'):
        raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

    if not message or not message.strip():
        raise ValueError("Message cannot be empty")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conversation_logs (customer_id, role, message, tool_used)
        VALUES (?, ?, ?, ?)
    """, (customer_id, role, message, tool_used))

    message_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return message_id


def get_customer_conversations(
    db_path: str,
    customer_id: int
) -> List[Dict[str, Any]]:
    """
    Retrieve all conversation messages for a customer.

    Args:
        db_path: Path to database
        customer_id: Customer ID

    Returns:
        List of conversation message dicts (ordered by time, oldest first)
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            customer_id,
            role,
            message,
            tool_used,
            created_at
        FROM conversation_logs
        WHERE customer_id = ?
        ORDER BY created_at ASC
    """, (customer_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_conversations_summary(db_path: str) -> List[Dict[str, Any]]:
    """
    Get summary of all customer conversations with their last message.

    Returns:
        List of dicts with customer info and last message
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id as customer_id,
            c.name,
            c.phone,
            c.email,
            last_msg.message as last_message,
            last_msg.created_at as last_message_time,
            (SELECT COUNT(*) FROM conversation_logs WHERE customer_id = c.id) as message_count
        FROM customers c
        INNER JOIN conversation_logs last_msg ON last_msg.id = (
            SELECT id
            FROM conversation_logs
            WHERE customer_id = c.id
            ORDER BY created_at DESC
            LIMIT 1
        )
        ORDER BY last_msg.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

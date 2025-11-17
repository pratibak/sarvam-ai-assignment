-- Restaurant Booking System Database Schema
-- SQLite version

-- ============================================================
-- Table: customers
-- Stores customer information for bookings
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: restaurants
-- Stores restaurant locations and details
-- ============================================================
CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cuisine TEXT NOT NULL,

    -- Geospatial data
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT 'Chennai',

    -- Capacity management
    total_capacity INTEGER NOT NULL,
    available_tables INTEGER NOT NULL,

    -- Restaurant details
    price_range TEXT CHECK(price_range IN ('₹', '₹₹', '₹₹₹', '₹₹₹₹')),
    rating REAL CHECK(rating >= 0 AND rating <= 5),

    -- Operating hours
    opening_time TEXT DEFAULT '11:00',
    closing_time TEXT DEFAULT '23:00',

    -- Features
    has_parking BOOLEAN DEFAULT 0,
    has_outdoor_seating BOOLEAN DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: reservations
-- Stores booking information
-- ============================================================
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,

    -- Booking details
    reservation_date DATE NOT NULL,
    reservation_time TEXT NOT NULL,
    party_size INTEGER NOT NULL CHECK(party_size > 0),

    -- Status tracking
    status TEXT DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'cancelled', 'completed', 'no_show')),
    special_requests TEXT,

    -- Upsell tracking
    accepted_offer BOOLEAN DEFAULT 0,
    offer_details TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);

-- ============================================================
-- Table: daily_offers
-- Stores promotional offers
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL,

    offer_title TEXT NOT NULL,
    offer_description TEXT NOT NULL,
    discount_percentage INTEGER,

    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    is_active BOOLEAN DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);

-- ============================================================
-- Table: conversation_logs
-- Stores customer-assistant conversation history
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    message TEXT NOT NULL,
    tool_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Index for conversation lookups by customer
CREATE INDEX IF NOT EXISTS idx_conversation_customer
ON conversation_logs(customer_id, created_at);

-- ============================================================
-- Table: feedback
-- Stores customer reviews and ratings
-- ============================================================
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    reservation_id INTEGER,

    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id)
);

-- ============================================================
-- Indexes for Performance
-- ============================================================

-- Customer lookup
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

-- Reservation queries
CREATE INDEX IF NOT EXISTS idx_reservations_customer ON reservations(customer_id);
CREATE INDEX IF NOT EXISTS idx_reservations_restaurant ON reservations(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_reservations_date ON reservations(reservation_date);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);

-- Offer queries
CREATE INDEX IF NOT EXISTS idx_offers_restaurant ON daily_offers(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_offers_dates ON daily_offers(valid_from, valid_until);

-- Feedback queries
CREATE INDEX IF NOT EXISTS idx_feedback_restaurant ON feedback(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_feedback_customer ON feedback(customer_id);

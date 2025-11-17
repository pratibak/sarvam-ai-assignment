"""
Tests for conversation logging functionality.

TDD Approach: These tests are written BEFORE implementing the functions.
They should FAIL initially, then pass after implementation.
"""

import pytest
import tempfile
import os

from database.db_manager import (
    initialize_database,
    create_customer,
    save_conversation_message,
    get_customer_conversations,
    get_all_conversations_summary
)


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    # Initialize with schema
    initialize_database(db_path)

    yield db_path

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def test_customer(test_db):
    """Create a test customer."""
    customer_id = create_customer(
        test_db,
        name="Test User",
        phone="+91-9999988888",
        email="test@example.com"
    )
    return customer_id


class TestConversationLogging:
    """Test suite for conversation logging functions."""

    def test_save_user_message(self, test_db, test_customer):
        """Test saving a user message."""
        message_id = save_conversation_message(
            test_db,
            customer_id=test_customer,
            role='user',
            message="Find me Italian restaurants"
        )

        assert message_id is not None
        assert isinstance(message_id, int)
        assert message_id > 0

    def test_save_assistant_message(self, test_db, test_customer):
        """Test saving an assistant message."""
        message_id = save_conversation_message(
            test_db,
            customer_id=test_customer,
            role='assistant',
            message="Here are 5 Italian restaurants near you..."
        )

        assert message_id is not None
        assert isinstance(message_id, int)
        assert message_id > 0

    def test_save_message_with_tool(self, test_db, test_customer):
        """Test saving a message with tool information."""
        message_id = save_conversation_message(
            test_db,
            customer_id=test_customer,
            role='assistant',
            message="I found 5 restaurants for you",
            tool_used='find_restaurants'
        )

        assert message_id is not None

        # Verify tool_used is stored
        conversations = get_customer_conversations(test_db, test_customer)
        assert len(conversations) == 1
        assert conversations[0]['tool_used'] == 'find_restaurants'

    def test_invalid_role_raises_error(self, test_db, test_customer):
        """Test that invalid role raises an error."""
        with pytest.raises(Exception):
            save_conversation_message(
                test_db,
                customer_id=test_customer,
                role='invalid_role',  # Should fail
                message="Test message"
            )

    def test_retrieve_customer_conversations(self, test_db, test_customer):
        """Test retrieving all messages for a customer."""
        # Save multiple messages
        save_conversation_message(test_db, test_customer, 'user', "Message 1")
        save_conversation_message(test_db, test_customer, 'assistant', "Response 1")
        save_conversation_message(test_db, test_customer, 'user', "Message 2")

        conversations = get_customer_conversations(test_db, test_customer)

        assert len(conversations) == 3
        assert conversations[0]['role'] == 'user'
        assert conversations[0]['message'] == 'Message 1'
        assert conversations[1]['role'] == 'assistant'
        assert conversations[2]['role'] == 'user'

    def test_conversations_ordered_by_time(self, test_db, test_customer):
        """Test that conversations are returned in chronological order."""
        save_conversation_message(test_db, test_customer, 'user', "First message")
        save_conversation_message(test_db, test_customer, 'assistant', "Second message")
        save_conversation_message(test_db, test_customer, 'user', "Third message")

        conversations = get_customer_conversations(test_db, test_customer)

        # Should be in order: oldest to newest
        assert conversations[0]['message'] == 'First message'
        assert conversations[1]['message'] == 'Second message'
        assert conversations[2]['message'] == 'Third message'

    def test_empty_conversation_returns_empty_list(self, test_db, test_customer):
        """Test that customer with no messages returns empty list."""
        conversations = get_customer_conversations(test_db, test_customer)

        assert conversations == []
        assert isinstance(conversations, list)

    def test_invalid_customer_id_returns_empty(self, test_db):
        """Test that invalid customer_id returns empty list."""
        conversations = get_customer_conversations(test_db, customer_id=99999)

        assert conversations == []

    def test_multiple_customers_separate_conversations(self, test_db):
        """Test that different customers have separate conversations."""
        customer1 = create_customer(test_db, "User 1", "+91-1111111111")
        customer2 = create_customer(test_db, "User 2", "+91-2222222222")

        save_conversation_message(test_db, customer1, 'user', "Customer 1 message")
        save_conversation_message(test_db, customer2, 'user', "Customer 2 message")

        conv1 = get_customer_conversations(test_db, customer1)
        conv2 = get_customer_conversations(test_db, customer2)

        assert len(conv1) == 1
        assert len(conv2) == 1
        assert conv1[0]['message'] == 'Customer 1 message'
        assert conv2[0]['message'] == 'Customer 2 message'


class TestConversationSummary:
    """Test suite for conversation summary functions."""

    def test_get_all_conversations_summary(self, test_db):
        """Test getting summary of all customer conversations."""
        # Create two customers with conversations
        customer1 = create_customer(test_db, "Alice", "+91-1111111111")
        customer2 = create_customer(test_db, "Bob", "+91-2222222222")

        save_conversation_message(test_db, customer1, 'user', "Alice's message")
        save_conversation_message(test_db, customer2, 'user', "Bob's message")

        summary = get_all_conversations_summary(test_db)

        assert len(summary) == 2
        assert any(c['name'] == 'Alice' for c in summary)
        assert any(c['name'] == 'Bob' for c in summary)

        # Check message counts are correct
        alice_summary = next(c for c in summary if c['name'] == 'Alice')
        assert alice_summary['message_count'] == 1

    def test_summary_includes_last_message(self, test_db, test_customer):
        """Test that summary includes last message from conversation."""
        save_conversation_message(test_db, test_customer, 'user', "First")
        save_conversation_message(test_db, test_customer, 'assistant', "Second")
        save_conversation_message(test_db, test_customer, 'user', "Last message")

        summary = get_all_conversations_summary(test_db)

        assert len(summary) == 1
        assert summary[0]['last_message'] == 'Last message'

    def test_summary_includes_contact_info(self, test_db):
        """Test that summary includes customer contact information."""
        customer = create_customer(
            test_db,
            name="John Doe",
            phone="+91-9876543210",
            email="john@example.com"
        )
        save_conversation_message(test_db, customer, 'user', "Hello")

        summary = get_all_conversations_summary(test_db)

        assert len(summary) == 1
        assert summary[0]['name'] == 'John Doe'
        assert summary[0]['phone'] == '+91-9876543210'

    def test_summary_empty_when_no_conversations(self, test_db):
        """Test that summary is empty when no conversations exist."""
        # Create customer but don't save any messages
        create_customer(test_db, "No Messages", "+91-9999999999")

        summary = get_all_conversations_summary(test_db)

        # Should return empty list (customer has no messages)
        assert summary == []

    def test_summary_counts_all_messages(self, test_db, test_customer):
        """Test that message count includes ALL messages, not just last one."""
        # Save multiple messages
        save_conversation_message(test_db, test_customer, 'user', "Message 1")
        save_conversation_message(test_db, test_customer, 'assistant', "Response 1")
        save_conversation_message(test_db, test_customer, 'user', "Message 2")
        save_conversation_message(test_db, test_customer, 'assistant', "Response 2")
        save_conversation_message(test_db, test_customer, 'user', "Message 3")

        summary = get_all_conversations_summary(test_db)

        assert len(summary) == 1
        assert summary[0]['message_count'] == 5  # Should count all 5 messages
        assert summary[0]['last_message'] == 'Message 3'  # Last message should be correct

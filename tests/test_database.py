"""
Comprehensive database tests for Secu-Agent AI lead management system.
Tests all database operations, models, relationships, and edge cases.
"""

import pytest
import sys
import os

# Add parent directory to path to import database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import (
    engine, SessionLocal, Base, get_db,
    Lead, Message,
    LeadOperations, MessageOperations,
    check_db_connection, init_db
)
from sqlalchemy import text
from datetime import datetime
from sqlalchemy.orm import Session


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test."""
    # Use in-memory SQLite for testing
    test_engine = engine
    Base.metadata.create_all(bind=test_engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up database after each test
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)


class TestDatabaseConnection:
    """Test database connection and initialization."""
    
    def test_database_connection(self):
        """Test that database connection works."""
        assert check_db_connection() is True
    
    def test_database_initialization(self):
        """Test that database tables are created correctly."""
        init_db()
        # Check that tables exist by querying them
        db = SessionLocal()
        try:
            # This should not raise an error if tables exist
            db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        finally:
            db.close()


class TestLeadModel:
    """Test Lead model and operations."""
    
    def test_create_lead_basic(self, test_db):
        """Test creating a lead with basic information."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="John Doe",
            email="john@example.com",
            source="event"
        )
        
        assert lead.id is not None
        assert lead.name == "John Doe"
        assert lead.email == "john@example.com"
        assert lead.source == "event"
        assert lead.status == "new"
        assert lead.created_at is not None
        assert lead.updated_at is not None
    
    def test_create_lead_full(self, test_db):
        """Test creating a lead with all fields."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Jane Smith",
            email="jane@example.com",
            company="Tech Corp",
            job_title="CTO",
            source="website",
            status="contacted"
        )
        
        assert lead.name == "Jane Smith"
        assert lead.email == "jane@example.com"
        assert lead.company == "Tech Corp"
        assert lead.job_title == "CTO"
        assert lead.source == "website"
        assert lead.status == "contacted"
    
    def test_get_lead_by_id(self, test_db):
        """Test retrieving a lead by ID."""
        created_lead = LeadOperations.create_lead(
            db=test_db,
            name="Test User",
            email="test@example.com",
            source="event"
        )
        
        retrieved_lead = LeadOperations.get_lead(test_db, created_lead.id)
        
        assert retrieved_lead is not None
        assert retrieved_lead.id == created_lead.id
        assert retrieved_lead.name == "Test User"
    
    def test_get_lead_by_email(self, test_db):
        """Test retrieving a lead by email."""
        LeadOperations.create_lead(
            db=test_db,
            name="Email Test",
            email="emailtest@example.com",
            source="event"
        )
        
        retrieved_lead = LeadOperations.get_lead_by_email(test_db, "emailtest@example.com")
        
        assert retrieved_lead is not None
        assert retrieved_lead.email == "emailtest@example.com"
    
    def test_get_all_leads(self, test_db):
        """Test retrieving all leads."""
        # Create multiple leads
        LeadOperations.create_lead(db=test_db, name="Lead 1", email="lead1@example.com", source="event")
        LeadOperations.create_lead(db=test_db, name="Lead 2", email="lead2@example.com", source="website")
        LeadOperations.create_lead(db=test_db, name="Lead 3", email="lead3@example.com", source="referral")
        
        leads = LeadOperations.get_all_leads(test_db)
        
        assert len(leads) == 3
    
    def test_get_leads_with_pagination(self, test_db):
        """Test retrieving leads with pagination."""
        # Create 5 leads
        for i in range(1, 6):
            LeadOperations.create_lead(
                db=test_db,
                name=f"Lead {i}",
                email=f"lead{i}@example.com",
                source="event"
            )
        
        # Get first 2 leads
        leads_page1 = LeadOperations.get_all_leads(test_db, skip=0, limit=2)
        assert len(leads_page1) == 2
        
        # Get next 2 leads
        leads_page2 = LeadOperations.get_all_leads(test_db, skip=2, limit=2)
        assert len(leads_page2) == 2
    
    def test_get_leads_by_status(self, test_db):
        """Test filtering leads by status."""
        LeadOperations.create_lead(db=test_db, name="New Lead", email="new@example.com", source="event", status="new")
        LeadOperations.create_lead(db=test_db, name="Contacted Lead", email="contacted@example.com", source="event", status="contacted")
        LeadOperations.create_lead(db=test_db, name="Another New", email="new2@example.com", source="event", status="new")
        
        new_leads = LeadOperations.get_leads_by_status(test_db, "new")
        contacted_leads = LeadOperations.get_leads_by_status(test_db, "contacted")
        
        assert len(new_leads) == 2
        assert len(contacted_leads) == 1
    
    def test_update_lead_status(self, test_db):
        """Test updating lead status."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Status Test",
            email="status@example.com",
            source="event",
            status="new"
        )
        
        updated_lead = LeadOperations.update_lead_status(test_db, lead.id, "contacted")
        
        assert updated_lead.status == "contacted"
        assert updated_lead.updated_at > lead.created_at
    
    def test_delete_lead(self, test_db):
        """Test deleting a lead."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Delete Test",
            email="delete@example.com",
            source="event"
        )
        
        success = LeadOperations.delete_lead(test_db, lead.id)
        
        assert success is True
        
        # Verify lead is deleted
        deleted_lead = LeadOperations.get_lead(test_db, lead.id)
        assert deleted_lead is None
    
    def test_email_uniqueness(self, test_db):
        """Test that email addresses are unique."""
        LeadOperations.create_lead(
            db=test_db,
            name="First User",
            email="unique@example.com",
            source="event"
        )
        
        # Try to create another lead with same email
        with pytest.raises(Exception):  # Should raise an integrity error
            LeadOperations.create_lead(
                db=test_db,
                name="Second User",
                email="unique@example.com",
                source="event"
            )


class TestMessageModel:
    """Test Message model and operations."""
    
    def test_create_message_basic(self, test_db):
        """Test creating a message with basic information."""
        # First create a lead
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Message Test",
            email="message@example.com",
            source="event"
        )
        
        message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Hello, this is a test message",
            channel="email",
            direction="outbound"
        )
        
        assert message.id is not None
        assert message.lead_id == lead.id
        assert message.message_text == "Hello, this is a test message"
        assert message.channel == "email"
        assert message.direction == "outbound"
        assert message.timestamp is not None
    
    def test_get_message_by_id(self, test_db):
        """Test retrieving a message by ID."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Message User",
            email="msguser@example.com",
            source="event"
        )
        
        created_message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Test message",
            channel="email",
            direction="outbound"
        )
        
        retrieved_message = MessageOperations.get_message(test_db, created_message.id)
        
        assert retrieved_message is not None
        assert retrieved_message.id == created_message.id
        assert retrieved_message.message_text == "Test message"
    
    def test_get_messages_by_lead(self, test_db):
        """Test retrieving all messages for a specific lead."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Multi Message",
            email="multi@example.com",
            source="event"
        )
        
        # Create multiple messages for the same lead
        MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 1", channel="email", direction="outbound")
        MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 2", channel="whatsapp", direction="inbound")
        MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 3", channel="email", direction="outbound")
        
        messages = MessageOperations.get_messages_by_lead(test_db, lead.id)
        
        assert len(messages) == 3
    
    def test_get_messages_by_channel(self, test_db):
        """Test retrieving messages by channel."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Channel Test",
            email="channel@example.com",
            source="event"
        )
        
        # Create messages with different channels
        MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Email 1", channel="email", direction="outbound")
        MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Email 2", channel="email", direction="inbound")
        MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="WhatsApp", channel="whatsapp", direction="outbound")
        
        email_messages = MessageOperations.get_messages_by_channel(test_db, "email")
        whatsapp_messages = MessageOperations.get_messages_by_channel(test_db, "whatsapp")
        
        assert len(email_messages) == 2
        assert len(whatsapp_messages) == 1
    
    def test_delete_message(self, test_db):
        """Test deleting a message."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Delete Message",
            email="delmsg@example.com",
            source="event"
        )
        
        message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Delete this message",
            channel="email",
            direction="outbound"
        )
        
        success = MessageOperations.delete_message(test_db, message.id)
        
        assert success is True
        
        # Verify message is deleted
        deleted_message = MessageOperations.get_message(test_db, message.id)
        assert deleted_message is None


class TestLeadMessageRelationship:
    """Test the relationship between Lead and Message models."""
    
    def test_lead_has_messages(self, test_db):
        """Test that a lead can have multiple messages."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Relationship Test",
            email="rel@example.com",
            source="event"
        )
        
        # Create messages for the lead
        msg1 = MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 1", channel="email", direction="outbound")
        msg2 = MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 2", channel="whatsapp", direction="inbound")
        
        # Refresh lead to get updated relationships
        test_db.refresh(lead)
        
        assert len(lead.messages) == 2
        assert msg1 in lead.messages
        assert msg2 in lead.messages
    
    def test_message_belongs_to_lead(self, test_db):
        """Test that a message belongs to a lead."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Owner Test",
            email="owner@example.com",
            source="event"
        )
        
        message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Owner message",
            channel="email",
            direction="outbound"
        )
        
        # Refresh message to get updated relationships
        test_db.refresh(message)
        
        assert message.lead == lead
        assert message.lead.id == lead.id
    
    def test_cascade_delete_lead_deletes_messages(self, test_db):
        """Test that deleting a lead also deletes its messages."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Cascade Test",
            email="cascade@example.com",
            source="event"
        )
        
        # Create messages for the lead
        msg1 = MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 1", channel="email", direction="outbound")
        msg2 = MessageOperations.create_message(db=test_db, lead_id=lead.id, message_text="Message 2", channel="whatsapp", direction="inbound")
        
        # Delete the lead
        LeadOperations.delete_lead(test_db, lead.id)
        
        # Verify messages are also deleted
        deleted_msg1 = MessageOperations.get_message(test_db, msg1.id)
        deleted_msg2 = MessageOperations.get_message(test_db, msg2.id)
        
        assert deleted_msg1 is None
        assert deleted_msg2 is None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_get_nonexistent_lead(self, test_db):
        """Test retrieving a lead that doesn't exist."""
        lead = LeadOperations.get_lead(test_db, 99999)
        assert lead is None
    
    def test_get_nonexistent_message(self, test_db):
        """Test retrieving a message that doesn't exist."""
        message = MessageOperations.get_message(test_db, 99999)
        assert message is None
    
    def test_update_nonexistent_lead_status(self, test_db):
        """Test updating status of a lead that doesn't exist."""
        lead = LeadOperations.update_lead_status(test_db, 99999, "contacted")
        assert lead is None
    
    def test_delete_nonexistent_lead(self, test_db):
        """Test deleting a lead that doesn't exist."""
        success = LeadOperations.delete_lead(test_db, 99999)
        assert success is False
    
    def test_delete_nonexistent_message(self, test_db):
        """Test deleting a message that doesn't exist."""
        success = MessageOperations.delete_message(test_db, 99999)
        assert success is False
    
    def test_create_message_for_nonexistent_lead(self, test_db):
        """Test creating a message for a lead that doesn't exist."""
        with pytest.raises(Exception):
            MessageOperations.create_message(
                db=test_db,
                lead_id=99999,
                message_text="Test message",
                channel="email",
                direction="outbound"
            )
    
    def test_empty_fields(self, test_db):
        """Test creating leads with optional fields empty."""
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Minimal Lead",
            email="minimal@example.com",
            source="event"
        )
        
        assert lead.company is None
        assert lead.job_title is None
    
    def test_long_text_fields(self, test_db):
        """Test handling of long text fields."""
        long_name = "A" * 255
        long_message = "B" * 10000
        
        lead = LeadOperations.create_lead(
            db=test_db,
            name=long_name,
            email="long@example.com",
            source="event"
        )
        
        message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text=long_message,
            channel="email",
            direction="outbound"
        )
        
        assert len(lead.name) == 255
        assert len(message.message_text) == 10000


class TestDatabaseSession:
    """Test database session management."""
    
    def test_get_db_dependency(self):
        """Test that get_db dependency works correctly."""
        db_gen = get_db()
        db = next(db_gen)
        
        assert isinstance(db, Session)
        
        # Clean up
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
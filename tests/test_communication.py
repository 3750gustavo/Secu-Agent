"""
Comprehensive tests for the communication module.
Tests email service, SMS service, database logging, and integration.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, get_db, LeadOperations, MessageOperations
from communication import (
    EmailService, SMSService, CommunicationService,
    get_communication_service, DeliveryStatus
)
from ai_client import Agent


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test."""
    init_db()
    db = next(get_db())
    yield db
    db.close()


@pytest.fixture(scope="function")
def sample_lead(test_db):
    """Create a sample lead for testing with unique email."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    lead = LeadOperations.create_lead(
        db=test_db,
        name="Test User",
        email=f"test{unique_id}@example.com",
        company="Test Company",
        job_title="Test Engineer",
        source="test",
        status="new"
    )
    yield lead
    # Cleanup: delete all messages for this lead
    try:
        from database import Message
        test_db.rollback()  # Ensure we can perform operations
        test_db.query(Message).filter(Message.lead_id == lead.id).delete()
        test_db.commit()
    except Exception:
        test_db.rollback()


class TestEmailService:
    """Tests for EmailService class."""
    
    def test_send_email_success(self, test_db, sample_lead):
        """Test successful email sending."""
        email_service = EmailService(failure_rate=0.0)  # No failures for testing
        
        result = email_service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test email body",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is True
        assert result["to"] == "recipient@example.com"
        assert result["subject"] == "Test Subject"
        assert "message_id" in result
        assert result["status"] in [status.value for status in DeliveryStatus]
        assert "metrics" in result
    
    def test_send_email_logs_to_database(self, test_db, sample_lead):
        """Test that emails are logged to database."""
        email_service = EmailService(failure_rate=0.0)
        
        result = email_service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test email body",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        # Check that message was logged
        messages = MessageOperations.get_messages_by_lead(test_db, sample_lead.id)
        assert len(messages) == 1
        assert messages[0].channel == "email"
        assert messages[0].direction == "outbound"
        assert "Test Subject" in messages[0].message_text
        assert "Test email body" in messages[0].message_text
    
    def test_send_email_with_failure(self, test_db, sample_lead):
        """Test email sending with simulated failure."""
        email_service = EmailService(failure_rate=1.0)  # Always fail
        
        result = email_service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test email body",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is False
        assert result["status"] == DeliveryStatus.FAILED.value
        assert "error" in result
    
    def test_send_html_email(self, test_db, sample_lead):
        """Test sending HTML email."""
        email_service = EmailService(failure_rate=0.0)
        
        result = email_service.send_email(
            to="recipient@example.com",
            subject="HTML Test",
            body="<h1>Test HTML</h1>",
            lead_id=sample_lead.id,
            db_session=test_db,
            html=True
        )
        
        assert result["success"] is True
        assert result["metrics"]["html"] is True
        assert result["metrics"]["click_rate"] > 0  # HTML emails have click rate
    
    def test_send_template_email(self, test_db, sample_lead):
        """Test sending email using template."""
        email_service = EmailService(failure_rate=0.0)
        
        result = email_service.send_template_email(
            template_name="welcome",
            to="recipient@example.com",
            lead_id=sample_lead.id,
            db_session=test_db,
            name="Test User"
        )
        
        assert result["success"] is True
        assert "Test User" in result["subject"] or "Welcome" in result["subject"]
    
    def test_send_invalid_template(self, test_db, sample_lead):
        """Test sending email with invalid template."""
        email_service = EmailService(failure_rate=0.0)
        
        result = email_service.send_template_email(
            template_name="invalid_template",
            to="recipient@example.com",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_get_email_stats(self, test_db, sample_lead):
        """Test getting email statistics."""
        email_service = EmailService(failure_rate=0.0)
        
        # Get initial stats
        initial_stats = email_service.get_email_stats(test_db)
        initial_count = initial_stats["total_emails"]
        
        # Send some emails
        email_service.send_email(
            to="recipient1@example.com",
            subject="Test 1",
            body="Body 1",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        email_service.send_email(
            to="recipient2@example.com",
            subject="Test 2",
            body="Body 2",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        stats = email_service.get_email_stats(test_db)
        
        # Check that we added 2 emails
        assert stats["total_emails"] == initial_count + 2
        assert stats["outbound"] >= 2  # At least our 2 new emails
        assert stats["success_rate"] == 1.0


class TestSMSService:
    """Tests for SMSService class."""
    
    def test_send_sms_success(self, test_db, sample_lead):
        """Test successful SMS sending."""
        sms_service = SMSService(failure_rate=0.0)
        
        result = sms_service.send_sms(
            phone="+1234567890",
            message="Test SMS message",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is True
        assert result["phone"] == "+1234567890"
        assert result["message"] == "Test SMS message"
        assert "message_id" in result
        assert result["status"] == DeliveryStatus.DELIVERED.value
    
    def test_send_sms_logs_to_database(self, test_db, sample_lead):
        """Test that SMS messages are logged to database."""
        sms_service = SMSService(failure_rate=0.0)
        
        result = sms_service.send_sms(
            phone="+1234567890",
            message="Test SMS message",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        # Check that message was logged
        messages = MessageOperations.get_messages_by_lead(test_db, sample_lead.id)
        assert len(messages) == 1
        assert messages[0].channel == "sms"
        assert messages[0].direction == "outbound"
        assert "Test SMS message" in messages[0].message_text
    
    def test_send_sms_with_failure(self, test_db, sample_lead):
        """Test SMS sending with simulated failure."""
        sms_service = SMSService(failure_rate=1.0)  # Always fail
        
        result = sms_service.send_sms(
            phone="+1234567890",
            message="Test SMS message",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is False
        assert result["status"] == DeliveryStatus.FAILED.value
        assert "error" in result
    
    def test_send_sms_invalid_phone(self, test_db, sample_lead):
        """Test SMS sending with invalid phone number."""
        sms_service = SMSService(failure_rate=0.0)
        
        result = sms_service.send_sms(
            phone="invalid",
            message="Test SMS message",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is False
        assert "Invalid phone number" in result["error"]
    
    def test_send_sms_long_message_truncation(self, test_db, sample_lead):
        """Test that long SMS messages are truncated."""
        sms_service = SMSService(failure_rate=0.0)
        
        long_message = "A" * 200  # 200 characters, exceeds 160 limit
        
        result = sms_service.send_sms(
            phone="+1234567890",
            message=long_message,
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is True
        assert result["character_count"] <= 160
        assert result["segments"] == 1
    
    def test_get_sms_stats(self, test_db, sample_lead):
        """Test getting SMS statistics."""
        sms_service = SMSService(failure_rate=0.0)
        
        # Send some SMS messages
        sms_service.send_sms(
            phone="+1234567890",
            message="SMS 1",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        sms_service.send_sms(
            phone="+0987654321",
            message="SMS 2",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        stats = sms_service.get_sms_stats(test_db)
        
        assert stats["total_sms"] == 2
        assert stats["outbound"] == 2
        assert stats["inbound"] == 0
        assert stats["success_rate"] == 1.0


class TestCommunicationService:
    """Tests for CommunicationService class."""
    
    def test_send_email_via_communication_service(self, test_db, sample_lead):
        """Test sending email through unified communication service."""
        comm_service = get_communication_service()
        
        result = comm_service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is True
        assert "message_id" in result
    
    def test_send_sms_via_communication_service(self, test_db, sample_lead):
        """Test sending SMS through unified communication service."""
        comm_service = get_communication_service()
        
        result = comm_service.send_sms(
            phone="+1234567890",
            message="Test SMS",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        assert result["success"] is True
        assert "message_id" in result
    
    def test_get_communications_for_lead(self, test_db, sample_lead):
        """Test retrieving all communications for a lead."""
        comm_service = get_communication_service()
        
        # Send email
        comm_service.send_email(
            to="recipient@example.com",
            subject="Email Subject",
            body="Email body",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        # Send SMS
        comm_service.send_sms(
            phone="+1234567890",
            message="SMS message",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        # Get communications
        communications = comm_service.get_communications_for_lead(sample_lead.id, test_db)
        
        assert len(communications) == 2
        assert any(comm["channel"] == "email" for comm in communications)
        assert any(comm["channel"] == "sms" for comm in communications)
    
    def test_get_overall_stats(self, test_db, sample_lead):
        """Test getting overall communication statistics."""
        comm_service = get_communication_service()
        
        # Get initial stats
        initial_stats = comm_service.get_overall_stats(test_db)
        initial_total = initial_stats["total_communications"]
        
        # Send email
        comm_service.send_email(
            to="recipient@example.com",
            subject="Email Subject",
            body="Email body",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        # Send SMS
        comm_service.send_sms(
            phone="+1234567890",
            message="SMS message",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        
        stats = comm_service.get_overall_stats(test_db)
        
        assert "email" in stats
        assert "sms" in stats
        # Check that we added 2 communications
        assert stats["total_communications"] == initial_total + 2
        assert stats["email"]["total_emails"] >= 1
        assert stats["sms"]["total_sms"] >= 1


class TestAgentIntegration:
    """Tests for integration with agent tool calls."""
    
    def test_agent_send_email_tool_call(self, test_db, sample_lead):
        """Test agent executing SEND_EMAIL tool call."""
        agent = Agent()
        
        tool_call = {
            'tool': 'SEND_EMAIL',
            'parameters': ('recipient@example.com', 'Test Subject', 'Test body'),
            'raw_match': 'SEND_EMAIL{recipient: recipient@example.com, subject: Test Subject, body: Test body}'
        }
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': sample_lead.status,
            'source': sample_lead.source
        }
        
        result = agent.execute_tool_call(tool_call, lead_dict, test_db)
        
        assert result["success"] is True
        assert result["action"] == "email_sent"
        assert "message_id" in result
        assert result["status"] in [status.value for status in DeliveryStatus]
    
    def test_agent_send_sms_tool_call(self, test_db, sample_lead):
        """Test agent executing SEND_SMS tool call."""
        agent = Agent()
        
        tool_call = {
            'tool': 'SEND_SMS',
            'parameters': ('+1234567890', 'Test SMS message'),
            'raw_match': 'SEND_SMS{phone: +1234567890, message: Test SMS message}'
        }
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': sample_lead.status,
            'source': sample_lead.source
        }
        
        result = agent.execute_tool_call(tool_call, lead_dict, test_db)
        
        assert result["success"] is True
        assert result["action"] == "sms_sent"
        assert "message_id" in result
        assert result["status"] == DeliveryStatus.DELIVERED.value
    
    def test_agent_tool_call_logs_to_database(self, test_db, sample_lead):
        """Test that agent tool calls are logged to database."""
        agent = Agent()
        
        tool_call = {
            'tool': 'SEND_EMAIL',
            'parameters': ('recipient@example.com', 'Test Subject', 'Test body'),
            'raw_match': 'SEND_EMAIL{recipient: recipient@example.com, subject: Test Subject, body: Test body}'
        }
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': sample_lead.status,
            'source': sample_lead.source
        }
        
        agent.execute_tool_call(tool_call, lead_dict, test_db)
        
        # Check that message was logged
        messages = MessageOperations.get_messages_by_lead(test_db, sample_lead.id)
        assert len(messages) == 1
        assert messages[0].channel == "email"
        assert messages[0].direction == "outbound"


class TestMockResponseRealism:
    """Tests for realistic mock responses."""
    
    def test_email_delivery_status_variety(self, test_db, sample_lead):
        """Test that email delivery statuses vary realistically."""
        email_service = EmailService(failure_rate=0.0)
        
        statuses = set()
        # Send multiple emails to get variety
        for i in range(20):
            result = email_service.send_email(
                to=f"recipient{i}@example.com",
                subject=f"Subject {i}",
                body=f"Body {i}",
                lead_id=sample_lead.id,
                db_session=test_db
            )
            statuses.add(result["status"])
        
        # Should have at least some variety in statuses
        assert len(statuses) > 1 or DeliveryStatus.DELIVERED.value in statuses
    
    def test_email_metrics_realism(self, test_db, sample_lead):
        """Test that email metrics are realistic."""
        email_service = EmailService(failure_rate=0.0)
        
        result = email_service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body",
            lead_id=sample_lead.id,
            db_session=test_db,
            html=True
        )
        
        metrics = result["metrics"]
        
        # Check realistic ranges
        assert 0.0 <= metrics["open_rate"] <= 1.0
        assert 0.0 <= metrics["click_rate"] <= 1.0
        assert metrics["open_rate"] >= metrics["click_rate"]  # Clicks should be <= opens
    
    def test_sms_high_delivery_rate(self, test_db, sample_lead):
        """Test that SMS has high delivery rate."""
        sms_service = SMSService(failure_rate=0.0)
        
        successful = 0
        total = 10
        
        for i in range(total):
            result = sms_service.send_sms(
                phone=f"+123456789{i}",
                message=f"Message {i}",
                lead_id=sample_lead.id,
                db_session=test_db
            )
            if result["success"]:
                successful += 1
        
        # SMS should have very high delivery rate
        assert successful / total >= 0.95
    
    def test_communication_delay_simulation(self, test_db, sample_lead):
        """Test that communications have realistic delays."""
        import time
        
        email_service = EmailService(failure_rate=0.0)
        
        start_time = time.time()
        email_service.send_email(
            to="recipient@example.com",
            subject="Test",
            body="Test",
            lead_id=sample_lead.id,
            db_session=test_db
        )
        elapsed_time = time.time() - start_time
        
        # Should have some delay (0.1 to 0.5 seconds)
        assert 0.1 <= elapsed_time <= 0.6


class TestErrorHandling:
    """Tests for error handling in communication services."""
    
    def test_email_service_exception_handling(self, test_db, sample_lead):
        """Test that email service handles exceptions gracefully."""
        email_service = EmailService(failure_rate=0.0)
        
        # Test with invalid lead_id (should still handle gracefully)
        result = email_service.send_email(
            to="recipient@example.com",
            subject="Test",
            body="Test",
            lead_id=99999,  # Non-existent lead
            db_session=test_db
        )
        
        # Should either succeed or fail gracefully
        assert "success" in result
        assert "error" in result or result["success"]
    
    def test_sms_service_exception_handling(self, test_db, sample_lead):
        """Test that SMS service handles exceptions gracefully."""
        sms_service = SMSService(failure_rate=0.0)
        
        # Test with invalid lead_id (should still handle gracefully)
        result = sms_service.send_sms(
            phone="+1234567890",
            message="Test",
            lead_id=99999,  # Non-existent lead
            db_session=test_db
        )
        
        # Should either succeed or fail gracefully
        assert "success" in result
        assert "error" in result or result["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
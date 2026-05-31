"""
Communication module for Secu-Agent AI lead management system.
Provides mocked email and SMS services with realistic behavior and database logging.
"""

import random
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Mock delivery status for communications."""
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    PENDING = "pending"


class EmailService:
    """
    Mock email service with realistic behavior simulation.
    Logs all emails to database via Message model.
    """
    
    # Mock email templates
    TEMPLATES = {
        'welcome': "Welcome {name}! Thank you for your interest in Vigil.AI cybersecurity solutions.",
        'follow_up': "Hi {name}, following up on our previous conversation about cybersecurity.",
        'meeting_reminder': "Reminder: Meeting scheduled for {when}. See you there!",
        'info_request': "Hi {name}, we'd like to learn more about {field} to better assist you."
    }
    
    def __init__(self, failure_rate: float = 0.05):
        """
        Initialize email service.
        
        Args:
            failure_rate: Probability of email failure (0.0 to 1.0)
        """
        self.failure_rate = failure_rate
        self.logger = logging.getLogger(__name__)
    
    def send_email(self, to: str, subject: str, body: str, lead_id: int,
                   db_session, html: bool = False) -> Dict[str, Any]:
        """
        Send a mock email with realistic behavior.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            lead_id: Lead ID for database logging
            db_session: Database session
            html: Whether email is HTML format
            
        Returns:
            Dictionary with delivery status and metadata
        """
        try:
            # Simulate realistic delay
            time.sleep(random.uniform(0.1, 0.5))
            
            # Simulate occasional failures
            if random.random() < self.failure_rate:
                self.logger.warning(f"Email failed to send to {to}")
                return {
                    "success": False,
                    "status": DeliveryStatus.FAILED.value,
                    "error": "SMTP connection timeout",
                    "to": to,
                    "subject": subject,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Log email to database
            from database import MessageOperations
            
            # Create full email content for logging
            email_content = f"Subject: {subject}\n\n{body}"
            
            message = MessageOperations.create_message(
                db=db_session,
                lead_id=lead_id,
                message_text=email_content,
                channel="email",
                direction="outbound"
            )
            
            # Simulate realistic delivery timeline
            delivery_time = datetime.utcnow() + timedelta(seconds=random.randint(1, 10))
            
            # Simulate engagement metrics
            open_rate = random.uniform(0.4, 0.9)
            click_rate = random.uniform(0.1, 0.4) if html else 0.0
            
            # Determine final status
            if random.random() < 0.02:  # 2% bounce rate
                status = DeliveryStatus.BOUNCED.value
            elif click_rate > 0.2:
                status = DeliveryStatus.CLICKED.value
            elif open_rate > 0.6:
                status = DeliveryStatus.OPENED.value
            else:
                status = DeliveryStatus.DELIVERED.value
            
            result = {
                "success": True,
                "message_id": message.id,
                "status": status,
                "to": to,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat(),
                "delivery_time": delivery_time.isoformat(),
                "metrics": {
                    "open_rate": round(open_rate, 2),
                    "click_rate": round(click_rate, 2),
                    "html": html
                }
            }
            
            self.logger.info(f"Email sent successfully to {to} - Status: {status}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {to}: {str(e)}")
            return {
                "success": False,
                "status": DeliveryStatus.FAILED.value,
                "error": str(e),
                "to": to,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def send_template_email(self, template_name: str, to: str, lead_id: int,
                           db_session, **kwargs) -> Dict[str, Any]:
        """
        Send email using a predefined template.
        
        Args:
            template_name: Name of template to use
            to: Recipient email address
            lead_id: Lead ID for database logging
            db_session: Database session
            **kwargs: Template variables
            
        Returns:
            Dictionary with delivery status and metadata
        """
        if template_name not in self.TEMPLATES:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get template and fill in variables
        template = self.TEMPLATES[template_name]
        body = template.format(**kwargs)
        
        # Generate subject based on template
        subject_map = {
            'welcome': "Welcome to Vigil.AI",
            'follow_up': "Following up - Vigil.AI",
            'meeting_reminder': "Meeting Reminder",
            'info_request': "Information Request"
        }
        
        subject = subject_map.get(template_name, "Message from Vigil.AI")
        
        return self.send_email(to, subject, body, lead_id, db_session)
    
    def get_email_stats(self, db_session) -> Dict[str, Any]:
        """
        Get statistics about email communications.
        
        Args:
            db_session: Database session
            
        Returns:
            Dictionary with email statistics
        """
        try:
            from database import MessageOperations
            
            messages = MessageOperations.get_messages_by_channel(db_session, "email")
            
            total_emails = len(messages)
            if total_emails == 0:
                return {
                    "total_emails": 0,
                    "outbound": 0,
                    "inbound": 0,
                    "success_rate": 0.0
                }
            
            outbound = sum(1 for msg in messages if msg.direction == "outbound")
            inbound = sum(1 for msg in messages if msg.direction == "inbound")
            
            # Mock success rate based on our failure_rate
            success_rate = round(1.0 - self.failure_rate, 2)
            
            return {
                "total_emails": total_emails,
                "outbound": outbound,
                "inbound": inbound,
                "success_rate": success_rate,
                "failure_rate": round(self.failure_rate, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get email stats: {str(e)}")
            return {
                "total_emails": 0,
                "error": str(e)
            }


class SMSService:
    """
    Mock SMS service with realistic behavior simulation.
    Logs all SMS messages to database via Message model.
    """
    
    def __init__(self, failure_rate: float = 0.03):
        """
        Initialize SMS service.
        
        Args:
            failure_rate: Probability of SMS failure (0.0 to 1.0)
        """
        self.failure_rate = failure_rate
        self.logger = logging.getLogger(__name__)
    
    def send_sms(self, phone: str, message: str, lead_id: int,
                db_session) -> Dict[str, Any]:
        """
        Send a mock SMS with realistic behavior.
        
        Args:
            phone: Recipient phone number
            message: SMS message content (max 160 chars)
            lead_id: Lead ID for database logging
            db_session: Database session
            
        Returns:
            Dictionary with delivery status and metadata
        """
        try:
            # Validate phone number format (basic)
            if not self._validate_phone(phone):
                return {
                    "success": False,
                    "status": DeliveryStatus.FAILED.value,
                    "error": "Invalid phone number format",
                    "phone": phone,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Truncate message if too long
            if len(message) > 160:
                message = message[:157] + "..."
                self.logger.warning(f"SMS message truncated to 160 characters")
            
            # Simulate realistic delay
            time.sleep(random.uniform(0.05, 0.2))
            
            # Simulate occasional failures
            if random.random() < self.failure_rate:
                self.logger.warning(f"SMS failed to send to {phone}")
                return {
                    "success": False,
                    "status": DeliveryStatus.FAILED.value,
                    "error": "Network timeout",
                    "phone": phone,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Log SMS to database
            from database import MessageOperations
            
            sms_content = f"[SMS to {phone}]\n{message}"
            
            message_record = MessageOperations.create_message(
                db=db_session,
                lead_id=lead_id,
                message_text=sms_content,
                channel="sms",
                direction="outbound"
            )
            
            # Simulate delivery timeline
            delivery_time = datetime.utcnow() + timedelta(seconds=random.randint(1, 5))
            
            # SMS typically has high delivery rate
            status = DeliveryStatus.DELIVERED.value
            
            result = {
                "success": True,
                "message_id": message_record.id,
                "status": status,
                "phone": phone,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "delivery_time": delivery_time.isoformat(),
                "character_count": len(message),
                "segments": 1 if len(message) <= 160 else 2
            }
            
            self.logger.info(f"SMS sent successfully to {phone}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send SMS to {phone}: {str(e)}")
            return {
                "success": False,
                "status": DeliveryStatus.FAILED.value,
                "error": str(e),
                "phone": phone,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _validate_phone(self, phone: str) -> bool:
        """
        Basic phone number validation.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Remove common separators and plus sign
        cleaned = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
        
        # Check if it's mostly digits and reasonable length
        return cleaned.isdigit() and 10 <= len(cleaned) <= 15
    
    def get_sms_stats(self, db_session) -> Dict[str, Any]:
        """
        Get statistics about SMS communications.
        
        Args:
            db_session: Database session
            
        Returns:
            Dictionary with SMS statistics
        """
        try:
            from database import MessageOperations
            
            messages = MessageOperations.get_messages_by_channel(db_session, "sms")
            
            total_sms = len(messages)
            if total_sms == 0:
                return {
                    "total_sms": 0,
                    "outbound": 0,
                    "inbound": 0,
                    "success_rate": 0.0
                }
            
            outbound = sum(1 for msg in messages if msg.direction == "outbound")
            inbound = sum(1 for msg in messages if msg.direction == "inbound")
            
            # Mock success rate based on our failure_rate
            success_rate = round(1.0 - self.failure_rate, 2)
            
            return {
                "total_sms": total_sms,
                "outbound": outbound,
                "inbound": inbound,
                "success_rate": success_rate,
                "failure_rate": round(self.failure_rate, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get SMS stats: {str(e)}")
            return {
                "total_sms": 0,
                "error": str(e)
            }


class CommunicationService:
    """
    Unified communication service that manages both email and SMS.
    Provides a single interface for all communication operations.
    """
    
    def __init__(self, email_failure_rate: float = 0.05, sms_failure_rate: float = 0.03):
        """
        Initialize unified communication service.
        
        Args:
            email_failure_rate: Email failure rate
            sms_failure_rate: SMS failure rate
        """
        self.email_service = EmailService(failure_rate=email_failure_rate)
        self.sms_service = SMSService(failure_rate=sms_failure_rate)
        self.logger = logging.getLogger(__name__)
    
    def send_email(self, to: str, subject: str, body: str, lead_id: int,
                   db_session, html: bool = False) -> Dict[str, Any]:
        """Send email via email service."""
        return self.email_service.send_email(to, subject, body, lead_id, db_session, html)
    
    def send_sms(self, phone: str, message: str, lead_id: int,
                db_session) -> Dict[str, Any]:
        """Send SMS via SMS service."""
        return self.sms_service.send_sms(phone, message, lead_id, db_session)
    
    def send_template_email(self, template_name: str, to: str, lead_id: int,
                           db_session, **kwargs) -> Dict[str, Any]:
        """Send template email via email service."""
        return self.email_service.send_template_email(template_name, to, lead_id, db_session, **kwargs)
    
    def get_communications_for_lead(self, lead_id: int, db_session) -> List[Dict[str, Any]]:
        """
        Get all communications for a specific lead.
        
        Args:
            lead_id: Lead ID
            db_session: Database session
            
        Returns:
            List of communication dictionaries
        """
        try:
            from database import MessageOperations
            
            messages = MessageOperations.get_messages_by_lead(db_session, lead_id)
            
            return [
                {
                    "id": msg.id,
                    "lead_id": msg.lead_id,
                    "message_text": msg.message_text,
                    "channel": msg.channel,
                    "direction": msg.direction,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get communications for lead {lead_id}: {str(e)}")
            return []
    
    def get_overall_stats(self, db_session) -> Dict[str, Any]:
        """
        Get overall communication statistics.
        
        Args:
            db_session: Database session
            
        Returns:
            Dictionary with combined statistics
        """
        email_stats = self.email_service.get_email_stats(db_session)
        sms_stats = self.sms_service.get_sms_stats(db_session)
        
        return {
            "email": email_stats,
            "sms": sms_stats,
            "total_communications": email_stats.get("total_emails", 0) + sms_stats.get("total_sms", 0)
        }


# Convenience function to get communication service
def get_communication_service(email_failure_rate: float = 0.05, 
                             sms_failure_rate: float = 0.03) -> CommunicationService:
    """
    Get a communication service instance.
    
    Args:
        email_failure_rate: Email failure rate
        sms_failure_rate: SMS failure rate
        
    Returns:
        CommunicationService instance
    """
    return CommunicationService(email_failure_rate, sms_failure_rate)
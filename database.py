"""
Database module for Secu-Agent AI lead management system.
Contains all database-related functionality: models, connection, and configuration.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, text, event
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from typing import Optional, List
import os

# Database Configuration
DATABASE_URL = "sqlite:///vigil_agent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class Lead(Base):
    """
    Lead model for managing potential customers.
    Represents a lead captured from various sources.
    """
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    source = Column(String(100), nullable=False)  # e.g., "event", "website", "referral"
    status = Column(String(50), nullable=False, default="new")  # e.g., "new", "contacted", "qualified", "meeting_scheduled", "converted", "lost"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with messages
    messages = relationship("Message", back_populates="lead", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.name}', email='{self.email}', status='{self.status}')>"


class Message(Base):
    """
    Message model for tracking communications with leads.
    Stores all messages sent/received through various channels.
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    message_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    channel = Column(String(50), nullable=False)  # e.g., "email", "whatsapp", "linkedin", "phone"
    direction = Column(String(20), nullable=False)  # e.g., "outbound", "inbound"
    
    # Relationship with lead
    lead = relationship("Lead", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, lead_id={self.lead_id}, channel='{self.channel}', direction='{self.direction}')>"


# Database Session Management
def get_db():
    """
    Dependency function to get database session.
    Used with FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Call this on application startup.
    """
    Base.metadata.create_all(bind=engine)


# Database Operations (CRUD Helper Functions)
class LeadOperations:
    """Helper class for Lead CRUD operations."""
    
    @staticmethod
    def create_lead(db: SessionLocal, name: str, email: str, company: Optional[str] = None, 
                   job_title: Optional[str] = None, source: str = "event", 
                   status: str = "new") -> Lead:
        """Create a new lead."""
        lead = Lead(
            name=name,
            email=email,
            company=company,
            job_title=job_title,
            source=source,
            status=status
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead
    
    @staticmethod
    def get_lead(db: SessionLocal, lead_id: int) -> Optional[Lead]:
        """Get a lead by ID."""
        return db.query(Lead).filter(Lead.id == lead_id).first()
    
    @staticmethod
    def get_lead_by_email(db: SessionLocal, email: str) -> Optional[Lead]:
        """Get a lead by email."""
        return db.query(Lead).filter(Lead.email == email).first()
    
    @staticmethod
    def get_all_leads(db: SessionLocal, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get all leads with pagination."""
        return db.query(Lead).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_leads_by_status(db: SessionLocal, status: str) -> List[Lead]:
        """Get leads filtered by status."""
        return db.query(Lead).filter(Lead.status == status).all()
    
    @staticmethod
    def update_lead_status(db: SessionLocal, lead_id: int, new_status: str) -> Optional[Lead]:
        """Update lead status."""
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            lead.status = new_status
            lead.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(lead)
        return lead
    
    @staticmethod
    def delete_lead(db: SessionLocal, lead_id: int) -> bool:
        """Delete a lead."""
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            db.delete(lead)
            db.commit()
            return True
        return False


class MessageOperations:
    """Helper class for Message CRUD operations."""
    
    @staticmethod
    def create_message(db: SessionLocal, lead_id: int, message_text: str, 
                      channel: str = "email", direction: str = "outbound") -> Message:
        """Create a new message."""
        message = Message(
            lead_id=lead_id,
            message_text=message_text,
            channel=channel,
            direction=direction
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_message(db: SessionLocal, message_id: int) -> Optional[Message]:
        """Get a message by ID."""
        return db.query(Message).filter(Message.id == message_id).first()
    
    @staticmethod
    def get_messages_by_lead(db: SessionLocal, lead_id: int) -> List[Message]:
        """Get all messages for a specific lead."""
        return db.query(Message).filter(Message.lead_id == lead_id).all()
    
    @staticmethod
    def get_messages_by_channel(db: SessionLocal, channel: str) -> List[Message]:
        """Get all messages for a specific channel."""
        return db.query(Message).filter(Message.channel == channel).all()
    
    @staticmethod
    def delete_message(db: SessionLocal, message_id: int) -> bool:
        """Delete a message."""
        message = db.query(Message).filter(Message.id == message_id).first()
        if message:
            db.delete(message)
            db.commit()
            return True
        return False


# Database Health Check
def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False
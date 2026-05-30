"""
Main application entry point for Secu-Agent AI lead management system.
FastAPI application with database integration.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uvicorn

# Import database components
from database import (
    get_db, init_db, check_db_connection,
    Lead, Message,
    LeadOperations, MessageOperations
)

# Import AI client and Agent
from ai_client import Agent

# Initialize FastAPI app
app = FastAPI(
    title="Secu-Agent AI Lead Management System",
    description="AI-powered lead management for Vigil.AI cybersecurity events",
    version="1.0.0"
)


# Startup event - Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()
    print("✓ Database initialized successfully")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify API and database status."""
    db_status = check_db_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Secu-Agent AI Lead Management System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "leads": "/leads",
            "messages": "/messages"
        }
    }


# Lead endpoints
@app.post("/leads", response_model=dict)
async def create_lead(
    name: str,
    email: str,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    source: str = "event",
    status: str = "new",
    db: Session = Depends(get_db)
):
    """Create a new lead."""
    try:
        lead = LeadOperations.create_lead(
            db=db,
            name=name,
            email=email,
            company=company,
            job_title=job_title,
            source=source,
            status=status
        )
        return {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "job_title": lead.job_title,
            "source": lead.source,
            "status": lead.status,
            "created_at": lead.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/leads/capture", response_model=dict)
async def capture_lead(
    name: str,
    email: str,
    company: str,
    job_title: str,
    source: str = "event",
    db: Session = Depends(get_db)
):
    """
    Capture a new lead with validation, enrichment, and automated agent processing.
    
    This endpoint:
    - Validates required fields (name, email, company, job_title)
    - Auto-enriches lead data with mock information
    - Creates lead in database
    - Triggers agent processing for welcome message and initial engagement
    - Returns lead ID and initial status
    """
    try:
        # Validate required fields
        if not name or not email or not company or not job_title:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: name, email, company, job_title are required"
            )
        
        # Basic email validation
        if "@" not in email or "." not in email:
            raise HTTPException(
                status_code=400,
                detail="Invalid email format"
            )
        
        # Check if lead already exists
        existing_lead = LeadOperations.get_lead_by_email(db, email)
        if existing_lead:
            raise HTTPException(
                status_code=409,
                detail=f"Lead with email {email} already exists"
            )
        
        # Create lead data dictionary
        lead_data = {
            "name": name,
            "email": email,
            "company": company,
            "job_title": job_title,
            "source": source
        }
        
        # Auto-enrich lead data
        agent = Agent()
        enriched_data = agent.enrich_lead_data(lead_data)
        
        # Create lead in database
        lead = LeadOperations.create_lead(
            db=db,
            name=enriched_data["name"],
            email=enriched_data["email"],
            company=enriched_data["company"],
            job_title=enriched_data["job_title"],
            source=enriched_data["source"],
            status="new"
        )
        
        # Refresh to get actual ID value
        db.refresh(lead)
        
        # Trigger agent processing
        processing_result = agent.process_lead(lead.id, db)
        
        # Return comprehensive response
        return {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "job_title": lead.job_title,
            "source": lead.source,
            "status": lead.status,
            "enrichment": {
                "company_size": enriched_data.get("company_size"),
                "industry": enriched_data.get("industry"),
                "enriched_at": enriched_data.get("enriched_at")
            },
            "agent_processing": processing_result,
            "created_at": lead.created_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lead capture failed: {str(e)}")


@app.get("/leads/{lead_id}", response_model=dict)
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a specific lead by ID."""
    lead = LeadOperations.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "company": lead.company,
        "job_title": lead.job_title,
        "source": lead.source,
        "status": lead.status,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat()
    }


@app.get("/leads", response_model=List[dict])
async def get_leads(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all leads with optional filtering."""
    if status:
        leads = LeadOperations.get_leads_by_status(db, status)
    else:
        leads = LeadOperations.get_all_leads(db, skip=skip, limit=limit)
    
    return [
        {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "job_title": lead.job_title,
            "source": lead.source,
            "status": lead.status,
            "created_at": lead.created_at.isoformat()
        }
        for lead in leads
    ]


@app.put("/leads/{lead_id}/status", response_model=dict)
async def update_lead_status(
    lead_id: int,
    new_status: str,
    db: Session = Depends(get_db)
):
    """Update lead status."""
    lead = LeadOperations.update_lead_status(db, lead_id, new_status)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "status": lead.status,
        "updated_at": lead.updated_at.isoformat()
    }


@app.delete("/leads/{lead_id}", response_model=dict)
async def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Delete a lead."""
    success = LeadOperations.delete_lead(db, lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted successfully", "id": lead_id}


# Message endpoints
@app.post("/messages", response_model=dict)
async def create_message(
    lead_id: int,
    message_text: str,
    channel: str = "email",
    direction: str = "outbound",
    db: Session = Depends(get_db)
):
    """Create a new message for a lead."""
    try:
        # Verify lead exists
        lead = LeadOperations.get_lead(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        message = MessageOperations.create_message(
            db=db,
            lead_id=lead_id,
            message_text=message_text,
            channel=channel,
            direction=direction
        )
        
        return {
            "id": message.id,
            "lead_id": message.lead_id,
            "message_text": message.message_text,
            "channel": message.channel,
            "direction": message.direction,
            "timestamp": message.timestamp.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/messages/{message_id}", response_model=dict)
async def get_message(message_id: int, db: Session = Depends(get_db)):
    """Get a specific message by ID."""
    message = MessageOperations.get_message(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {
        "id": message.id,
        "lead_id": message.lead_id,
        "message_text": message.message_text,
        "channel": message.channel,
        "direction": message.direction,
        "timestamp": message.timestamp.isoformat()
    }


@app.get("/leads/{lead_id}/messages", response_model=List[dict])
async def get_lead_messages(lead_id: int, db: Session = Depends(get_db)):
    """Get all messages for a specific lead."""
    # Verify lead exists
    lead = LeadOperations.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    messages = MessageOperations.get_messages_by_lead(db, lead_id)
    
    return [
        {
            "id": message.id,
            "lead_id": message.lead_id,
            "message_text": message.message_text,
            "channel": message.channel,
            "direction": message.direction,
            "timestamp": message.timestamp.isoformat()
        }
        for message in messages
    ]


@app.delete("/messages/{message_id}", response_model=dict)
async def delete_message(message_id: int, db: Session = Depends(get_db)):
    """Delete a message."""
    success = MessageOperations.delete_message(db, message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Message deleted successfully", "id": message_id}


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Run the application
if __name__ == "__main__":
    print("Starting Secu-Agent AI Lead Management System...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
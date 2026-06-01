"""
Main application entry point for Secu-Agent AI lead management system.
FastAPI application with database integration and security features.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
import uvicorn
import webbrowser
import os
import platform

# Import database components
from database import (
    get_db, init_db, check_db_connection,
    Lead, Message,
    LeadOperations, MessageOperations
)

# Import AI client and Agent
from ai_client import Agent, EngagementRules

# Import communication services
from communication import get_communication_service

# Import security components
from security import (
    rate_limit, APIKeyManager, check_abuse, get_client_ip,
    _abuse_detector
)

# Pydantic models for request validation
class LeadCaptureRequest(BaseModel):
    name: str
    email: str
    company: str
    job_title: str
    source: str = "event"

class LeadCreateRequest(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    source: str = "event"
    status: str = "new"

class MessageCreateRequest(BaseModel):
    lead_id: int
    message_text: str
    channel: str = "email"
    direction: str = "outbound"

class StatusUpdateRequest(BaseModel):
    new_status: str

# Initialize FastAPI app
app = FastAPI(
    title="Secu-Agent AI Lead Management System",
    description="AI-powered lead management for Vigil.AI cybersecurity events",
    version="1.0.0"
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


# Startup event - Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup with migration support."""
    try:
        # Run database migration
        import migrate_db
        migration_success = migrate_db.migrate_database()
        
        if migration_success:
            print("✓ Database migration completed successfully")
        else:
            print("⚠️  Database migration had issues, but continuing...")
    except Exception as e:
        print(f"⚠️  Database migration warning: {str(e)}")
        # Fallback to basic initialization
        init_db()
        print("✓ Database initialized (fallback mode)")


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


# Landing page route
@app.get("/")
async def landing_page():
    """Serve the landing page."""
    return FileResponse('static/index.html')

# Dashboard route
@app.get("/dashboard")
async def dashboard_page():
    """Serve the dashboard page."""
    return FileResponse('static/dashboard.html')

# API info endpoint
@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Secu-Agent AI Lead Management System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "leads": "/leads",
            "messages": "/messages",
            "landing": "/",
            "dashboard": "/dashboard"
        }
    }


# Lead endpoints
@app.post("/leads", response_model=dict)
async def create_lead(
    request: LeadCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new lead."""
    try:
        lead = LeadOperations.create_lead(
            db=db,
            name=request.name,
            email=request.email,
            company=request.company,
            job_title=request.job_title,
            source=request.source,
            status=request.status
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
@rate_limit(max_requests=10, window_seconds=60)
async def capture_lead(
    request: Request,
    lead_request: LeadCaptureRequest,
    db: Session = Depends(get_db)
):
    """
    Capture a new lead with validation, enrichment, and automated agent processing.
    
    Rate limited to 10 requests per minute per IP to prevent abuse.
    
    This endpoint:
    - Validates required fields (name, email, company, job_title)
    - Auto-enriches lead data with mock information
    - Creates lead in database
    - Triggers agent processing for welcome message and initial engagement
    - Returns lead ID and initial status
    """
    try:
        # Validate required fields
        if not lead_request.name or not lead_request.email or not lead_request.company or not lead_request.job_title:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: name, email, company, job_title are required"
            )
        
        # Basic email validation
        if "@" not in lead_request.email or "." not in lead_request.email:
            raise HTTPException(
                status_code=400,
                detail="Invalid email format"
            )
        
        # Check if lead already exists
        existing_lead = LeadOperations.get_lead_by_email(db, lead_request.email)
        if existing_lead:
            raise HTTPException(
                status_code=409,
                detail=f"Lead with email {lead_request.email} already exists"
            )
        
        # Create lead data dictionary
        lead_data = {
            "name": lead_request.name,
            "email": lead_request.email,
            "company": lead_request.company,
            "job_title": lead_request.job_title,
            "source": lead_request.source
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
        
        # Check for abuse patterns (3-4 AI calls per lead capture)
        abuse_reason = check_abuse(request, ai_calls=4, leads_created=1)
        if abuse_reason:
            raise HTTPException(
                status_code=429,
                detail=f"Suspicious activity detected: {abuse_reason}"
            )
        
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
    request: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update lead status."""
    lead = LeadOperations.update_lead_status(db, lead_id, request.new_status)
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
    request: MessageCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new message for a lead."""
    try:
        # Verify lead exists
        lead = LeadOperations.get_lead(db, request.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        message = MessageOperations.create_message(
            db=db,
            lead_id=request.lead_id,
            message_text=request.message_text,
            channel=request.channel,
            direction=request.direction
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


# Communication endpoints
@app.get("/api/communications/{lead_id}", response_model=List[dict])
async def get_communications_for_lead(lead_id: int, db: Session = Depends(get_db)):
    """
    Get all communications for a specific lead.
    Includes both email and SMS messages.
    """
    # Verify lead exists
    lead = LeadOperations.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get communications via communication service
    comm_service = get_communication_service()
    communications = comm_service.get_communications_for_lead(lead_id, db)
    
    return communications


@app.post("/api/communications/test", response_model=dict)
@rate_limit(max_requests=5, window_seconds=60)
async def test_communication_service(
    request: Request,
    lead_id: int,
    channel: str = "email",
    db: Session = Depends(get_db)
):
    """
    Test communication service by sending a test message.
    Rate limited to 5 requests per minute per IP.
    
    Args:
        lead_id: Lead ID to send test message to
        channel: Communication channel (email or sms)
        db: Database session
    """
    # Verify lead exists
    lead = LeadOperations.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    comm_service = get_communication_service()
    
    if channel == "email":
        result = comm_service.send_email(
            to=lead.email,
            subject="Test Email from Secu-Agent",
            body="This is a test email from the Secu-Agent communication system.",
            lead_id=lead_id,
            db_session=db
        )
    elif channel == "sms":
        # Use a mock phone number for testing
        result = comm_service.send_sms(
            phone="+1234567890",
            message="This is a test SMS from the Secu-Agent communication system.",
            lead_id=lead_id,
            db_session=db
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel: {channel}. Must be 'email' or 'sms'"
        )
    
    return {
        "lead_id": lead_id,
        "channel": channel,
        "test_result": result,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/communications/stats", response_model=dict)
async def get_communication_stats(db: Session = Depends(get_db)):
    """
    Get overall communication statistics.
    Includes both email and SMS metrics.
    """
    comm_service = get_communication_service()
    stats = comm_service.get_overall_stats(db)
    
    return {
        "statistics": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


# Engagement Rules endpoints
@app.get("/api/rules", response_model=dict)
async def get_engagement_rules():
    """
    Get all engagement rules with their metadata.
    Returns information about all registered engagement rules.
    """
    try:
        # Create engagement rules instance
        rules_engine = EngagementRules()
        rules = rules_engine.get_all_rules()
        
        return {
            "total_rules": len(rules),
            "event_date": rules_engine.event_date.isoformat(),
            "rules": rules,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get engagement rules: {str(e)}")


@app.post("/api/rules/evaluate/{lead_id}", response_model=dict)
@rate_limit(max_requests=30, window_seconds=60)
async def evaluate_rules_for_lead(
    request: Request,
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    Evaluate and execute engagement rules for a specific lead.
    Rate limited to 30 requests per minute per IP.
    
    This endpoint:
    - Retrieves the lead from database
    - Calculates engagement score and context
    - Evaluates all applicable engagement rules
    - Executes matching rules and returns results
    """
    try:
        # Get lead from database
        lead = LeadOperations.get_lead(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Create lead dictionary
        lead_dict = {
            'id': lead.id,
            'name': lead.name,
            'email': lead.email,
            'company': lead.company,
            'job_title': lead.job_title,
            'status': lead.status,
            'source': lead.source
        }
        
        # Create engagement rules engine and agent
        rules_engine = EngagementRules()
        agent = Agent()
        
        # Calculate engagement score
        engagement_score = rules_engine.get_engagement_score(lead_dict, db)
        
        # Build context for rule evaluation
        context = {
            'engagement_score': engagement_score,
            'event_date': rules_engine.event_date,
            'sessions_attended': [],  # Could be populated from database
            'last_email_opened': None,  # Could be populated from tracking
            'last_contact_date': lead.updated_at
        }
        
        # Evaluate and execute rules
        results = rules_engine.evaluate_rules_for_lead(lead_dict, context, agent, db)
        
        # Check for abuse (2-3 AI calls per evaluation)
        abuse_reason = check_abuse(request, ai_calls=3)
        if abuse_reason:
            raise HTTPException(
                status_code=429,
                detail=f"Suspicious activity detected: {abuse_reason}"
            )
        
        return {
            "lead_id": lead_id,
            "lead_name": lead.name,
            "lead_status": lead.status,
            "engagement_score": engagement_score,
            "rules_evaluated": len(rules_engine.rules),
            "rules_matched": len(results),
            "execution_results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate rules: {str(e)}")


@app.post("/api/rules/process-all", response_model=dict)
@rate_limit(max_requests=1, window_seconds=60)
async def process_rules_for_all_leads(
    request: Request,
    api_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Process engagement rules for all leads in the database.
    
    ⚠️  RESTRICTED ENDPOINT - Requires API key authentication
    Rate limited to 1 request per minute per IP
    
    This endpoint:
    - Retrieves all leads from database
    - Evaluates engagement rules for each lead
    - Executes applicable rules
    - Returns summary of processing results
    
    Headers:
        api-key: Admin API key (required)
    """
    # Require API key for this dangerous endpoint
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide 'api-key' header. This is a restricted endpoint."
        )
    
    if not APIKeyManager.validate_key(api_key, required_level="admin"):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key. Access denied."
        )
    
    try:
        # Get all leads
        leads = LeadOperations.get_all_leads(db)
        
        if not leads:
            return {
                "total_leads": 0,
                "processed": 0,
                "rules_matched": 0,
                "message": "No leads found in database",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Create engagement rules engine and agent
        rules_engine = EngagementRules()
        agent = Agent()
        
        # Process each lead
        total_matched = 0
        processing_results = []
        total_ai_calls = 0
        
        for lead in leads:
            lead_dict = {
                'id': lead.id,
                'name': lead.name,
                'email': lead.email,
                'company': lead.company,
                'job_title': lead.job_title,
                'status': lead.status,
                'source': lead.source
            }
            
            # Calculate engagement score
            engagement_score = rules_engine.get_engagement_score(lead_dict, db)
            total_ai_calls += 1
            
            # Build context
            context = {
                'engagement_score': engagement_score,
                'event_date': rules_engine.event_date,
                'sessions_attended': [],
                'last_email_opened': None,
                'last_contact_date': lead.updated_at
            }
            
            # Evaluate rules
            results = rules_engine.evaluate_rules_for_lead(lead_dict, context, agent, db)
            total_ai_calls += len(results)
            
            if results:
                total_matched += len(results)
                processing_results.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "lead_status": lead.status,
                    "engagement_score": engagement_score,
                    "rules_matched": len(results),
                    "results": results
                })
        
        # Check for abuse (this endpoint makes many AI calls)
        abuse_reason = check_abuse(request, ai_calls=total_ai_calls)
        if abuse_reason:
            raise HTTPException(
                status_code=429,
                detail=f"Suspicious activity detected: {abuse_reason}"
            )
        
        return {
            "total_leads": len(leads),
            "processed": len(leads),
            "total_rules_matched": total_matched,
            "leads_with_matches": len(processing_results),
            "total_ai_calls": total_ai_calls,
            "processing_results": processing_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process rules for all leads: {str(e)}")


@app.get("/api/rules/schedule", response_model=dict)
async def get_upcoming_scheduled_actions(db: Session = Depends(get_db)):
    """
    Get upcoming scheduled actions based on time-based engagement rules.
    
    This endpoint:
    - Retrieves all leads from database
    - Predicts when time-based rules will trigger
    - Returns sorted list of upcoming actions
    """
    try:
        # Get all leads
        leads = LeadOperations.get_all_leads(db)
        
        if not leads:
            return {
                "total_leads": 0,
                "upcoming_actions": [],
                "message": "No leads found in database",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Create engagement rules engine
        rules_engine = EngagementRules()
        
        # Convert leads to dictionaries
        leads_dicts = [
            {
                'id': lead.id,
                'name': lead.name,
                'email': lead.email,
                'company': lead.company,
                'job_title': lead.job_title,
                'status': lead.status,
                'source': lead.source
            }
            for lead in leads
        ]
        
        # Build context
        context = {
            'event_date': rules_engine.event_date
        }
        
        # Get upcoming actions
        upcoming_actions = rules_engine.get_upcoming_actions(leads_dicts, context)
        
        return {
            "total_leads": len(leads),
            "upcoming_actions_count": len(upcoming_actions),
            "event_date": rules_engine.event_date.isoformat(),
            "upcoming_actions": upcoming_actions,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upcoming schedule: {str(e)}")


@app.post("/api/rules/event-date", response_model=dict)
async def update_event_date(request: dict):
    """
    Update the event date for time-based engagement rules.
    
    Args:
        request: Dictionary with 'event_date' in ISO format
    """
    try:
        event_date_str = request.get('event_date')
        if not event_date_str:
            raise HTTPException(status_code=400, detail="event_date is required")
        
        # Parse and validate date
        from datetime import datetime as dt
        event_date = dt.fromisoformat(event_date_str)
        
        # Update global event date (in real app, would persist to database)
        return {
            "success": True,
            "event_date": event_date.isoformat(),
            "message": "Event date updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update event date: {str(e)}")


# Admin endpoints for monitoring abuse
@app.get("/api/admin/abuse-metrics")
async def get_abuse_metrics(api_key: str = Header(None)):
    """
    Get abuse detection metrics (admin only).
    
    Headers:
        api-key: Admin API key (required)
    """
    if not api_key or not APIKeyManager.validate_key(api_key, required_level="admin"):
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    
    # Return metrics for all tracked IPs
    metrics = {}
    for ip in list(_abuse_detector.ip_metrics.keys()):
        is_suspicious, reason = _abuse_detector.is_suspicious(ip)
        metrics[ip] = {
            **_abuse_detector.get_metrics(ip),
            "is_suspicious": is_suspicious,
            "reason": reason if is_suspicious else None
        }
    
    return {
        "total_tracked_ips": len(metrics),
        "suspicious_ips": sum(1 for m in metrics.values() if m["is_suspicious"]),
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))


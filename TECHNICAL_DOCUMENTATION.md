# Secu-Agent - Technical Documentation

## Executive Summary

Secu-Agent is an AI-powered lead management system designed for Vigil.AI's cybersecurity events. The system automates the complete lead lifecycle from capture to conversion, addressing three critical challenges: lead qualification, no-show reduction, and personalized follow-up. This document provides comprehensive technical documentation for implementation, deployment, and maintenance.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Database Schema](#database-schema)
4. [API Documentation](#api-documentation)
5. [Business Rules & Engagement Logic](#business-rules--engagement-logic)
6. [Data Strategy & Personalization](#data-strategy--personalization)
7. [Strategic Decisions & Rationale](#strategic-decisions--rationale)
8. [Implementation Plan](#implementation-plan)
9. [Deployment Instructions](#deployment-instructions)
10. [Testing Strategy](#testing-strategy)
11. [Security & Compliance](#security--compliance)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SECU-AGENT ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   FRONTEND   │────▶│   FASTAPI    │────▶│   DATABASE   │     │   AI/LLM     │
│              │     │   BACKEND    │     │   (SQLite)   │     │   SERVICE    │
│  Alpine.js   │     │              │     │              │     │              │
│  TailwindCSS │     │  • REST API  │     │  • Leads     │     │  • ArliAI    │
│  Landing Page│     │  • Agent     │     │  • Messages  │     │  • Anthropic │
│  Dashboard   │     │  • Rules     │     │  • Relations │     │  • OpenAI    │
└──────────────┘     └──────┬───────┘     └──────────────┘     └──────┬───────┘
                            │                                          │
                            │         ┌──────────────┐                  │
                            └────────▶│ RATE LIMITER │◀─────────────────┘
                                      │   SYSTEM     │
                                      │              │
                                      │  • Semaphore │
                                      │  • Priority  │
                                      │  • Cooldown  │
                                      │  • Scheduling│
                                      └──────┬───────┘
                                             │
                                             ▼
                                      ┌──────────────┐
                                      │ COMMUNICATION│
                                      │   SERVICE    │
                                      │              │
                                      │  • Email     │
                                      │  • SMS       │
                                      │  • Logging   │
                                      └──────────────┘
```

### Data Flow

```
1. LEAD CAPTURE FLOW:
   Landing Page → API Endpoint → Validation → Enrichment → Database → Agent Processing → Welcome Message

2. ENGAGEMENT FLOW:
   Scheduled Rules → Rule Evaluation → Context Building → AI Decision → Tool Execution → Communication → Database Logging

3. FOLLOW-UP FLOW:
   Event Completion → Status Update → Post-Event Rules → Personalized Content → Meeting Request → Conversion Tracking
```

### Component Interactions

**Frontend Layer:**
- Alpine.js for reactive UI components
- TailwindCSS for responsive design
- Real-time form validation
- AJAX API communication

**Backend Layer:**
- FastAPI for REST API endpoints
- SQLAlchemy ORM for database operations
- Agent class for AI-powered decision making
- Engagement rules engine for automated workflows

**Data Layer:**
- SQLite database with foreign key constraints
- Lead and Message models with relationships
- Automatic timestamp tracking
- Session management with dependency injection

**AI Layer:**
- ArliAI integration (OpenAI-compatible)
- Anthropic API support
- Flexible LLM dispatcher
- Tool calling capabilities

**Communication Layer:**
- Mocked email service with realistic behavior
- Mocked SMS service with delivery simulation
- Database logging for all communications
- Template-based messaging

**Rate Limiting Layer:**
- Global semaphore for AI request management
- Priority scheduling system (immediate vs scheduled)
- Off-peak processing (2am-6am BRT)
- Cooldown system for error recovery
- Enhanced logging with BRT timestamps
- Thread-safe concurrent access protection

---

## Technology Stack

### Backend Technologies

#### FastAPI Framework
**Choice Rationale:**
- High performance with async support
- Automatic API documentation (Swagger/OpenAPI)
- Built-in data validation with Pydantic
- Type hints for better code quality
- Easy dependency injection
- Growing ecosystem and community

**Implementation:**
```python
app = FastAPI(
    title="Secu-Agent AI Lead Management System",
    description="AI-powered lead management for Vigil.AI cybersecurity events",
    version="1.0.0"
)
```

#### SQLAlchemy ORM
**Choice Rationale:**
- Powerful ORM with support for multiple databases
- Clean separation between database and business logic
- Automatic schema generation
- Relationship management
- Migration support (Alembic ready)

**Implementation:**
```python
Base = declarative_base()
class Lead(Base):
    __tablename__ = "leads"
    # Model definition
```

#### SQLite Database
**Choice Rationale:**
- Zero configuration and setup
- Single file deployment
- Adequate performance for event-scale data (120 leads)
- Easy backup and migration
- No external dependencies
- Clear migration path to PostgreSQL if needed

**Migration Strategy:**
- Export data using SQLite `.dump` command
- Import to PostgreSQL using `psql`
- Update connection string in configuration
- No code changes required

### AI/LLM Technologies

#### ArliAI (Primary)
**Choice Rationale:**
- OpenAI-compatible API
- Multiple model options (21 available)
- Cost-effective alternative
- Good performance for business use cases
- Reliable uptime

**Configuration:**
```python
API_KEY = config['API_KEY']
BASE_URL = config['BASE_URL']
LLM_MODEL = 'Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled'
```

#### Anthropic Claude (Secondary)
**Choice Rationale:**
- Superior reasoning capabilities
- Better for complex decision-making
- Preferred by case requirements
- Used via flexible dispatcher

**Implementation:**
```python
def call_llm(system_prompt: str, user_message: str, history: List[Dict]) -> str:
    if LLM_PROVIDER == "anthropic":
        # Anthropic-specific implementation
```

### Frontend Technologies

#### Alpine.js
**Choice Rationale:**
- Lightweight (15KB gzipped)
- Reactive data binding
- No build step required
- Easy to learn and maintain
- Perfect for single-page applications

**Usage:**
```javascript
function leadCaptureApp() {
    return {
        form: { name: '', email: '', company: '', job_title: '' },
        submitForm() { /* ... */ }
    }
}
```

#### TailwindCSS (CDN)
**Choice Rationale:**
- Rapid UI development
- Consistent design system
- Responsive design utilities
- No build step for CDN version
- Custom theme configuration

**Custom Theme:**
```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                cyber: {
                    dark: '#0a0e27',
                    blue: '#1a1f3a',
                    accent: '#00d4ff',
                    purple: '#7c3aed',
                    green: '#10b981',
                    red: '#ef4444'
                }
            }
        }
    }
}
```

### Communication Technologies

#### Mocked Services
**Choice Rationale:**
- No external dependencies required
- Realistic behavior simulation
- Full database logging
- Easy to replace with real services
- Consistent failure rates for testing

**Email Service Features:**
- Template-based messaging
- Delivery status simulation
- Open/click rate tracking
- Bounce handling
- 5% failure rate simulation

**SMS Service Features:**
- Phone number validation
- Message truncation (160 chars)
- Delivery confirmation
- 3% failure rate simulation

### Data Enrichment

#### Clearbit API Integration
**Choice Rationale:**
- Comprehensive company data
- Industry classification
- Employee count metrics
- Logo retrieval
- Reliable API with good documentation

**Fallback Strategy:**
- Mock enrichment when API fails
- Company size heuristics
- Industry keyword matching
- Graceful degradation

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE SCHEMA                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                    LEADS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ id (PK)           │ INTEGER      │ AUTO INCREMENT                           │
│ name              │ VARCHAR(255) │ NOT NULL                                 │
│ email             │ VARCHAR(255) │ NOT NULL, UNIQUE, INDEXED                │
│ company           │ VARCHAR(255) │ NULLABLE                                 │
│ job_title         │ VARCHAR(255) │ NULLABLE                                 │
│ source            │ VARCHAR(100) │ NOT NULL (event, website, referral)     │
│ status            │ VARCHAR(50)  │ NOT NULL (new, contacted, engaged, ...) │
│ created_at        │ DATETIME     │ DEFAULT CURRENT_TIMESTAMP                │
│ updated_at        │ DATETIME     │ DEFAULT CURRENT_TIMESTAMP, ON UPDATE     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   MESSAGES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ id (PK)           │ INTEGER      │ AUTO INCREMENT                           │
│ lead_id (FK)      │ INTEGER      │ NOT NULL, REFERENCES leads(id)          │
│ message_text      │ TEXT         │ NOT NULL                                 │
│ timestamp         │ DATETIME     │ DEFAULT CURRENT_TIMESTAMP                │
│ channel           │ VARCHAR(50)  │ NOT NULL (email, sms, whatsapp, ...)    │
│ direction         │ VARCHAR(20)  │ NOT NULL (outbound, inbound)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Lead Model

**Fields:**
- `id`: Primary key, auto-increment
- `name`: Lead's full name (required)
- `email`: Unique email address (required, indexed)
- `company`: Company name (optional)
- `job_title`: Job title (optional)
- `source`: Lead source (event, website, referral)
- `status`: Current status in funnel
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**Status Values:**
- `new`: Newly captured lead
- `contacted`: Initial contact made
- `engaged`: Active engagement
- `meeting_scheduled`: Meeting booked
- `attended`: Event attended
- `converted`: Commercial meeting scheduled
- `lost`: Lead lost or unresponsive

**Indexes:**
- Primary key on `id`
- Unique index on `email`
- Index on `status` for filtering

### Message Model

**Fields:**
- `id`: Primary key, auto-increment
- `lead_id`: Foreign key to leads table
- `message_text`: Full message content
- `timestamp`: Message timestamp
- `channel`: Communication channel
- `direction`: Message direction

**Channel Values:**
- `email`: Email communication
- `sms`: SMS message
- `whatsapp`: WhatsApp message
- `linkedin`: LinkedIn message
- `phone`: Phone call

**Direction Values:**
- `outbound`: Sent to lead
- `inbound`: Received from lead

**Relationships:**
- Many-to-one with Lead (cascade delete)

### Database Operations

**Lead Operations:**
- `create_lead()`: Create new lead
- `get_lead()`: Retrieve lead by ID
- `get_lead_by_email()`: Retrieve lead by email
- `get_all_leads()`: List all leads with pagination
- `get_leads_by_status()`: Filter leads by status
- `update_lead_status()`: Update lead status
- `delete_lead()`: Delete lead

**Message Operations:**
- `create_message()`: Create new message
- `get_message()`: Retrieve message by ID
- `get_messages_by_lead()`: Get all messages for lead
- `get_messages_by_channel()`: Filter by channel
- `delete_message()`: Delete message

### Performance Considerations

**Current Scale:**
- 120 leads per event
- ~10 messages per lead
- ~1,200 total records
- SQLite performance: Excellent

**Scaling Strategy:**
- Add indexes on frequently queried fields
- Implement connection pooling
- Migrate to PostgreSQL for 10,000+ leads
- Consider read replicas for dashboard queries
- Implement caching for engagement scores

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication
Currently no authentication required. Future implementations may include API key authentication.

### Response Format
All endpoints return JSON responses with appropriate HTTP status codes.

### Endpoints

#### Health Check

**GET** `/health`
Check API and database status.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

#### Lead Management

**POST** `/leads`
Create a new lead.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Tech Corp",
  "job_title": "CTO",
  "source": "event",
  "status": "new"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Tech Corp",
  "job_title": "CTO",
  "source": "event",
  "status": "new",
  "created_at": "2026-06-01T15:20:54.810Z"
}
```

**POST** `/api/leads/capture`
Capture lead with validation, enrichment, and automated processing.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Tech Corp",
  "job_title": "CTO",
  "source": "event"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Tech Corp",
  "job_title": "CTO",
  "source": "event",
  "status": "new",
  "enrichment": {
    "company_size": "Large (200+ employees)",
    "industry": "Technology",
    "enriched_at": "2026-06-01T15:20:54.810Z"
  },
  "agent_processing": {
    "action": "welcome_sent",
    "welcome_message": "Welcome John! Thank you for your interest...",
    "new_status": "contacted",
    "tool_calls_executed": 1
  },
  "created_at": "2026-06-01T15:20:54.810Z"
}
```

**GET** `/leads/{lead_id}`
Get specific lead by ID.

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Tech Corp",
  "job_title": "CTO",
  "source": "event",
  "status": "contacted",
  "created_at": "2026-06-01T15:20:54.810Z",
  "updated_at": "2026-06-01T15:21:00.000Z"
}
```

**GET** `/leads`
Get all leads with optional filtering.

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)
- `status`: Filter by status (optional)

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Tech Corp",
    "job_title": "CTO",
    "source": "event",
    "status": "contacted",
    "created_at": "2026-06-01T15:20:54.810Z"
  }
]
```

**PUT** `/leads/{lead_id}/status`
Update lead status.

**Request Body:**
```json
{
  "new_status": "engaged"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "status": "engaged",
  "updated_at": "2026-06-01T15:22:00.000Z"
}
```

**DELETE** `/leads/{lead_id}`
Delete a lead.

**Response:**
```json
{
  "message": "Lead deleted successfully",
  "id": 1
}
```

#### Message Management

**POST** `/messages`
Create a new message.

**Request Body:**
```json
{
  "lead_id": 1,
  "message_text": "Hello, how can I help you?",
  "channel": "email",
  "direction": "outbound"
}
```

**Response:**
```json
{
  "id": 1,
  "lead_id": 1,
  "message_text": "Hello, how can I help you?",
  "channel": "email",
  "direction": "outbound",
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

**GET** `/messages/{message_id}`
Get specific message by ID.

**GET** `/leads/{lead_id}/messages`
Get all messages for a specific lead.

**DELETE** `/messages/{message_id}`
Delete a message.

#### Communication Services

**GET** `/api/communications/{lead_id}`
Get all communications for a specific lead.

**Response:**
```json
[
  {
    "id": 1,
    "lead_id": 1,
    "message_text": "Subject: Welcome\n\nWelcome message body",
    "channel": "email",
    "direction": "outbound",
    "timestamp": "2026-06-01T15:20:54.810Z"
  }
]
```

**POST** `/api/communications/test`
Test communication service.

**Query Parameters:**
- `lead_id`: Lead ID
- `channel`: Communication channel (email or sms)

**Response:**
```json
{
  "lead_id": 1,
  "channel": "email",
  "test_result": {
    "success": true,
    "message_id": 1,
    "status": "delivered",
    "to": "john@example.com",
    "subject": "Test Email from Secu-Agent"
  },
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

**GET** `/api/communications/stats`
Get overall communication statistics.

**Response:**
```json
{
  "statistics": {
    "email": {
      "total_emails": 50,
      "outbound": 45,
      "inbound": 5,
      "success_rate": 0.95,
      "failure_rate": 0.05
    },
    "sms": {
      "total_sms": 20,
      "outbound": 20,
      "inbound": 0,
      "success_rate": 0.97,
      "failure_rate": 0.03
    },
    "total_communications": 70
  },
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

#### Engagement Rules

**GET** `/api/rules`
Get all engagement rules with metadata.

**Response:**
```json
{
  "total_rules": 13,
  "event_date": "2026-06-15T10:00:00Z",
  "rules": [
    {
      "name": "new_lead_welcome",
      "priority": 10,
      "rule_type": "time_based",
      "cooldown_hours": 24,
      "last_executed": null
    }
  ],
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

**POST** `/api/rules/evaluate/{lead_id}`
Evaluate and execute engagement rules for a specific lead.

**Response:**
```json
{
  "lead_id": 1,
  "lead_name": "John Doe",
  "lead_status": "new",
  "engagement_score": 0,
  "rules_evaluated": 13,
  "rules_matched": 1,
  "execution_results": [
    {
      "rule_name": "new_lead_welcome",
      "priority": 10,
      "action": "email_sent",
      "success": true
    }
  ],
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

**POST** `/api/rules/process-all`
Process engagement rules for all leads.

**Response:**
```json
{
  "total_leads": 50,
  "processed": 50,
  "total_rules_matched": 25,
  "leads_with_matches": 20,
  "processing_results": [
    {
      "lead_id": 1,
      "lead_name": "John Doe",
      "lead_status": "new",
      "engagement_score": 0,
      "rules_matched": 1,
      "results": [...]
    }
  ],
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

**GET** `/api/rules/schedule`
Get upcoming scheduled actions.

**Response:**
```json
{
  "total_leads": 50,
  "upcoming_actions_count": 15,
  "event_date": "2026-06-15T10:00:00Z",
  "upcoming_actions": [
    {
      "lead_id": 1,
      "lead_name": "John Doe",
      "rule_name": "reminder_7_days_before",
      "scheduled_date": "2026-06-08T10:00:00Z",
      "days_until_event": 7
    }
  ],
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

**POST** `/api/rules/event-date`
Update the event date for time-based rules.

**Request Body:**
```json
{
  "event_date": "2026-06-15T10:00:00Z"
}
```

**Response:**
```json
{
  "message": "Event date updated successfully",
  "event_date": "2026-06-15T10:00:00Z",
  "timestamp": "2026-06-01T15:20:54.810Z"
}
```

### Error Handling

**HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (validation error)
- `404`: Not Found
- `409`: Conflict (duplicate lead)
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message description"
}
```

### Rate Limiting

**AI Rate Limiting System (Implemented):**

The system implements a comprehensive rate limiting mechanism for AI API calls to prevent abuse and optimize resource usage:

**Global Semaphore:**
- Limits to 1 concurrent AI request (leaves 1 free for API owner)
- Uses asyncio.Semaphore for thread-safe operation
- Serializes concurrent requests with queue management
- Prevents API rate limit violations and shadowban

**Priority Scheduling:**
- **Immediate Priority**: Dashboard interactions, user-facing features
- **Scheduled Priority**: Background tasks, email generation, batch processing
- Smart queuing based on business criticality
- Immediate requests processed before scheduled ones

**Off-Peak Processing:**
- Non-critical tasks scheduled for 2am-6am BRT
- Reduces API load during peak hours
- Optimizes cost efficiency
- Configurable time windows

**Cooldown System:**
- Activates after 3 consecutive API errors
- 1-hour cooldown duration (3600 seconds)
- Prevents API abuse during service outages
- Automatic recovery after cooldown period
- Error tracking with consecutive count

**Enhanced Logging:**
- All AI requests logged with BRT timestamps
- Business reason context for each request
- Caller context (filename:function:line)
- Request status tracking (QUEUED, STARTING, COMPLETED, FAILED)
- Error monitoring and alerting

**Configuration:**
```python
# Global rate limiting
_ai_semaphore = asyncio.Semaphore(1)  # 1 concurrent request

# Priority levels
PRIORITY_IMMEDIATE = "immediate"  # Dashboard, user interactions
PRIORITY_SCHEDULED = "scheduled"  # Emails, background tasks

# Error cooldown
MAX_CONSECUTIVE_ERRORS = 3
COOLDOWN_DURATION = 3600  # 1 hour

# Off-peak hours
OFF_PEAK_START = 2  # 2am BRT
OFF_PEAK_END = 6    # 6am BRT
```

**API Rate Limiting (Future):**
Planned implementation for general API endpoints:
- 100 requests per minute per IP
- 1000 requests per hour per IP
- Burst allowance for legitimate traffic
- JWT-based rate limiting per user

---

## Business Rules & Engagement Logic

### Engagement Rules Engine

The system implements a sophisticated rules engine with 13 engagement rules divided into three categories:

#### Pre-Event Rules (6 rules)

**1. New Lead Welcome (Priority: 10)**
- **Trigger:** Lead status = 'new'
- **Action:** Send personalized welcome email
- **Cooldown:** 24 hours
- **Purpose:** Immediate engagement and confirmation

**2. 7-Day Reminder (Priority: 8)**
- **Trigger:** 7 days before event
- **Action:** Send reminder with agenda preview
- **Cooldown:** 48 hours
- **Purpose:** Early awareness and planning

**3. 3-Day Reminder (Priority: 9)**
- **Trigger:** 3 days before event
- **Action:** Send reminder with logistics details
- **Cooldown:** 24 hours
- **Purpose:** Final planning and travel arrangements

**4. 1-Day Reminder (Priority: 10)**
- **Trigger:** 1 day before event
- **Action:** Send final reminder with check-in info
- **Cooldown:** 12 hours
- **Purpose:** Last-minute confirmation

**5. Personalized Content (Priority: 7)**
- **Trigger:** 5 days before event
- **Action:** Send personalized content based on job title
- **Cooldown:** 72 hours
- **Purpose:** Value-added engagement

**6. Confirmed Lead Confirmation (Priority: 8)**
- **Trigger:** Lead status = 'confirmed'
- **Action:** Send confirmation with next steps
- **Cooldown:** 24 hours
- **Purpose:** Reinforce commitment

#### Post-Event Rules (4 rules)

**1. Attended Thank You (Priority: 10)**
- **Trigger:** Lead status = 'attended'
- **Action:** Send thank you message with key takeaways
- **Cooldown:** 24 hours
- **Purpose:** Gratitude and relationship building

**2. Attended Meeting Request (Priority: 9)**
- **Trigger:** Lead status = 'attended', 2 days after event
- **Action:** Request commercial meeting
- **Cooldown:** 48 hours
- **Purpose:** Conversion to sales meeting

**3. No-Show Reschedule (Priority: 8)**
- **Trigger:** Lead status = 'confirmed', event passed
- **Action:** Offer reschedule or alternative content
- **Cooldown:** 24 hours
- **Purpose:** Recover lost leads

**4. Session-Based Content (Priority: 7)**
- **Trigger:** Lead attended specific sessions
- **Action:** Send session-specific follow-up content
- **Cooldown:** 48 hours
- **Purpose:** Personalized value delivery

#### Behavior-Based Rules (3 rules)

**1. High Engagement Escalation (Priority: 9)**
- **Trigger:** Engagement score >= 7
- **Action:** Prioritize for direct contact
- **Cooldown:** 24 hours
- **Purpose:** Accelerate high-value leads

**2. No Response De-Prioritize (Priority: 6)**
- **Trigger:** No response for 14 days
- **Action:** Reduce communication frequency
- **Cooldown:** 168 hours
- **Purpose:** Resource optimization

**3. Email Opened Follow-up (Priority: 8)**
- **Trigger:** Email opened but no response
- **Action:** Send follow-up with different angle
- **Cooldown:** 48 hours
- **Purpose:** Re-engage interested leads

### Engagement Score Calculation

**Score Components:**
- **Status Score:** 0-3 points based on lead status
- **Message Count:** 0-3 points based on total messages
- **Response Rate:** 0-2 points based on inbound/outbound ratio
- **Recency:** 0-2 points based on last activity

**Score Formula:**
```
engagement_score = status_score + message_score + response_score + recency_score
```

**Score Interpretation:**
- `0-2`: Low engagement
- `3-5`: Medium engagement
- `6-8`: High engagement
- `9-10`: Very high engagement

### Rule Evaluation Logic

**Evaluation Process:**
1. Retrieve lead and context data
2. Calculate engagement score
3. Sort rules by priority (descending)
4. Evaluate each rule's conditions
5. Check cooldown period
6. Execute matching rules
7. Log execution results
8. Update last executed timestamp

**Priority System:**
- Higher priority rules evaluated first
- Multiple rules can match simultaneously
- Cooldown periods prevent duplicate execution
- Business hours considered for timing

**Business Hours:**
- Monday-Friday: 9 AM - 6 PM UTC
- Saturday-Sunday: No automated communications
- Emergency communications: Manual override

### Scheduling and Timing

**Time-Based Triggers:**
- Event date configurable via API
- Relative time calculations (X days before/after)
- Timezone-aware scheduling
- Batch processing for efficiency

**Execution Schedule:**
- Real-time: Lead capture and status changes
- Hourly: Time-based rule evaluation
- Daily: Batch processing and reporting
- Weekly: Engagement score recalculation

### Tool Calling System

**Available Tools:**
- `SEND_EMAIL`: Send email to lead
- `SEND_SMS`: Send SMS to lead
- `SCHEDULE_REMINDER`: Schedule follow-up reminder
- `UPDATE_STATUS`: Update lead status
- `REQUEST_INFO`: Request additional information

**Tool Call Format:**
```
TOOL_NAME{parameter1: value1, parameter2: value2}
```

**Example:**
```
SEND_EMAIL{recipient: john@example.com, subject: Welcome, body: Hi John, welcome to Vigil Summit!}
```

---

## Data Strategy & Personalization

### Data Enrichment Strategy

**Primary Source: Clearbit API**
- Company information retrieval
- Industry classification
- Employee count metrics
- Company logo
- Technology stack detection

**Fallback: Mock Enrichment**
- Company size heuristics
- Industry keyword matching
- Default values for missing data
- Graceful degradation

**Enrichment Process:**
1. Extract domain from email
2. Query Clearbit API
3. Parse and normalize response
4. Store enriched data
5. Use for personalization

### Personalization Approach

**Message Personalization:**
- Dynamic content insertion
- Industry-specific messaging
- Role-based communication
- Company size adaptation
- Behavioral triggers

**Personalization Variables:**
- `{name}`: Lead's name
- `{company}`: Company name
- `{job_title}`: Job title
- `{industry}`: Industry classification
- `{company_size}`: Company size category
- `{event_date}`: Event date
- `{session_topics}`: Relevant session topics

**Content Strategy:**
- **CISOs:** Focus on strategic security and risk management
- **CTOs:** Emphasize technical implementation and integration
- **Directors:** Highlight ROI and business value
- **Managers:** Address operational efficiency and team productivity

### Data Storage Strategy

**Lead Data:**
- Core information in database
- Enrichment data in database
- Communication history in database
- Engagement metrics calculated on-demand

**Message Data:**
- Full message content stored
- Channel and direction tracked
- Timestamps for analysis
- Lead relationship maintained

**Context Management:**
- Conversation history stored
- Last 10 messages retrieved for context
- Message direction tagged (inbound/outbound)
- Chronological order preserved

### Data Privacy & Security

**LGPD Compliance:**
- Explicit consent for data collection
- Data minimization principle
- Right to deletion implementation
- Data retention policies
- Secure data storage

**Data Protection:**
- Encryption at rest (future implementation)
- Secure API communication
- Access control (future implementation)
- Audit logging
- Regular backups

### Data Analytics Strategy

**Key Metrics:**
- Lead capture rate
- Engagement score distribution
- Communication effectiveness
- Conversion rate
- No-show rate
- Response time

**Analytics Approach:**
- Real-time dashboard monitoring
- Historical trend analysis
- A/B testing capabilities
- Predictive modeling (future)
- Automated reporting

---

## Strategic Decisions & Rationale

### Architecture Decisions

**Decision: Monolithic Architecture**
**Rationale:**
- Simpler deployment and maintenance
- Adequate for current scale (120 leads)
- Lower operational overhead
- Easier testing and debugging
- Clear migration path to microservices if needed

**Decision: SQLite Database**
**Rationale:**
- Zero configuration required
- Single file deployment
- Excellent performance for current scale
- Easy backup and migration
- No external dependencies
- Clear upgrade path to PostgreSQL

**Decision: Mocked Communication Services**
**Rationale:**
- No external dependencies during development
- Realistic behavior simulation
- Full database logging
- Easy to replace with real services
- Consistent testing environment
- Cost-effective for demonstration

### Technology Choices

**Decision: FastAPI over Flask/Django**
**Rationale:**
- Better performance with async support
- Automatic API documentation
- Modern Python features
- Type hints for better code quality
- Growing ecosystem
- Easier learning curve

**Decision: Alpine.js over React/Vue**
**Rationale:**
- Lightweight and fast
- No build step required
- Easy to integrate with existing HTML
- Perfect for single-page applications
- Lower complexity
- Faster development time

**Decision: TailwindCSS CDN over Build Process**
**Rationale:**
- Rapid prototyping
- No build configuration needed
- Easy customization
- Consistent design system
- Good performance for production
- Lower barrier to entry

### AI/LLM Strategy

**Decision: ArliAI as Primary LLM**
**Rationale:**
- OpenAI-compatible API
- Cost-effective alternative
- Multiple model options
- Good performance for business use
- Reliable uptime
- Easy integration

**Decision: Anthropic as Secondary Option**
**Rationale:**
- Superior reasoning capabilities
- Better for complex decisions
- Preferred by case requirements
- Flexible dispatcher implementation
- Easy switching between providers

**Decision: Tool Calling Approach**
**Rationale:**
- Structured AI decision-making
- Clear action execution
- Better debugging and logging
- Extensible architecture
- Industry best practice

### Business Logic Decisions

**Decision: 13 Engagement Rules**
**Rationale:**
- Comprehensive coverage of lead lifecycle
- Balance between automation and personalization
- Proactive and reactive triggers
- Time-based and behavior-based rules
- Priority system for conflict resolution

**Decision: Engagement Score (0-10)**
**Rationale:**
- Simple and intuitive
- Actionable thresholds
- Easy to communicate
- Calculated from multiple factors
- Adaptable scoring formula

**Decision: Cooldown Periods**
**Rationale:**
- Prevent communication fatigue
- Respect lead's time
- Optimize resource usage
- Improve response rates
- Professional communication standards

### Deployment Strategy

**Decision: Local Development First**
**Rationale:**
- Faster development cycle
- Easier debugging
- No infrastructure costs
- Full control over environment
- Quick iteration and testing

**Decision: Clear Migration Path**
**Rationale:**
- PostgreSQL for production scaling
- Docker for containerization
- Cloud deployment ready
- Environment configuration
- CI/CD pipeline ready

### Testing Strategy

**Decision: Comprehensive Test Suite**
**Rationale:**
- Ensure reliability
- Facilitate refactoring
- Document expected behavior
- Catch regressions early
- Build confidence in changes

**Decision: Mocked External Services**
**Rationale:**
- Consistent testing environment
- No external dependencies
- Faster test execution
- Predictable test results
- Cost-effective testing

---

## Implementation Plan

### Day 1: Environment Setup and Basic Structure

**Morning:**
- Set up development environment
- Initialize Git repository
- Create project structure
- Configure virtual environment
- Install core dependencies

**Afternoon:**
- Set up FastAPI application
- Configure database connection
- Create basic models (Lead, Message)
- Implement CRUD operations
- Set up API documentation

**Deliverables:**
- Running FastAPI server
- Database schema created
- Basic CRUD endpoints working
- API documentation accessible

### Day 2: Database and Core API

**Morning:**
- Implement database relationships
- Add foreign key constraints
- Create database operations classes
- Implement data validation
- Add error handling

**Afternoon:**
- Build lead management endpoints
- Build message management endpoints
- Implement filtering and pagination
- Add health check endpoint
- Create API testing suite

**Deliverables:**
- Complete database operations
- All CRUD endpoints functional
- Validation and error handling
- Basic test coverage

### Day 3: AI Integration and Agent Logic

**Morning:**
- Integrate ArliAI API
- Implement LLM dispatcher
- Create AI client class
- Test AI responses
- Handle API errors gracefully

**Afternoon:**
- Implement Agent class
- Create tool calling system
- Build welcome message generation
- Implement context management
- Add conversation history tracking

**Deliverables:**
- Working AI integration
- Agent with tool calling
- Welcome message automation
- Context-aware responses

### Day 4: Communication and Business Rules

**Morning:**
- Implement communication services
- Create email service with templates
- Create SMS service
- Add database logging
- Implement delivery tracking

**Afternoon:**
- Build engagement rules engine
- Implement pre-event rules
- Implement post-event rules
- Add behavior-based rules
- Create rule evaluation logic

**Deliverables:**
- Communication services working
- All 13 engagement rules implemented
- Rule evaluation system
- Automated workflows

### Day 5: Frontend, Testing, and Documentation

**Morning:**
- Build landing page with Alpine.js
- Implement form validation
- Add real-time feedback
- Create dashboard interface
- Integrate with backend API

**Afternoon:**
- Complete test coverage
- Fix bugs and issues
- Write technical documentation
- Create user guide
- Prepare deployment package

**Deliverables:**
- Fully functional frontend
- Comprehensive test suite
- Complete documentation
- Deployment-ready application

---

## Deployment Instructions

### Local Development Setup

**Prerequisites:**
- Python 3.8 or higher
- pip package manager
- Git (optional)
- Modern web browser

**Step-by-Step Setup:**

1. **Clone or Download Repository**
   ```bash
   git clone <repository-url>
   cd Secu-Agent
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate Virtual Environment**
   - **Windows:**
     ```bash
     .venv\Scripts\activate
     ```
   - **Linux/Mac:**
     ```bash
     source .venv/bin/activate
     ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure AI API**
   - Create `airli_config.json`:
   ```json
   {
     "API_KEY": "your-api-key-here",
     "BASE_URL": "https://api.arli.ai/v1",
     "LLM_PROVIDER": "openai",
     "LLM_MODEL": "Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled"
   }
   ```

6. **Initialize Database**
   ```bash
   python -c "from database import init_db; init_db()"
   ```

7. **Run Application**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Access Application**
   - Landing Page: http://localhost:8000
   - Dashboard: http://localhost:8000/dashboard
   - API Docs: http://localhost:8000/docs

### Environment Configuration

**Required Environment Variables:**
```bash
# AI Configuration
LLM_PROVIDER=openai  # or 'anthropic'
LLM_API_KEY=your-api-key
LLM_API_URL=https://api.arli.ai/v1
LLM_MODEL=Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled

# Database (optional, defaults to sqlite:///vigil_agent.db)
DATABASE_URL=sqlite:///vigil_agent.db

# Application (optional)
APP_NAME=Secu-Agent
APP_VERSION=1.0.0
DEBUG=False
```

**Configuration Files:**
- `airli_config.json`: AI API configuration
- `requirements.txt`: Python dependencies
- `.env`: Environment variables (optional)

### Production Deployment

**Railway Deployment (Current):**

The Secu-Agent system is currently deployed on Railway cloud platform with the following configuration:

**Deployment Configuration:**
- **Platform**: Railway (cloud deployment platform)
- **Environment**: Production
- **Database**: SQLite (with PostgreSQL migration path)
- **AI Integration**: ArliAI with rate limiting
- **Static Files**: Served via FastAPI static file mounting

**Railway-Specific Features:**
- Automatic HTTPS/SSL certificates
- Built-in monitoring and logging
- Environment variable management
- Automatic deployments from Git
- Health check monitoring
- Resource scaling capabilities

**Environment Variables on Railway:**
```bash
# AI Configuration
LLM_PROVIDER=openai
LLM_API_KEY=${RAILWAY_PRIVATE_API_KEY}
LLM_API_URL=https://api.arli.ai/v1
LLM_MODEL=Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled

# Database
DATABASE_URL=sqlite:///vigil_agent.db

# Application
APP_NAME=Secu-Agent
APP_VERSION=1.0.0
DEBUG=False
```

**Railway AI Integration:**
- Rate limiting implemented via Railway AI PR
- Global semaphore for AI request management
- Priority scheduling for optimal resource usage
- Cooldown system for error recovery
- Enhanced logging with BRT timestamps

**Monitoring on Railway:**
- Real-time health checks
- API response time monitoring
- Error rate tracking
- Resource usage metrics
- AI API usage monitoring

**Option 1: Traditional VPS**

1. **Server Setup**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python
   sudo apt install python3 python3-pip python3-venv -y
   
   # Install Nginx
   sudo apt install nginx -y
   ```

2. **Application Setup**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd Secu-Agent
   
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Install production server
   pip install gunicorn
   ```

3. **Configure Gunicorn**
   ```bash
   gunicorn main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --access-logfile - \
     --error-logfile -
   ```

4. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /static {
           alias /path/to/Secu-Agent/static;
       }
   }
   ```

5. **Set Up Systemd Service**
   ```ini
   [Unit]
   Description=Secu-Agent Application
   After=network.target
   
   [Service]
   User=www-data
   WorkingDirectory=/path/to/Secu-Agent
   Environment="PATH=/path/to/Secu-Agent/.venv/bin"
   ExecStart=/path/to/Secu-Agent/.venv/bin/gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   
   [Install]
   WantedBy=multi-user.target
   ```

**Option 2: Docker Deployment**

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.10-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   EXPOSE 8000
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     app:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./vigil_agent.db:/app/vigil_agent.db
       environment:
         - LLM_PROVIDER=openai
         - LLM_API_KEY=${LLM_API_KEY}
       restart: unless-stopped
   ```

3. **Deploy**
   ```bash
   docker-compose up -d
   ```

**Option 3: Cloud Deployment (AWS/GCP/Azure)**

1. **Containerize Application**
2. **Push to Container Registry**
3. **Create Cloud Service**
4. **Configure Environment Variables**
5. **Set Up Load Balancer**
6. **Configure Domain and SSL**

### Database Migration

**SQLite to PostgreSQL:**

1. **Export SQLite Data**
   ```bash
   sqlite3 vigil_agent.db .dump > backup.sql
   ```

2. **Create PostgreSQL Database**
   ```sql
   CREATE DATABASE vigil_agent;
   ```

3. **Import Data**
   ```bash
   psql -h localhost -U postgres -d vigil_agent < backup.sql
   ```

4. **Update Configuration**
   ```python
   DATABASE_URL = "postgresql://user:password@localhost/vigil_agent"
   ```

### Backup and Recovery

**Database Backup:**
```bash
# SQLite
cp vigil_agent.db vigil_agent_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump -U postgres vigil_agent > backup_$(date +%Y%m%d).sql
```

**Database Recovery:**
```bash
# SQLite
cp vigil_agent_backup_20260601.db vigil_agent.db

# PostgreSQL
psql -U postgres vigil_agent < backup_20260601.sql
```

### Monitoring and Logging

**Application Logging:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

**Health Monitoring:**
- Check `/health` endpoint regularly
- Monitor database connection
- Track AI API response times
- Monitor error rates

**Performance Monitoring:**
- Response time tracking
- Database query performance
- Memory usage
- CPU utilization

---

## Testing Strategy

### Test Coverage Overview

**Current Coverage:**
- Unit tests: ~80%
- Integration tests: ~70%
- End-to-end tests: ~60%
- Overall: ~75%

**Test Suite Breakdown:**
- **Database Tests**: 29 tests (100% passing)
  - Database connection and initialization
  - Lead CRUD operations
  - Message CRUD operations
  - Lead-Message relationships
  - Edge cases and error handling
  - Data integrity constraints
  - Pagination and filtering

- **AI Integration Tests**: 16 tests (100% passing)
  - AI client initialization
  - Real API interactions
  - Lead engagement features
  - Interest analysis
  - Follow-up suggestions
  - Error handling
  - API discovery validation

- **Rate Limiting Tests**: 18 tests (72% passing - 13/18)
  - Global semaphore behavior
  - Concurrent request serialization
  - Priority scheduling system
  - Off-peak hours detection
  - Cooldown system activation
  - Error handling and recovery
  - Logging with BRT timestamps
  - Integration scenarios

- **E2E Tests**: 35 tests (71% passing - 25/35)
  - Complete user flows
  - System integration
  - Data consistency validation

**Total Tests**: 98 tests across 4 test suites
**Overall Pass Rate**: ~85% (83/98 tests passing)

**Target Coverage:**
- Unit tests: 90%
- Integration tests: 85%
- End-to-end tests: 80%
- Overall: 85%

### Testing Approach

#### Unit Testing

**Purpose:** Test individual components in isolation

**Tools:** pytest, unittest.mock

**Coverage:**
- Database operations
- AI client functions
- Communication services
- Business logic functions
- Utility functions

**Example:**
```python
def test_create_lead(db_session):
    lead = LeadOperations.create_lead(
        db=db_session,
        name="John Doe",
        email="john@example.com",
        company="Tech Corp",
        job_title="CTO"
    )
    assert lead.id is not None
    assert lead.name == "John Doe"
    assert lead.email == "john@example.com"
```

#### Integration Testing

**Purpose:** Test component interactions

**Tools:** pytest, test database

**Coverage:**
- API endpoints
- Database integration
- AI service integration
- Communication service integration
- Rule evaluation

**Example:**
```python
def test_lead_capture_endpoint(client, db_session):
    response = client.post("/api/leads/capture", json={
        "name": "John Doe",
        "email": "john@example.com",
        "company": "Tech Corp",
        "job_title": "CTO"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John Doe"
    assert "enrichment" in data
```

#### End-to-End Testing

**Purpose:** Test complete user flows

**Tools:** Selenium, Playwright, or manual testing

**Coverage:**
- Lead capture flow
- Engagement rule execution
- Dashboard functionality
- Communication flows
- Error handling

**Test Scenarios:**
1. Lead captures → Welcome message sent
2. Lead receives reminder → Confirms attendance
3. Lead attends event → Thank you message sent
4. Lead requests meeting → Meeting scheduled
5. Invalid data → Error handling

### Test Execution

**Run All Tests:**
```bash
pytest tests/ -v
```

**Run Specific Test File:**
```bash
pytest tests/test_database.py -v
```

**Run with Coverage:**
```bash
pytest tests/ --cov=. --cov-report=html
```

**Run Specific Test:**
```bash
pytest tests/test_database.py::test_create_lead -v
```

### Continuous Integration

**GitHub Actions Example:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

### Test Data Management

**Fixtures:**
- Fresh database for each test
- Sample lead data
- Sample message data
- Mock AI responses
- Mock communication results

**Cleanup:**
- Automatic rollback after each test
- Delete test data
- Reset sequences
- Clear caches

### Performance Testing

**Load Testing:**
- Simulate concurrent users
- Test API response times
- Database query performance
- Memory usage monitoring

**Tools:**
- Locust
- Apache Bench
- pytest-benchmark

---

## Security & Compliance

### LGPD Compliance

**Data Collection:**
- Explicit consent required
- Purpose specification
- Data minimization
- Transparent privacy policy

**Data Rights:**
- Right to access
- Right to correction
- Right to deletion
- Right to portability
- Right to objection

**Data Storage:**
- Secure storage
- Encryption at rest (planned)
- Access controls (planned)
- Regular backups
- Retention policies

**Data Processing:**
- Lawful basis for processing
- Purpose limitation
- Data accuracy
- Storage limitation
- Integrity and confidentiality

### Security Measures

**Application Security:**
- Input validation
- SQL injection prevention
- XSS protection
- CSRF protection (planned)
- Rate limiting (planned)

**API Security:**
- API key authentication (planned)
- JWT tokens (recommended for production - see below)
- HTTPS enforcement
- Request signing (planned)

**JWT Authentication Requirements (Production):**

For production deployment, implementing JWT (JSON Web Token) authentication is strongly recommended:

**Required Components:**
1. **User Authentication System**
   - User registration and login endpoints
   - Password hashing with bcrypt
   - Session management
   - User roles and permissions

2. **JWT Token Generation**
   - Token creation on successful authentication
   - Token expiration configuration (recommended: 1 hour)
   - Refresh token mechanism (recommended: 7 days)
   - Secret key management via environment variables

3. **Protected API Endpoints**
   - JWT validation middleware
   - Token refresh endpoint
   - Protected route decorators
   - Role-based access control

4. **Session Management**
   - Token blacklist for logout
   - Session timeout handling
   - Concurrent session limits
   - Security event logging

**Implementation Guidance:**
```python
# Required dependencies
# pip install fastapi-jwt-auth python-jose[cryptography] passlib[bcrypt]

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# User Model Extension
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Security Best Practices:**
- Store JWT_SECRET_KEY in Railway environment variables
- Use strong, randomly generated secret keys
- Implement token rotation for enhanced security
- Add rate limiting per authenticated user
- Log all authentication attempts
- Implement account lockout after failed attempts

**Production Deployment Steps:**
1. Set JWT_SECRET_KEY in Railway environment variables
2. Create user management database tables
3. Implement authentication endpoints (/auth/login, /auth/register)
4. Add JWT middleware to protected routes
5. Update API documentation with authentication requirements
6. Test authentication flow thoroughly
7. Monitor authentication logs for suspicious activity

**Current Status:**
- JWT authentication is **recommended for production** but not currently implemented
- System operates without authentication for development/testing
- All endpoints are currently publicly accessible
- JWT implementation should be prioritized before public production launch

**Database Security:**
- Parameterized queries
- Foreign key constraints
- Access controls (planned)
- Encryption at rest (planned)
- Regular backups

**Communication Security:**
- TLS/SSL encryption
- Secure API communication
- Email authentication (planned)
- SMS verification (planned)

### Best Practices

**Development:**
- Secure coding practices
- Regular dependency updates
- Code reviews
- Security testing
- Vulnerability scanning

**Deployment:**
- Environment separation
- Secrets management
- Secure configuration
- Regular updates
- Monitoring and alerting

**Operations:**
- Access logging
- Audit trails
- Incident response plan
- Regular security audits
- Penetration testing

### Incident Response

**Detection:**
- Monitoring and alerting
- Log analysis
- Anomaly detection
- User reports

**Response:**
- Incident classification
- Containment measures
- Investigation
- Remediation
- Communication

**Recovery:**
- System restoration
- Data recovery
- Security improvements
- Documentation
- Post-incident review

---

## Conclusion

This technical documentation provides a comprehensive overview of the Secu-Agent system, covering architecture, technology stack, business rules, implementation details, and deployment strategies. The system is designed to be scalable, maintainable, and compliant with data protection regulations while delivering effective lead management for cybersecurity events.

For questions or support, please refer to the README.md or contact the development team.

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-06-01  
**Author:** Gustavo Rossoni Corrêa De Barros
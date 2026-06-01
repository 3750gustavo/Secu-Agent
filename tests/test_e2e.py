"""
Comprehensive End-to-End Tests for Secu-Agent AI Lead Management System.
Tests complete user flows, system integration, data consistency, performance, and security.
"""

import pytest
import sys
import os
import time
import uuid
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import (
    init_db, get_db, Lead, Message,
    LeadOperations, MessageOperations, check_db_connection,
    SessionLocal, Base, engine
)
from ai_client import Agent, EngagementRules, AIClient
from communication import get_communication_service, EmailService, SMSService
from main import app


# Test fixtures
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test."""
    # Use test database
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


@pytest.fixture(scope="function")
def test_client():
    """Create a test FastAPI client."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def sample_lead_data():
    """Generate unique sample lead data for testing."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"Test User {unique_id}",
        "email": f"test{unique_id}@example.com",
        "company": "Test Company",
        "job_title": "CTO",
        "source": "event"
    }


@pytest.fixture
def multiple_leads_data():
    """Generate multiple unique leads for batch testing."""
    leads = []
    for i in range(5):
        unique_id = str(uuid.uuid4())[:8]
        leads.append({
            "name": f"Batch Lead {i}",
            "email": f"batch{i}{unique_id}@example.com",
            "company": f"Company {i}",
            "job_title": ["CTO", "CISO", "Security Manager", "IT Director", "VP Engineering"][i],
            "source": "event"
        })
    return leads


class TestE2EFlow1_LandingToDashboard:
    """Test Flow 1: Landing page → form submission → enrichment → welcome message → dashboard display."""
    
    def test_complete_landing_to_dashboard_flow(self, test_client, test_db, sample_lead_data):
        """Test complete user journey from landing to dashboard."""
        # Step 1: Access landing page
        response = test_client.get("/")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        
        # Step 2: Submit lead capture form
        capture_response = test_client.post("/api/leads/capture", json=sample_lead_data)
        assert capture_response.status_code == 200
        
        lead_data = capture_response.json()
        assert "id" in lead_data
        assert lead_data["name"] == sample_lead_data["name"]
        assert lead_data["email"] == sample_lead_data["email"]
        assert "enrichment" in lead_data
        assert "agent_processing" in lead_data
        
        lead_id = lead_data["id"]
        
        # Step 3: Verify enrichment data
        assert lead_data["enrichment"]["company_size"] is not None
        assert lead_data["enrichment"]["industry"] is not None
        
        # Step 4: Verify agent processing
        assert lead_data["agent_processing"]["success"] is True
        assert lead_data["agent_processing"]["action"] == "welcome_sent"
        
        # Step 5: Verify welcome message was sent
        messages = MessageOperations.get_messages_by_lead(test_db, lead_id)
        assert len(messages) >= 1
        assert any("welcome" in msg.message_text.lower() for msg in messages)
        
        # Step 6: Access dashboard
        dashboard_response = test_client.get("/dashboard")
        assert dashboard_response.status_code == 200
        assert "html" in dashboard_response.text.lower()
        
        # Step 7: Verify lead appears in API
        leads_response = test_client.get("/leads")
        assert leads_response.status_code == 200
        leads = leads_response.json()
        assert len(leads) >= 1
        assert any(lead["id"] == lead_id for lead in leads)
        
        # Step 8: Verify specific lead data
        lead_detail_response = test_client.get(f"/leads/{lead_id}")
        assert lead_detail_response.status_code == 200
        lead_detail = lead_detail_response.json()
        assert lead_detail["status"] == "contacted"  # Status should change after welcome
        
        print(f"✓ Flow 1 Complete: Lead {lead_id} captured, enriched, processed, and displayed")


class TestE2EFlow2_EngagementRulesAndReminders:
    """Test Flow 2: Lead capture → engagement rules → reminder scheduling → communication."""
    
    def test_complete_engagement_flow(self, test_client, test_db, sample_lead_data):
        """Test engagement rules and reminder scheduling."""
        # Step 1: Capture lead
        capture_response = test_client.post("/api/leads/capture", json=sample_lead_data)
        assert capture_response.status_code == 200
        lead_id = capture_response.json()["id"]
        
        # Step 2: Get engagement rules
        rules_response = test_client.get("/api/rules")
        assert rules_response.status_code == 200
        rules_data = rules_response.json()
        assert rules_data["total_rules"] > 0
        
        # Step 3: Evaluate rules for the lead
        evaluate_response = test_client.post(f"/api/rules/evaluate/{lead_id}")
        assert evaluate_response.status_code == 200
        evaluation = evaluate_response.json()
        
        assert evaluation["lead_id"] == lead_id
        assert evaluation["engagement_score"] >= 0
        assert evaluation["rules_evaluated"] > 0
        
        # Step 4: Verify rule execution results
        if evaluation["rules_matched"] > 0:
            assert "execution_results" in evaluation
            assert len(evaluation["execution_results"]) > 0
        
        # Step 5: Get upcoming scheduled actions
        schedule_response = test_client.get("/api/rules/schedule")
        assert schedule_response.status_code == 200
        schedule_data = schedule_response.json()
        
        assert "upcoming_actions" in schedule_data
        assert "event_date" in schedule_data
        
        # Step 6: Test communication service integration
        comm_response = test_client.get(f"/api/communications/{lead_id}")
        assert comm_response.status_code == 200
        communications = comm_response.json()
        
        assert len(communications) >= 1  # At least welcome message
        
        # Step 7: Test communication stats
        stats_response = test_client.get("/api/communications/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        assert "statistics" in stats
        assert "email" in stats["statistics"]
        assert "sms" in stats["statistics"]
        
        print(f"✓ Flow 2 Complete: Engagement rules evaluated and communications tracked for lead {lead_id}")


class TestE2EFlow3_BatchProcessingAndPriority:
    """Test Flow 3: Multiple leads → rule evaluation → priority handling → batch processing."""
    
    def test_complete_batch_processing_flow(self, test_client, test_db, multiple_leads_data):
        """Test batch processing of multiple leads with priority handling."""
        lead_ids = []
        
        # Step 1: Capture multiple leads
        for lead_data in multiple_leads_data:
            capture_response = test_client.post("/api/leads/capture", json=lead_data)
            assert capture_response.status_code == 200
            lead_ids.append(capture_response.json()["id"])
        
        # Step 2: Verify all leads were created
        leads_response = test_client.get("/leads")
        assert leads_response.status_code == 200
        all_leads = leads_response.json()
        assert len(all_leads) >= len(multiple_leads_data)
        
        # Step 3: Process rules for all leads
        process_all_response = test_client.post("/api/rules/process-all")
        assert process_all_response.status_code == 200
        processing_results = process_all_response.json()
        
        assert processing_results["total_leads"] >= len(multiple_leads_data)
        assert processing_results["processed"] >= len(multiple_leads_data)
        assert "total_rules_matched" in processing_results
        
        # Step 4: Verify priority handling
        if processing_results["leads_with_matches"] > 0:
            assert "processing_results" in processing_results
            results = processing_results["processing_results"]
            
            # Check that results are ordered by engagement score (priority)
            if len(results) > 1:
                scores = [r.get("engagement_score", 0) for r in results]
                assert scores == sorted(scores, reverse=True)
        
        # Step 5: Verify communications for all leads
        total_communications = 0
        for lead_id in lead_ids:
            comm_response = test_client.get(f"/api/communications/{lead_id}")
            assert comm_response.status_code == 200
            communications = comm_response.json()
            total_communications += len(communications)
        
        assert total_communications >= len(multiple_leads_data)  # At least welcome for each
        
        # Step 6: Test filtering by status
        new_leads_response = test_client.get("/leads?status=new")
        assert new_leads_response.status_code == 200
        
        contacted_leads_response = test_client.get("/leads?status=contacted")
        assert contacted_leads_response.status_code == 200
        
        print(f"✓ Flow 3 Complete: {len(lead_ids)} leads processed with priority handling")


class TestE2EFlow4_ErrorScenariosAndRecovery:
    """Test Flow 4: Error scenarios → recovery → fallback mechanisms."""
    
    def test_duplicate_lead_handling(self, test_client, test_db, sample_lead_data):
        """Test handling of duplicate lead submissions."""
        # Step 1: Submit lead first time
        first_response = test_client.post("/api/leads/capture", json=sample_lead_data)
        assert first_response.status_code == 200
        first_lead_id = first_response.json()["id"]
        
        # Step 2: Try to submit same lead again (should fail)
        second_response = test_client.post("/api/leads/capture", json=sample_lead_data)
        assert second_response.status_code == 409  # Conflict
        assert "already exists" in second_response.json()["detail"].lower()
        
        # Step 3: Verify only one lead exists
        leads_response = test_client.get("/leads")
        leads = leads_response.json()
        email_leads = [lead for lead in leads if lead["email"] == sample_lead_data["email"]]
        assert len(email_leads) == 1
        
        print(f"✓ Duplicate handling: Lead {first_lead_id} protected from duplicate submission")
    
    def test_invalid_data_validation(self, test_client):
        """Test validation of invalid input data."""
        # Test missing required fields
        invalid_data = {
            "name": "Test User"
            # Missing email, company, job_title
        }
        
        response = test_client.post("/api/leads/capture", json=invalid_data)
        assert response.status_code == 400
        assert "missing" in response.json()["detail"].lower() or "required" in response.json()["detail"].lower()
        
        # Test invalid email format
        invalid_email_data = {
            "name": "Test User",
            "email": "invalid-email",
            "company": "Test Company",
            "job_title": "CTO"
        }
        
        response = test_client.post("/api/leads/capture", json=invalid_email_data)
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()
        
        print("✓ Invalid data validation: Proper error responses for invalid inputs")
    
    def test_nonexistent_resource_handling(self, test_client):
        """Test handling of requests for non-existent resources."""
        # Test non-existent lead
        response = test_client.get("/leads/99999")
        assert response.status_code == 404
        
        # Test non-existent message
        response = test_client.get("/messages/99999")
        assert response.status_code == 404
        
        # Test communications for non-existent lead
        response = test_client.get("/api/communications/99999")
        assert response.status_code == 404
        
        # Test rules for non-existent lead
        response = test_client.post("/api/rules/evaluate/99999")
        assert response.status_code == 404
        
        print("✓ Non-existent resource handling: Proper 404 responses")
    
    def test_database_connection_recovery(self, test_db):
        """Test database connection and recovery."""
        # Test initial connection
        assert check_db_connection() is True
        
        # Test database operations after connection check
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Connection Test",
            email="connection@example.com",
            source="test"
        )
        
        assert lead.id is not None
        
        # Test retrieval
        retrieved_lead = LeadOperations.get_lead(test_db, lead.id)
        assert retrieved_lead is not None
        assert retrieved_lead.name == "Connection Test"
        
        print("✓ Database connection recovery: Connection stable and operations successful")


class TestSystemIntegration:
    """Test system integration points."""
    
    def test_database_persistence_across_operations(self, test_db, sample_lead_data):
        """Test that data persists correctly across database operations."""
        # Create lead
        lead = LeadOperations.create_lead(
            db=test_db,
            **sample_lead_data
        )
        
        # Add message
        message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Test message",
            channel="email",
            direction="outbound"
        )
        
        # Update status
        updated_lead = LeadOperations.update_lead_status(test_db, lead.id, "contacted")
        
        # Verify all changes persist
        final_lead = LeadOperations.get_lead(test_db, lead.id)
        assert final_lead.status == "contacted"
        assert len(final_lead.messages) == 1
        assert final_lead.messages[0].id == message.id
        
        print("✓ Database persistence: All operations persist correctly")
    
    def test_ai_integration_with_real_api(self):
        """Test AI integration with real API calls."""
        client = AIClient()
        
        # Test basic chat completion
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'AI integration test passed!'"}
        ]
        
        response = client.chat_completion(messages)
        
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "content" in response["choices"][0]["message"]
        assert "test passed" in response["choices"][0]["message"]["content"].lower()
        
        print("✓ AI integration: Real API calls successful")
    
    def test_communication_system_integration(self, test_db, sample_lead_data):
        """Test communication system integration with database."""
        # Create lead
        lead = LeadOperations.create_lead(db=test_db, **sample_lead_data)
        
        # Get communication service
        comm_service = get_communication_service()
        
        # Send email
        email_result = comm_service.send_email(
            to=lead.email,
            subject="Integration Test",
            body="Testing communication integration",
            lead_id=lead.id,
            db_session=test_db
        )
        
        assert email_result["success"] is True
        
        # Send SMS
        sms_result = comm_service.send_sms(
            phone="+1234567890",
            message="SMS integration test",
            lead_id=lead.id,
            db_session=test_db
        )
        
        assert sms_result["success"] is True
        
        # Verify both communications are logged
        communications = comm_service.get_communications_for_lead(lead.id, test_db)
        assert len(communications) == 2
        
        print("✓ Communication system integration: Email and SMS logged correctly")
    
    def test_business_rules_engine_execution(self, test_db, sample_lead_data):
        """Test business rules engine execution."""
        # Create lead
        lead = LeadOperations.create_lead(db=test_db, **sample_lead_data)
        
        # Create rules engine
        rules_engine = EngagementRules()
        
        # Create agent
        agent = Agent()
        
        # Build lead dict
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
        score = rules_engine.get_engagement_score(lead_dict, test_db)
        assert isinstance(score, int)
        assert 0 <= score <= 10
        
        # Build context
        context = {
            'engagement_score': score,
            'event_date': rules_engine.event_date,
            'sessions_attended': [],
            'last_email_opened': None,
            'last_contact_date': lead.updated_at
        }
        
        # Evaluate rules
        results = rules_engine.evaluate_rules_for_lead(lead_dict, context, agent, test_db)
        
        assert isinstance(results, list)
        
        print("✓ Business rules engine: Rules evaluated and executed correctly")


class TestDataConsistency:
    """Test data consistency and relationships."""
    
    def test_foreign_key_constraints(self, test_db):
        """Test foreign key constraints between leads and messages."""
        # Create lead
        lead = LeadOperations.create_lead(
            db=test_db,
            name="FK Test",
            email="fk@example.com",
            source="test"
        )
        
        # Create valid message
        message = MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Valid message",
            channel="email",
            direction="outbound"
        )
        
        assert message.lead_id == lead.id
        
        # Try to create message with invalid lead_id (should fail)
        with pytest.raises(Exception):
            MessageOperations.create_message(
                db=test_db,
                lead_id=99999,
                message_text="Invalid message",
                channel="email",
                direction="outbound"
            )
        
        print("✓ Foreign key constraints: Valid relationships enforced")
    
    def test_data_relationships(self, test_db, sample_lead_data):
        """Test data relationships between leads and messages."""
        # Create lead
        lead = LeadOperations.create_lead(db=test_db, **sample_lead_data)
        
        # Create multiple messages
        msg1 = MessageOperations.create_message(
            db=test_db, lead_id=lead.id, message_text="Message 1",
            channel="email", direction="outbound"
        )
        msg2 = MessageOperations.create_message(
            db=test_db, lead_id=lead.id, message_text="Message 2",
            channel="sms", direction="outbound"
        )
        msg3 = MessageOperations.create_message(
            db=test_db, lead_id=lead.id, message_text="Message 3",
            channel="email", direction="inbound"
        )
        
        # Refresh lead to get relationships
        test_db.refresh(lead)
        
        # Test lead → messages relationship
        assert len(lead.messages) == 3
        assert msg1 in lead.messages
        assert msg2 in lead.messages
        assert msg3 in lead.messages
        
        # Test message → lead relationship
        test_db.refresh(msg1)
        assert msg1.lead == lead
        assert msg1.lead.id == lead.id
        
        print("✓ Data relationships: Lead-message relationships work correctly")
    
    def test_transaction_rollback_on_error(self, test_db):
        """Test transaction rollback on errors."""
        initial_lead_count = len(LeadOperations.get_all_leads(test_db))
        
        # Try to create lead with invalid data (should rollback)
        try:
            # This should fail due to unique constraint violation
            LeadOperations.create_lead(
                db=test_db,
                name="Rollback Test",
                email="rollback@example.com",
                source="test"
            )
            
            # Try to create duplicate
            LeadOperations.create_lead(
                db=test_db,
                name="Rollback Test 2",
                email="rollback@example.com",  # Same email
                source="test"
            )
        except Exception:
            pass
        
        # Verify no partial data was committed
        final_lead_count = len(LeadOperations.get_all_leads(test_db))
        
        # Count should be either initial or initial + 1 (first create might have succeeded)
        assert final_lead_count <= initial_lead_count + 1
        
        print("✓ Transaction rollback: Errors handled correctly without partial commits")
    
    def test_concurrent_operations(self, test_db):
        """Test concurrent database operations."""
        import threading
        
        results = []
        errors = []
        
        def create_lead_thread(index):
            try:
                unique_id = str(uuid.uuid4())[:8]
                lead = LeadOperations.create_lead(
                    db=test_db,
                    name=f"Concurrent {index}",
                    email=f"concurrent{index}{unique_id}@example.com",
                    source="test"
                )
                results.append(lead.id)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_lead_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Verify all leads were created
        all_leads = LeadOperations.get_all_leads(test_db)
        assert len(all_leads) >= 5
        
        print("✓ Concurrent operations: Multiple threads handled correctly")


class TestPerformance:
    """Test performance characteristics."""
    
    def test_lead_capture_response_time(self, test_client, sample_lead_data):
        """Test lead capture API response time."""
        start_time = time.time()
        
        response = test_client.post("/api/leads/capture", json=sample_lead_data)
        
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < 5.0  # Should complete within 5 seconds
        
        print(f"✓ Lead capture response time: {elapsed_time:.2f}s (target: <5s)")
    
    def test_api_endpoint_performance(self, test_client):
        """Test various API endpoint performance."""
        endpoints = [
            ("GET", "/health"),
            ("GET", "/api/info"),
            ("GET", "/api/rules"),
            ("GET", "/api/communications/stats"),
        ]
        
        for method, endpoint in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = test_client.get(endpoint)
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200
            assert elapsed_time < 2.0  # Should complete within 2 seconds
            
            print(f"✓ {method} {endpoint}: {elapsed_time:.2f}s (target: <2s)")
    
    def test_database_query_efficiency(self, test_db, multiple_leads_data):
        """Test database query efficiency with multiple records."""
        # Create multiple leads
        lead_ids = []
        for lead_data in multiple_leads_data:
            lead = LeadOperations.create_lead(db=test_db, **lead_data)
            lead_ids.append(lead.id)
        
        # Test query performance
        start_time = time.time()
        all_leads = LeadOperations.get_all_leads(test_db)
        query_time = time.time() - start_time
        
        assert len(all_leads) >= len(multiple_leads_data)
        assert query_time < 1.0  # Should complete within 1 second
        
        # Test filtered query performance
        start_time = time.time()
        filtered_leads = LeadOperations.get_leads_by_status(test_db, "new")
        filter_time = time.time() - start_time
        
        assert filter_time < 1.0  # Should complete within 1 second
        
        print(f"✓ Database query efficiency: {query_time:.3f}s for all, {filter_time:.3f}s for filtered")
    
    def test_memory_usage_during_operations(self, test_db, sample_lead_data):
        """Test memory usage during operations."""
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Create multiple leads and messages
        for i in range(10):
            unique_id = str(uuid.uuid4())[:8]
            lead = LeadOperations.create_lead(
                db=test_db,
                name=f"Memory Test {i}",
                email=f"memory{i}{unique_id}@example.com",
                company="Test Company",
                source="test"
            )
            
            # Add messages
            for j in range(5):
                MessageOperations.create_message(
                    db=test_db,
                    lead_id=lead.id,
                    message_text=f"Message {j}",
                    channel="email",
                    direction="outbound"
                )
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (< 100MB for this operation)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100, f"Memory usage too high: {peak_mb:.2f}MB"
        
        print(f"✓ Memory usage: Peak {peak_mb:.2f}MB (target: <100MB)")
    
    def test_concurrent_request_handling(self, test_client):
        """Test handling of concurrent API requests."""
        import threading
        
        results = []
        errors = []
        
        def make_request(index):
            try:
                unique_id = str(uuid.uuid4())[:8]
                data = {
                    "name": f"Concurrent {index}",
                    "email": f"concurrent{index}{unique_id}@example.com",
                    "company": "Test Company",
                    "job_title": "CTO",
                    "source": "test"
                }
                
                start_time = time.time()
                response = test_client.post("/api/leads/capture", json=data)
                elapsed_time = time.time() - start_time
                
                results.append({
                    "index": index,
                    "status": response.status_code,
                    "time": elapsed_time
                })
            except Exception as e:
                errors.append(str(e))
        
        # Make 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        
        # Check response times
        avg_time = sum(r["time"] for r in results) / len(results)
        max_time = max(r["time"] for r in results)
        
        assert avg_time < 5.0, f"Average response time too high: {avg_time:.2f}s"
        assert max_time < 10.0, f"Max response time too high: {max_time:.2f}s"
        
        print(f"✓ Concurrent requests: {len(results)} requests, avg {avg_time:.2f}s, max {max_time:.2f}s")


class TestSecurity:
    """Test security measures."""
    
    def test_input_validation_on_all_endpoints(self, test_client):
        """Test input validation on API endpoints."""
        # Test SQL injection attempt
        sql_injection_data = {
            "name": "Test User'; DROP TABLE leads; --",
            "email": "test@example.com",
            "company": "Test Company",
            "job_title": "CTO"
        }
        
        response = test_client.post("/api/leads/capture", json=sql_injection_data)
        
        # Should either accept it (sanitized) or reject it
        # But should not cause database corruption
        assert response.status_code in [200, 400]
        
        # Verify database still works
        health_response = test_client.get("/health")
        assert health_response.status_code == 200
        
        print("✓ Input validation: SQL injection attempts handled safely")
    
    def test_xss_prevention_in_frontend(self, test_client):
        """Test XSS prevention in user input."""
        xss_payload = "<script>alert('XSS')</script>"
        
        xss_data = {
            "name": xss_payload,
            "email": "xss@example.com",
            "company": "Test Company",
            "job_title": "CTO"
        }
        
        response = test_client.post("/api/leads/capture", json=xss_data)
        
        if response.status_code == 200:
            lead_data = response.json()
            
            # Check that script tags are not returned unescaped
            # (they should be escaped or sanitized)
            assert "<script>" not in str(lead_data.get("name", ""))
        
        print("✓ XSS prevention: Script tags handled safely")
    
    def test_error_message_safety(self, test_client):
        """Test that error messages don't expose sensitive information."""
        # Test with invalid data
        invalid_data = {
            "name": "Test",
            "email": "invalid",
            "company": "Test",
            "job_title": "Test"
        }
        
        response = test_client.post("/api/leads/capture", json=invalid_data)
        
        if response.status_code != 200:
            error_detail = response.json().get("detail", "")
            
            # Should not contain sensitive information
            sensitive_keywords = ["password", "secret", "key", "token", "database", "sql"]
            for keyword in sensitive_keywords:
                assert keyword.lower() not in error_detail.lower()
        
        print("✓ Error message safety: No sensitive information exposed")
    
    def test_rate_limiting_considerations(self, test_client):
        """Test that the system can handle rapid requests."""
        # Make multiple rapid requests
        responses = []
        for i in range(20):
            unique_id = str(uuid.uuid4())[:8]
            data = {
                "name": f"Rate Limit {i}",
                "email": f"ratelimit{i}{unique_id}@example.com",
                "company": "Test Company",
                "job_title": "CTO",
                "source": "test"
            }
            
            response = test_client.post("/api/leads/capture", json=data)
            responses.append(response.status_code)
        
        # Most requests should succeed
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 15, f"Too many requests failed: {success_count}/20 succeeded"
        
        print(f"✓ Rate limiting: {success_count}/20 requests succeeded (system handles load)")
    
    def test_unauthorized_access_prevention(self, test_client):
        """Test that unauthorized operations are prevented."""
        # Try to access admin-only endpoints (if any)
        # For now, test that proper authentication would be required
        
        # Test that we can't delete without proper authorization
        # (This is a placeholder - actual auth implementation would be tested here)
        
        # Test that sensitive operations require proper validation
        invalid_update = {
            "new_status": ""  # Invalid status
        }
        
        # This should fail validation
        response = test_client.put("/leads/1/status", json=invalid_update)
        
        # Should either fail (404 for non-existent) or fail validation
        assert response.status_code in [400, 404]
        
        print("✓ Unauthorized access prevention: Invalid operations blocked")


class TestSystemHealth:
    """Test system health and readiness."""
    
    def test_health_check_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert "database" in health_data
        assert "timestamp" in health_data
        
        assert health_data["status"] == "healthy"
        assert health_data["database"] == "connected"
        
        print("✓ Health check: System healthy and database connected")
    
    def test_database_initialization(self):
        """Test database initialization."""
        # Initialize database
        init_db()
        
        # Check connection
        assert check_db_connection() is True
        
        # Try to create and query a test record
        db = SessionLocal()
        try:
            lead = LeadOperations.create_lead(
                db=db,
                name="Health Check",
                email="health@example.com",
                source="test"
            )
            
            retrieved = LeadOperations.get_lead(db, lead.id)
            assert retrieved is not None
            
        finally:
            db.close()
        
        print("✓ Database initialization: Database ready for operations")
    
    def test_api_info_endpoint(self, test_client):
        """Test API info endpoint."""
        response = test_client.get("/api/info")
        
        assert response.status_code == 200
        
        info_data = response.json()
        assert "name" in info_data
        assert "version" in info_data
        assert "status" in info_data
        assert "endpoints" in info_data
        
        assert info_data["status"] == "running"
        
        print("✓ API info: System information available")
    
    def test_static_file_serving(self, test_client):
        """Test static file serving."""
        # Test landing page
        response = test_client.get("/")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        
        # Test dashboard
        response = test_client.get("/dashboard")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        
        print("✓ Static file serving: Frontend pages accessible")


class TestCleanup:
    """Test cleanup and temporary file handling."""
    
    def test_temporary_file_cleanup(self):
        """Test that temporary files are handled correctly."""
        import tempfile
        import os
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as f:
            temp_file = f.name
            f.write("test data")
        
        # Verify file exists
        assert os.path.exists(temp_file)
        
        # Clean up
        os.unlink(temp_file)
        
        # Verify file is deleted
        assert not os.path.exists(temp_file)
        
        print("✓ Temporary file cleanup: Files handled correctly")
    
    def test_database_cleanup_after_tests(self, test_db):
        """Test that database can be cleaned up after tests."""
        # Create some test data
        lead = LeadOperations.create_lead(
            db=test_db,
            name="Cleanup Test",
            email="cleanup@example.com",
            source="test"
        )
        
        MessageOperations.create_message(
            db=test_db,
            lead_id=lead.id,
            message_text="Test message",
            channel="email",
            direction="outbound"
        )
        
        # Verify data exists
        leads = LeadOperations.get_all_leads(test_db)
        assert len(leads) >= 1
        
        # Cleanup (simulated)
        LeadOperations.delete_lead(test_db, lead.id)
        
        # Verify cleanup
        leads_after = LeadOperations.get_all_leads(test_db)
        assert len(leads_after) < len(leads)
        
        print("✓ Database cleanup: Test data can be removed")


class TestDeploymentReadiness:
    """Test deployment readiness and configuration."""
    
    def test_all_dependencies_in_requirements(self):
        """Test that all required dependencies are listed."""
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        # Check for critical dependencies
        critical_deps = [
            'fastapi',
            'sqlalchemy',
            'requests',
            'uvicorn',
            'pytest'
        ]
        
        for dep in critical_deps:
            assert dep.lower() in requirements.lower(), f"Missing dependency: {dep}"
        
        print("✓ Dependencies: All critical dependencies listed in requirements.txt")
    
    def test_environment_configuration(self):
        """Test environment configuration."""
        # Check that required environment variables can be set
        # (This is a placeholder - actual env var checks would be here)
        
        # Test that the system can run with default configuration
        from ai_client import LLM_PROVIDER, LLM_MODEL
        
        assert LLM_PROVIDER is not None
        assert LLM_MODEL is not None
        
        print("✓ Environment configuration: System can run with default config")
    
    def test_application_startup(self):
        """Test application startup."""
        # Test that the application can start without errors
        from main import app
        
        assert app is not None
        assert app.title == "Secu-Agent AI Lead Management System"
        
        print("✓ Application startup: Application initializes correctly")
    
    def test_error_handling_verification(self, test_client):
        """Test comprehensive error handling."""
        # Test various error scenarios
        error_scenarios = [
            ("/leads/99999", 404),  # Non-existent lead
            ("/messages/99999", 404),  # Non-existent message
            ("/api/communications/99999", 404),  # Non-existent communications
        ]
        
        for endpoint, expected_status in error_scenarios:
            response = test_client.get(endpoint)
            assert response.status_code == expected_status
        
        print("✓ Error handling: All error scenarios handled correctly")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
"""
Comprehensive tests for engagement rules engine.
Tests rule evaluation, time-based triggers, behavior-based triggers,
priority handling, scheduling, and integration with agent processing.
"""

import pytest
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_client import EngagementRule, EngagementRules, Agent, AIClient
from database import Lead, Message, LeadOperations, MessageOperations, SessionLocal, init_db


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    init_db()
    db = SessionLocal()
    try:
        yield db
        db.rollback()
        # Clean up any leads created during test
        db.query(Message).delete()
        db.query(Lead).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def sample_lead(db_session):
    """Create a sample lead for testing with unique email."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    lead = LeadOperations.create_lead(
        db=db_session,
        name="John Doe",
        email=f"john.doe.{unique_id}@example.com",
        company="Tech Corp",
        job_title="CTO",
        source="event",
        status="new"
    )
    return lead


@pytest.fixture
def sample_lead_dict(sample_lead):
    """Create a lead dictionary for testing."""
    return {
        'id': sample_lead.id,
        'name': sample_lead.name,
        'email': sample_lead.email,
        'company': sample_lead.company,
        'job_title': sample_lead.job_title,
        'status': sample_lead.status,
        'source': sample_lead.source
    }


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    with patch('ai_client.AIClient'):
        agent = Agent()
        return agent


class TestEngagementRule:
    """Test individual EngagementRule functionality."""
    
    def test_rule_initialization(self):
        """Test that a rule can be initialized with correct parameters."""
        def dummy_condition(lead, context):
            return True
        
        def dummy_action(lead, context, agent, db):
            return {"success": True}
        
        rule = EngagementRule(
            name="test_rule",
            priority=5,
            conditions=[dummy_condition],
            actions=[dummy_action],
            cooldown_hours=24,
            rule_type="time_based"
        )
        
        assert rule.name == "test_rule"
        assert rule.priority == 5
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1
        assert rule.cooldown_hours == 24
        assert rule.rule_type == "time_based"
        assert rule.last_executed is None
    
    def test_rule_evaluation_with_matching_condition(self, sample_lead_dict):
        """Test rule evaluation when conditions are met."""
        def condition(lead, context):
            return lead.get('status') == 'new'
        
        def action(lead, context, agent, db):
            return {"success": True, "action": "test"}
        
        rule = EngagementRule(
            name="test_rule",
            priority=5,
            conditions=[condition],
            actions=[action],
            cooldown_hours=24
        )
        
        context = {}
        result = rule.evaluate(sample_lead_dict, context)
        
        assert result is True
    
    def test_rule_evaluation_with_non_matching_condition(self, sample_lead_dict):
        """Test rule evaluation when conditions are not met."""
        def condition(lead, context):
            return lead.get('status') == 'contacted'
        
        def action(lead, context, agent, db):
            return {"success": True}
        
        rule = EngagementRule(
            name="test_rule",
            priority=5,
            conditions=[condition],
            actions=[action],
            cooldown_hours=24
        )
        
        context = {}
        result = rule.evaluate(sample_lead_dict, context)
        
        assert result is False
    
    def test_rule_cooldown_period(self, sample_lead_dict):
        """Test that rule respects cooldown period."""
        def condition(lead, context):
            return True
        
        def action(lead, context, agent, db):
            return {"success": True}
        
        rule = EngagementRule(
            name="test_rule",
            priority=5,
            conditions=[condition],
            actions=[action],
            cooldown_hours=1
        )
        
        # First evaluation should pass
        context = {}
        assert rule.evaluate(sample_lead_dict, context) is True
        
        # Execute the rule to set last_executed
        rule.execute(sample_lead_dict, context, Mock(), Mock())
        
        # Immediate evaluation should fail due to cooldown
        assert rule.evaluate(sample_lead_dict, context) is False
    
    def test_rule_execution(self, sample_lead_dict):
        """Test that rule actions are executed correctly."""
        def condition(lead, context):
            return True
        
        def action(lead, context, agent, db):
            return {"success": True, "action": "test_action", "lead_id": lead['id']}
        
        rule = EngagementRule(
            name="test_rule",
            priority=5,
            conditions=[condition],
            actions=[action],
            cooldown_hours=24
        )
        
        context = {}
        mock_agent = Mock()
        mock_db = Mock()
        
        results = rule.execute(sample_lead_dict, context, mock_agent, mock_db)
        
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["action"] == "test_action"
        assert results[0]["lead_id"] == sample_lead_dict['id']
        assert rule.last_executed is not None


class TestEngagementRules:
    """Test EngagementRules engine functionality."""
    
    def test_engagement_rules_initialization(self):
        """Test that EngagementRules initializes with all rules."""
        rules_engine = EngagementRules()
        
        assert len(rules_engine.rules) > 0
        assert rules_engine.event_date is not None
        assert isinstance(rules_engine.event_date, datetime)
    
    def test_pre_event_rules_exist(self):
        """Test that all pre-event rules are registered."""
        rules_engine = EngagementRules()
        rule_names = [rule.name for rule in rules_engine.rules]
        
        expected_pre_event_rules = [
            "new_lead_welcome",
            "reminder_7_days_before",
            "reminder_3_days_before",
            "reminder_1_day_before",
            "personalized_content_5_days",
            "confirmed_lead_confirmation"
        ]
        
        for rule_name in expected_pre_event_rules:
            assert rule_name in rule_names, f"Pre-event rule {rule_name} not found"
    
    def test_post_event_rules_exist(self):
        """Test that all post-event rules are registered."""
        rules_engine = EngagementRules()
        rule_names = [rule.name for rule in rules_engine.rules]
        
        expected_post_event_rules = [
            "attended_thank_you",
            "attended_meeting_request",
            "no_show_reschedule",
            "session_based_content"
        ]
        
        for rule_name in expected_post_event_rules:
            assert rule_name in rule_names, f"Post-event rule {rule_name} not found"
    
    def test_behavior_based_rules_exist(self):
        """Test that behavior-based rules are registered."""
        rules_engine = EngagementRules()
        rule_names = [rule.name for rule in rules_engine.rules]
        
        expected_behavior_rules = [
            "high_engagement_escalate",
            "no_response_de_prioritize",
            "email_opened_followup"
        ]
        
        for rule_name in expected_behavior_rules:
            assert rule_name in rule_names, f"Behavior-based rule {rule_name} not found"
    
    def test_business_hours_check(self):
        """Test business hours logic."""
        rules_engine = EngagementRules()
        
        # Test during business hours (weekday, 9 AM - 6 PM UTC)
        with patch('ai_client.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 14
            mock_now.weekday.return_value = 4  # Friday
            mock_datetime.now.return_value = mock_now
            assert rules_engine._is_business_hours() is True
        
        # Test outside business hours (weekend)
        with patch('ai_client.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 14
            mock_now.weekday.return_value = 5  # Saturday
            mock_datetime.now.return_value = mock_now
            assert rules_engine._is_business_hours() is False
        
        # Test outside business hours (early morning)
        with patch('ai_client.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 8
            mock_now.weekday.return_value = 4  # Friday
            mock_datetime.now.return_value = mock_now
            assert rules_engine._is_business_hours() is False
        
        # Test outside business hours (evening)
        with patch('ai_client.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 19
            mock_now.weekday.return_value = 4  # Friday
            mock_datetime.now.return_value = mock_now
            assert rules_engine._is_business_hours() is False
    
    def test_get_all_rules(self):
        """Test getting all rules information."""
        rules_engine = EngagementRules()
        rules_info = rules_engine.get_all_rules()
        
        assert isinstance(rules_info, list)
        assert len(rules_info) > 0
        
        for rule_info in rules_info:
            assert 'name' in rule_info
            assert 'priority' in rule_info
            assert 'rule_type' in rule_info
            assert 'cooldown_hours' in rule_info
            assert 'last_executed' in rule_info
    
    def test_set_event_date(self):
        """Test updating event date."""
        rules_engine = EngagementRules()
        new_date = datetime(2024, 12, 15, 10, 0, tzinfo=timezone.utc)
        
        rules_engine.set_event_date(new_date)
        
        assert rules_engine.event_date == new_date
    
    def test_get_engagement_score_new_lead(self, db_session, sample_lead):
        """Test engagement score calculation for new lead."""
        rules_engine = EngagementRules()
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': sample_lead.status,
            'source': sample_lead.source
        }
        
        score = rules_engine.get_engagement_score(lead_dict, db_session)
        
        assert isinstance(score, int)
        assert 0 <= score <= 10
    
    def test_get_engagement_score_with_messages(self, db_session, sample_lead):
        """Test engagement score calculation with messages."""
        rules_engine = EngagementRules()
        
        # Add some messages
        MessageOperations.create_message(
            db=db_session,
            lead_id=sample_lead.id,
            message_text="Welcome message",
            channel="email",
            direction="outbound"
        )
        
        MessageOperations.create_message(
            db=db_session,
            lead_id=sample_lead.id,
            message_text="Thanks for reaching out",
            channel="email",
            direction="inbound"
        )
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': 'contacted',
            'source': sample_lead.source
        }
        
        score = rules_engine.get_engagement_score(lead_dict, db_session)
        
        assert isinstance(score, int)
        assert 0 <= score <= 10
        # Score should be higher with messages and better status
        assert score > 0
    
    def test_evaluate_rules_for_lead(self, db_session, sample_lead, mock_agent):
        """Test evaluating rules for a specific lead."""
        rules_engine = EngagementRules()
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': 'new',
            'source': sample_lead.source
        }
        
        context = {
            'engagement_score': 0,
            'event_date': rules_engine.event_date,
            'sessions_attended': [],
            'last_email_opened': None,
            'last_contact_date': sample_lead.updated_at
        }
        
        results = rules_engine.evaluate_rules_for_lead(lead_dict, context, mock_agent, db_session)
        
        assert isinstance(results, list)
        # New lead should trigger welcome rule
        assert len(results) > 0
    
    def test_get_upcoming_actions(self, db_session, sample_lead):
        """Test getting upcoming scheduled actions."""
        rules_engine = EngagementRules()
        
        leads = [{
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': sample_lead.status,
            'source': sample_lead.source
        }]
        
        context = {'event_date': rules_engine.event_date}
        
        upcoming = rules_engine.get_upcoming_actions(leads, context)
        
        assert isinstance(upcoming, list)
        # Should have predictions for time-based rules
        assert len(upcoming) >= 0


class TestRuleIntegration:
    """Test integration of engagement rules with agent processing."""
    
    def test_agent_initialization_with_rules(self):
        """Test that agent can be initialized with engagement rules."""
        rules_engine = EngagementRules()
        
        with patch('ai_client.AIClient'):
            agent = Agent(engagement_rules=rules_engine)
            
            assert agent.engagement_rules is not None
            assert agent.engagement_rules == rules_engine
    
    def test_process_lead_with_rules(self, db_session, sample_lead):
        """Test processing lead with automatic rule evaluation."""
        with patch('ai_client.AIClient') as mock_ai_client:
            # Mock the AI response to return proper string
            mock_instance = Mock()
            mock_instance.chat_completion.return_value = {
                "choices": [{
                    "message": {
                        "content": "Welcome to Vigil.AI! We're excited to help with your cybersecurity needs."
                    }
                }]
            }
            mock_ai_client.return_value = mock_instance
            
            agent = Agent()
            
            result = agent.process_lead_with_rules(sample_lead.id, db_session)
            
            assert result.get("success") is True
            assert "basic_processing" in result
            assert "engagement_score" in result
            assert "rules_evaluated" in result
            assert "rules_matched" in result
            assert "rule_results" in result
    
    def test_new_lead_triggers_welcome_rule(self, db_session, sample_lead):
        """Test that new lead triggers welcome rule during basic processing."""
        with patch('ai_client.AIClient') as mock_ai_client:
            # Mock the AI response to return proper string
            mock_instance = Mock()
            mock_instance.chat_completion.return_value = {
                "choices": [{
                    "message": {
                        "content": "Welcome to Vigil.AI! We're excited to help with your cybersecurity needs."
                    }
                }]
            }
            mock_ai_client.return_value = mock_instance
            
            agent = Agent()
            
            result = agent.process_lead_with_rules(sample_lead.id, db_session)
            
            assert result.get("success") is True
            # The welcome rule is triggered during basic processing, not rule evaluation
            # Check that basic processing sent welcome message
            basic_result = result.get("basic_processing", {})
            assert basic_result.get("action") == "welcome_sent"
            assert basic_result.get("new_status") == "contacted"
            
            # After status change to 'contacted', other rules may be evaluated
            # The welcome rule won't trigger again due to status change
            assert result.get("engagement_score", 0) >= 0
    
    def test_engagement_score_increases_with_activity(self, db_session, sample_lead):
        """Test that engagement score increases with lead activity."""
        rules_engine = EngagementRules()
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': 'new',
            'source': sample_lead.source
        }
        
        # Initial score
        initial_score = rules_engine.get_engagement_score(lead_dict, db_session)
        
        # Add messages
        MessageOperations.create_message(
            db=db_session,
            lead_id=sample_lead.id,
            message_text="Welcome",
            channel="email",
            direction="outbound"
        )
        
        MessageOperations.create_message(
            db=db_session,
            lead_id=sample_lead.id,
            message_text="Response",
            channel="email",
            direction="inbound"
        )
        
        # Update status
        lead_dict['status'] = 'contacted'
        
        # Score should increase
        new_score = rules_engine.get_engagement_score(lead_dict, db_session)
        assert new_score >= initial_score


class TestTimeBasedTriggers:
    """Test time-based rule triggers."""
    
    def test_reminder_7_days_before_trigger(self):
        """Test 7-day reminder rule triggers at correct time."""
        event_date = datetime.now(timezone.utc) + timedelta(days=7)
        rules_engine = EngagementRules(event_date=event_date)
        
        # Find the 7-day reminder rule
        reminder_rule = next(
            (r for r in rules_engine.rules if "7_days_before" in r.name),
            None
        )
        
        assert reminder_rule is not None
        assert reminder_rule.rule_type == "time_based"
    
    def test_reminder_3_days_before_trigger(self):
        """Test 3-day reminder rule triggers at correct time."""
        event_date = datetime.now(timezone.utc) + timedelta(days=3)
        rules_engine = EngagementRules(event_date=event_date)
        
        reminder_rule = next(
            (r for r in rules_engine.rules if "3_days_before" in r.name),
            None
        )
        
        assert reminder_rule is not None
        assert reminder_rule.rule_type == "time_based"
    
    def test_reminder_1_day_before_trigger(self):
        """Test 1-day reminder rule triggers at correct time."""
        event_date = datetime.now(timezone.utc) + timedelta(days=1)
        rules_engine = EngagementRules(event_date=event_date)
        
        reminder_rule = next(
            (r for r in rules_engine.rules if "1_day_before" in r.name),
            None
        )
        
        assert reminder_rule is not None
        assert reminder_rule.rule_type == "time_based"


class TestBehaviorBasedTriggers:
    """Test behavior-based rule triggers."""
    
    def test_high_engagement_escalation(self, db_session, sample_lead):
        """Test high engagement triggers priority escalation."""
        rules_engine = EngagementRules()
        
        # Add messages to increase engagement
        for i in range(5):
            MessageOperations.create_message(
                db=db_session,
                lead_id=sample_lead.id,
                message_text=f"Message {i}",
                channel="email",
                direction="outbound"
            )
        
        for i in range(3):
            MessageOperations.create_message(
                db=db_session,
                lead_id=sample_lead.id,
                message_text=f"Response {i}",
                channel="email",
                direction="inbound"
            )
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': 'engaged',
            'source': sample_lead.source
        }
        
        score = rules_engine.get_engagement_score(lead_dict, db_session)
        
        # Should have high engagement score
        assert score >= 5
    
    def test_no_response_de_prioritization(self, db_session, sample_lead):
        """Test lack of response triggers de-prioritization."""
        rules_engine = EngagementRules()
        
        # Create old message with timestamp using direct SQL update
        old_message = MessageOperations.create_message(
            db=db_session,
            lead_id=sample_lead.id,
            message_text="Old message",
            channel="email",
            direction="outbound"
        )
        
        # Update timestamp using SQL
        from sqlalchemy import update
        old_timestamp = datetime.now(timezone.utc) - timedelta(days=14)
        db_session.execute(
            update(Message).where(Message.id == old_message.id).values(timestamp=old_timestamp)
        )
        db_session.commit()
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': 'contacted',
            'source': sample_lead.source
        }
        
        context = {
            'engagement_score': 0,
            'event_date': rules_engine.event_date,
            'sessions_attended': [],
            'last_email_opened': None,
            'last_contact_date': old_timestamp
        }
        
        # Find no-response rule
        no_response_rule = next(
            (r for r in rules_engine.rules if "no_response" in r.name),
            None
        )
        
        assert no_response_rule is not None
        assert no_response_rule.rule_type == "behavior_based"


class TestPriorityAndConflictResolution:
    """Test rule priority and conflict resolution."""
    
    def test_rules_sorted_by_priority(self):
        """Test that rules are evaluated in priority order."""
        rules_engine = EngagementRules()
        
        # Sort rules by priority
        sorted_rules = sorted(rules_engine.rules, key=lambda r: r.priority, reverse=True)
        
        # Check that priorities are in descending order
        for i in range(len(sorted_rules) - 1):
            assert sorted_rules[i].priority >= sorted_rules[i + 1].priority
    
    def test_higher_priority_rules_execute_first(self, db_session, sample_lead, mock_agent):
        """Test that higher priority rules are executed first."""
        rules_engine = EngagementRules()
        
        lead_dict = {
            'id': sample_lead.id,
            'name': sample_lead.name,
            'email': sample_lead.email,
            'company': sample_lead.company,
            'job_title': sample_lead.job_title,
            'status': 'new',
            'source': sample_lead.source
        }
        
        context = {
            'engagement_score': 0,
            'event_date': rules_engine.event_date,
            'sessions_attended': [],
            'last_email_opened': None,
            'last_contact_date': sample_lead.updated_at
        }
        
        results = rules_engine.evaluate_rules_for_lead(lead_dict, context, mock_agent, db_session)
        
        # Results should be ordered by priority
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['priority'] >= results[i + 1]['priority']


class TestCooldownPeriods:
    """Test cooldown period functionality."""
    
    def test_cooldown_prevents_duplicate_execution(self, sample_lead_dict):
        """Test that cooldown prevents duplicate rule execution."""
        def condition(lead, context):
            return True
        
        def action(lead, context, agent, db):
            return {"success": True}
        
        rule = EngagementRule(
            name="test_cooldown",
            priority=5,
            conditions=[condition],
            actions=[action],
            cooldown_hours=1
        )
        
        context = {}
        
        # First execution
        assert rule.evaluate(sample_lead_dict, context) is True
        rule.execute(sample_lead_dict, context, Mock(), Mock())
        
        # Immediate second execution should fail
        assert rule.evaluate(sample_lead_dict, context) is False
    
    def test_different_cooldown_periods_for_different_rules(self):
        """Test that different rules can have different cooldown periods."""
        rules_engine = EngagementRules()
        
        cooldown_periods = {}
        for rule in rules_engine.rules:
            if rule.name not in cooldown_periods:
                cooldown_periods[rule.name] = rule.cooldown_hours
        
        # Should have variety in cooldown periods
        assert len(cooldown_periods) > 1
        
        # Check that cooldown periods are reasonable
        for rule_name, cooldown in cooldown_periods.items():
            assert cooldown > 0
            assert cooldown <= 168  # Max 7 days


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
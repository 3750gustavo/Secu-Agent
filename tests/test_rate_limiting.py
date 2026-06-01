"""
Comprehensive tests for AI rate limiting and scheduling system.
Tests global semaphore, request queuing, priority scheduling, logging, and cooldown system.
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_client import (
    call_llm_with_limit,
    _call_llm_internal,
    _ai_semaphore,
    _scheduled_tasks,
    _scheduled_tasks_lock,
    _scheduler_running,
    PRIORITY_IMMEDIATE,
    PRIORITY_SCHEDULED,
    is_off_peak_hours,
    get_brt_timestamp,
    get_caller_context,
    start_scheduler
)


import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def reset_ai_client_state():
    """Reset AI client global state before each test."""
    global _consecutive_errors, _error_cooldown_until, _scheduled_tasks, _scheduler_running
    
    # Reset error tracking
    _consecutive_errors = 0
    _error_cooldown_until = None
    
    # Reset scheduled tasks
    async with _scheduled_tasks_lock:
        _scheduled_tasks.clear()
    
    # Reset scheduler
    _scheduler_running = False
    
    yield
    
    # Cleanup after test
    _scheduler_running = False


class TestGlobalSemaphore:
    """Test global semaphore behavior for AI rate limiting."""
    
    @pytest.mark.asyncio
    async def test_single_request_acquires_semaphore(self):
        """Test that a single request can acquire the semaphore."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            mock_llm.return_value = "Test response"
            
            result = await call_llm_with_limit(
                "Test system prompt",
                "Test user message",
                reason="test_single_request"
            )
            
            assert result == "Test response"
            mock_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_are_serialized(self):
        """Test that concurrent requests are serialized by the semaphore."""
        call_order = []
        
        async def mock_llm_with_delay(system_prompt, user_message, history=None):
            # Simulate AI API delay
            await asyncio.sleep(0.1)
            call_order.append(time.time())
            return f"Response at {time.time()}"
        
        with patch('ai_client._call_llm_internal', side_effect=mock_llm_with_delay):
            # Launch 3 concurrent requests
            tasks = [
                call_llm_with_limit(f"Prompt {i}", f"Message {i}", reason=f"test_concurrent_{i}")
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All requests should complete
            assert len(results) == 3
            
            # Requests should be serialized (not parallel)
            # Time differences should be at least 0.1s between each
            assert len(call_order) == 3
            for i in range(1, len(call_order)):
                assert call_order[i] - call_order[i-1] >= 0.1
    
    @pytest.mark.asyncio
    async def test_semaphore_released_on_error(self):
        """Test that semaphore is released even when request fails."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            mock_llm.side_effect = Exception("API error")
            
            with pytest.raises(Exception):
                await call_llm_with_limit(
                    "Test prompt",
                    "Test message",
                    reason="test_error"
                )
            
            # Semaphore should be available for next request
            with patch('ai_client._call_llm_internal') as mock_llm2:
                mock_llm2.return_value = "Recovery response"
                result = await call_llm_with_limit(
                    "Recovery prompt",
                    "Recovery message",
                    reason="test_recovery"
                )
                assert result == "Recovery response"


class TestPriorityScheduling:
    """Test priority-based scheduling system."""
    
    @pytest.mark.asyncio
    async def test_immediate_priority_executes_now(self):
        """Test that immediate priority requests execute immediately."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            mock_llm.return_value = "Immediate response"
            
            result = await call_llm_with_limit(
                "Test prompt",
                "Test message",
                reason="test_immediate",
                priority=PRIORITY_IMMEDIATE
            )
            
            assert result == "Immediate response"
            mock_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scheduled_priority_queues_task(self):
        """Test that scheduled priority requests are queued."""
        initial_queue_length = len(_scheduled_tasks)
        
        with patch('ai_client._call_llm_internal') as mock_llm:
            mock_llm.return_value = "Should not execute"
            
            result = await call_llm_with_limit(
                "Test prompt",
                "Test message",
                reason="test_scheduled",
                priority=PRIORITY_SCHEDULED
            )
            
            # Should return empty string for scheduled tasks
            assert result == ""
            
            # Should not execute immediately
            mock_llm.assert_not_called()
            
            # Should be added to queue
            async with _scheduled_tasks_lock:
                assert len(_scheduled_tasks) == initial_queue_length + 1
    
    @pytest.mark.asyncio
    async def test_scheduler_processes_off_peak_tasks(self):
        """Test that scheduler processes tasks during off-peak hours."""
        # Add a task to the queue
        async with _scheduled_tasks_lock:
            _scheduled_tasks.append({
                'func': MagicMock(return_value="Scheduled response"),
                'args': (),
                'kwargs': {},
                'reason': "test_scheduler",
                'queued_at': get_brt_timestamp(),
                'caller': "test"
            })
        
        # Mock is_off_peak_hours to return True
        with patch('ai_client.is_off_peak_hours', return_value=True):
            # Run one iteration of scheduler
            await start_scheduler()
            
            # Give scheduler time to process
            await asyncio.sleep(0.1)
            
            # Task should be processed
            async with _scheduled_tasks_lock:
                # Queue should be empty or reduced
                assert len(_scheduled_tasks) == 0


class TestLoggingAndContext:
    """Test logging with BRT timestamps and caller context."""
    
    def test_brt_timestamp_format(self):
        """Test that BRT timestamp is correctly formatted."""
        timestamp = get_brt_timestamp()
        
        # Should contain date and time
        assert len(timestamp) > 0
        # BRT timezone can be "BRT", "-03", or "-03:00"
        assert "BRT" in timestamp or "-03" in timestamp
    
    def test_caller_context_detection(self):
        """Test that caller context is correctly detected."""
        context = get_caller_context()
        
        # Should contain filename and function name
        assert len(context) > 0
        assert ":" in context  # Should have format filename:function:line
    
    @pytest.mark.asyncio
    async def test_logging_includes_context(self, caplog):
        """Test that AI requests log with proper context."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            mock_llm.return_value = "Test response"
            
            with caplog.at_level('INFO'):
                await call_llm_with_limit(
                    "Test prompt",
                    "Test message",
                    reason="test_logging"
                )
            
            # Check that logs contain expected information
            log_messages = [record.message for record in caplog.records]
            
            # Should have queued, starting, and completed logs
            assert any("QUEUED" in msg for msg in log_messages)
            assert any("STARTING" in msg for msg in log_messages)
            assert any("COMPLETED" in msg for msg in log_messages)
            
            # Should contain reason and caller context
            assert any("test_logging" in msg for msg in log_messages)


class TestOffPeakHours:
    """Test off-peak hours detection."""
    
    def test_is_off_peak_hours_returns_bool(self):
        """Test that off-peak hours check returns boolean."""
        result = is_off_peak_hours()
        assert isinstance(result, bool)
    
    @patch('ai_client.datetime')
    def test_off_peak_hours_2am_to_6am(self, mock_datetime):
        """Test that 2am-6am BRT is considered off-peak."""
        from ai_client import BRT_TZ
        
        # Test 2am (should be off-peak)
        mock_datetime.now.return_value.hour = 2
        assert is_off_peak_hours() is True
        
        # Test 4am (should be off-peak)
        mock_datetime.now.return_value.hour = 4
        assert is_off_peak_hours() is True
        
        # Test 6am (should NOT be off-peak)
        mock_datetime.now.return_value.hour = 6
        assert is_off_peak_hours() is False
        
        # Test 1am (should NOT be off-peak)
        mock_datetime.now.return_value.hour = 1
        assert is_off_peak_hours() is False


class TestErrorHandling:
    """Test error handling in rate limiting system."""
    
    @pytest.mark.asyncio
    async def test_api_error_logged_correctly(self, caplog):
        """Test that API errors are logged with proper context."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            mock_llm.side_effect = Exception("API failure")
            
            with caplog.at_level('ERROR'):
                with pytest.raises(Exception):
                    await call_llm_with_limit(
                        "Test prompt",
                        "Test message",
                        reason="test_error_logging"
                    )
            
            # Should log error with context
            error_logs = [record.message for record in caplog.records if record.levelname == 'ERROR']
            assert len(error_logs) > 0
            assert any("FAILED" in msg for msg in error_logs)
            assert any("test_error_logging" in msg for msg in error_logs)
    
    @pytest.mark.asyncio
    async def test_semaphore_available_after_error(self):
        """Test that semaphore remains available after error."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            # First request fails
            mock_llm.side_effect = Exception("First error")
            
            with pytest.raises(Exception):
                await call_llm_with_limit("Prompt1", "Message1", reason="error1")
            
            # Second request should succeed
            mock_llm.side_effect = None
            mock_llm.return_value = "Success"
            
            result = await call_llm_with_limit("Prompt2", "Message2", reason="success")
            assert result == "Success"


class TestCooldownSystem:
    """Test cooldown system after consecutive errors."""
    
    @pytest.mark.asyncio
    async def test_single_error_does_not_trigger_cooldown(self):
        """Test that a single error doesn't trigger cooldown."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            # First request fails
            mock_llm.side_effect = Exception("First error")
            
            with pytest.raises(Exception):
                await call_llm_with_limit("Prompt1", "Message1", reason="error1")
            
            # Second request should still work (not in cooldown)
            mock_llm.side_effect = None
            mock_llm.return_value = "Success"
            
            result = await call_llm_with_limit("Prompt2", "Message2", reason="success")
            assert result == "Success"
    
    @pytest.mark.asyncio
    async def test_three_consecutive_errors_trigger_cooldown(self):
        """Test that 3 consecutive errors trigger 1-hour cooldown."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            # Make 3 requests fail
            for i in range(3):
                mock_llm.side_effect = Exception(f"Error {i}")
                with pytest.raises(Exception):
                    await call_llm_with_limit(f"Prompt{i}", f"Message{i}", reason=f"error_{i}")
            
            # 4th request should be rejected due to cooldown
            mock_llm.side_effect = None
            mock_llm.return_value = "Should not execute"
            
            with pytest.raises(Exception) as exc_info:
                await call_llm_with_limit("Prompt4", "Message4", reason="cooldown_test")
            
            assert "cooldown" in str(exc_info.value).lower()
            mock_llm.assert_not_called()  # Should not execute
    
    @pytest.mark.asyncio
    async def test_successful_request_resets_error_counter(self):
        """Test that successful request resets consecutive error counter."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            # First request fails
            mock_llm.side_effect = Exception("First error")
            with pytest.raises(Exception):
                await call_llm_with_limit("Prompt1", "Message1", reason="error1")
            
            # Second request succeeds
            mock_llm.side_effect = None
            mock_llm.return_value = "Success"
            result = await call_llm_with_limit("Prompt2", "Message2", reason="success")
            assert result == "Success"
            
            # Third request fails (should not trigger cooldown since counter was reset)
            mock_llm.side_effect = Exception("Third error")
            with pytest.raises(Exception):
                await call_llm_with_limit("Prompt3", "Message3", reason="error3")
            
            # Fourth request should still work (only 1 consecutive error)
            mock_llm.side_effect = None
            mock_llm.return_value = "Another success"
            result = await call_llm_with_limit("Prompt4", "Message4", reason="success2")
            assert result == "Another success"
    
    @pytest.mark.asyncio
    async def test_cooldown_prevents_shadowban(self, caplog):
        """Test that cooldown prevents spamming errors to avoid shadowban."""
        with patch('ai_client._call_llm_internal') as mock_llm:
            # Simulate model being down (all requests fail)
            mock_llm.side_effect = Exception("Model unavailable")
            
            with caplog.at_level('CRITICAL'):
                # Try to make 10 requests
                for i in range(10):
                    with pytest.raises(Exception):
                        await call_llm_with_limit(f"Prompt{i}", f"Message{i}", reason=f"spam_{i}")
            
            # Should have cooldown activation log
            critical_logs = [record.message for record in caplog.records if record.levelname == 'CRITICAL']
            assert len(critical_logs) > 0
            assert any("COOLDOWN ACTIVATED" in msg for msg in critical_logs)
            
            # After cooldown, only 3 actual API calls should have been made
            assert mock_llm.call_count == 3


class TestIntegration:
    """Integration tests for the complete rate limiting system."""
    
    @pytest.mark.asyncio
    async def test_mixed_priority_requests(self):
        """Test handling of mixed immediate and scheduled requests."""
        immediate_results = []
        scheduled_count = [0]
        
        async def mock_llm(system_prompt, user_message, history=None):
            await asyncio.sleep(0.05)
            return f"Response: {user_message}"
        
        with patch('ai_client._call_llm_internal', side_effect=mock_llm):
            # Mix of immediate and scheduled requests
            tasks = []
            
            # Add immediate requests
            for i in range(2):
                task = call_llm_with_limit(
                    f"Immediate {i}",
                    f"Message {i}",
                    reason=f"immediate_{i}",
                    priority=PRIORITY_IMMEDIATE
                )
                tasks.append(task)
            
            # Add scheduled requests
            for i in range(2):
                task = call_llm_with_limit(
                    f"Scheduled {i}",
                    f"Message {i}",
                    reason=f"scheduled_{i}",
                    priority=PRIORITY_SCHEDULED
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # Immediate requests should have results
            immediate_results = [r for r in results[:2] if r]
            assert len(immediate_results) == 2
            
            # Scheduled requests should return empty strings
            scheduled_results = results[2:]
            assert all(r == "" for r in scheduled_results)
            
            # Scheduled tasks should be in queue
            async with _scheduled_tasks_lock:
                assert len(_scheduled_tasks) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
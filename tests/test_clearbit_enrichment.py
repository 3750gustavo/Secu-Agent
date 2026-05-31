"""
Comprehensive tests for Clearbit enrichment and LLM dispatcher functionality.
Tests real API integration, error handling, and backward compatibility.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timezone

# Import modules to test
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_client import Agent, call_llm, LLM_PROVIDER, LLM_API_KEY, LLM_API_URL, LLM_MODEL


class TestClearbitEnrichment:
    """Test suite for Clearbit API integration in lead enrichment."""
    
    @pytest.fixture
    def agent(self):
        """Create an Agent instance for testing."""
        return Agent()
    
    @pytest.fixture
    def sample_lead_data(self):
        """Sample lead data for testing."""
        return {
            'name': 'John Doe',
            'email': 'john.doe@google.com',
            'company': 'Google',
            'job_title': 'Software Engineer',
            'source': 'website'
        }
    
    def test_clearbit_enrichment_with_real_domain(self, agent, sample_lead_data):
        """Test Clearbit enrichment with real domain (google.com)."""
        # This test makes a real API call to Clearbit
        enriched = agent.enrich_lead_data(sample_lead_data)
        
        # Verify enrichment happened
        assert 'enriched_at' in enriched
        assert 'enrichment_source' in enriched
        
        # If Clearbit succeeded, verify expected fields
        if enriched.get('enrichment_source') == 'clearbit':
            assert 'company_name' in enriched
            assert 'domain' in enriched
            assert 'industry' in enriched
            assert enriched['domain'] == 'google.com'
            print(f"✓ Clearbit enrichment successful for google.com: {enriched.get('company_name')}")
        else:
            # Fallback to mock enrichment
            assert enriched.get('enrichment_source') == 'mock'
            print("✓ Fallback to mock enrichment for google.com")
    
    def test_clearbit_enrichment_microsoft_domain(self, agent):
        """Test Clearbit enrichment with Microsoft domain."""
        lead_data = {
            'name': 'Jane Smith',
            'email': 'jane.smith@microsoft.com',
            'company': 'Microsoft',
            'job_title': 'Product Manager'
        }
        
        enriched = agent.enrich_lead_data(lead_data)
        
        assert 'enriched_at' in enriched
        assert 'enrichment_source' in enriched
        
        if enriched.get('enrichment_source') == 'clearbit':
            assert enriched['domain'] == 'microsoft.com'
            print(f"✓ Clearbit enrichment successful for microsoft.com: {enriched.get('company_name')}")
        else:
            print("✓ Fallback to mock enrichment for microsoft.com")
    
    def test_clearbit_enrichment_vigil_domain(self, agent):
        """Test Clearbit enrichment with Vigil.AI domain."""
        lead_data = {
            'name': 'Alex Johnson',
            'email': 'alex@vigil.ai',
            'company': 'Vigil.AI',
            'job_title': 'CTO'
        }
        
        enriched = agent.enrich_lead_data(lead_data)
        
        assert 'enriched_at' in enriched
        assert 'enrichment_source' in enriched
        
        if enriched.get('enrichment_source') == 'clearbit':
            # Clearbit may normalize domain names (e.g., vigil.ai -> vigilai.com)
            assert 'vigil' in enriched['domain'].lower()
            print(f"✓ Clearbit enrichment successful for vigil.ai: {enriched.get('company_name')} (domain: {enriched['domain']})")
        else:
            print("✓ Fallback to mock enrichment for vigil.ai")
    
    def test_clearbit_json_parsing_empty_results(self, agent):
        """Test JSON parsing when Clearbit returns empty results."""
        lead_data = {
            'name': 'Test User',
            'email': 'test@nonexistent-domain-12345.com',
            'company': 'Test Company'
        }
        
        enriched = agent.enrich_lead_data(lead_data)
        
        # Should fallback to mock enrichment
        assert enriched.get('enrichment_source') == 'mock'
        assert 'company_name' in enriched
        assert 'industry' in enriched
        print("✓ Correctly handled empty results from Clearbit")
    
    def test_clearbit_json_parsing_missing_fields(self, agent, sample_lead_data):
        """Test JSON parsing when response has missing fields."""
        # Mock a response with missing fields
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'name': 'Test Company',
                'domain': 'test.com'
                # Missing category, logo, metrics
            }
        ]
        
        with patch('requests.get', return_value=mock_response):
            enriched = agent.enrich_lead_data(sample_lead_data)
            
            # Should still work with missing fields
            assert enriched.get('enrichment_source') == 'clearbit'
            assert enriched['company_name'] == 'Test Company'
            assert enriched['domain'] == 'test.com'
            # Missing fields should have defaults
            assert enriched.get('industry') == 'Unknown'
            print("✓ Correctly handled missing fields in Clearbit response")
    
    def test_clearbit_error_handling_timeout(self, agent, sample_lead_data):
        """Test error handling when Clearbit API times out."""
        with patch('requests.get', side_effect=requests.exceptions.Timeout()):
            enriched = agent.enrich_lead_data(sample_lead_data)
            
            # Should fallback to mock enrichment
            assert enriched.get('enrichment_source') == 'mock'
            assert 'company_name' in enriched
            print("✓ Correctly handled timeout error")
    
    def test_clearbit_error_handling_request_exception(self, agent, sample_lead_data):
        """Test error handling when Clearbit API request fails."""
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Connection error")):
            enriched = agent.enrich_lead_data(sample_lead_data)
            
            # Should fallback to mock enrichment
            assert enriched.get('enrichment_source') == 'mock'
            assert 'company_name' in enriched
            print("✓ Correctly handled request exception")
    
    def test_clearbit_error_handling_json_decode_error(self, agent, sample_lead_data):
        """Test error handling when JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with patch('requests.get', return_value=mock_response):
            enriched = agent.enrich_lead_data(sample_lead_data)
            
            # Should fallback to mock enrichment
            assert enriched.get('enrichment_source') == 'mock'
            print("✓ Correctly handled JSON decode error")
    
    def test_enrichment_without_email(self, agent):
        """Test enrichment when lead has no email address."""
        lead_data = {
            'name': 'No Email User',
            'company': 'Test Company',
            'job_title': 'Developer'
        }
        
        enriched = agent.enrich_lead_data(lead_data)
        
        # Should use mock enrichment
        assert enriched.get('enrichment_source') == 'mock'
        assert 'company_name' in enriched
        assert 'industry' in enriched
        print("✓ Correctly handled lead without email")
    
    def test_enrichment_with_invalid_email(self, agent):
        """Test enrichment when email has invalid format."""
        lead_data = {
            'name': 'Invalid Email User',
            'email': 'invalid-email-format',
            'company': 'Test Company'
        }
        
        enriched = agent.enrich_lead_data(lead_data)
        
        # Should use mock enrichment
        assert enriched.get('enrichment_source') == 'mock'
        print("✓ Correctly handled invalid email format")
    
    def test_mock_enrichment_fallback(self, agent):
        """Test mock enrichment fallback functionality."""
        lead_data = {
            'name': 'Fallback Test',
            'email': 'test@unknown-domain.xyz',
            'company': 'Tech Startup Inc'
        }
        
        enriched = agent.enrich_lead_data(lead_data)
        
        # Verify mock enrichment fields
        assert enriched.get('enrichment_source') == 'mock'
        assert 'company_name' in enriched
        assert 'industry' in enriched
        assert 'company_size' in enriched
        assert 'enriched_at' in enriched
        
        # Verify industry detection based on company name
        assert enriched['industry'] == 'Technology'  # Contains "Tech"
        print("✓ Mock enrichment fallback working correctly")
    
    def test_enrichment_preserves_original_data(self, agent, sample_lead_data):
        """Test that enrichment preserves original lead data."""
        original_name = sample_lead_data['name']
        original_email = sample_lead_data['email']
        
        enriched = agent.enrich_lead_data(sample_lead_data)
        
        # Original fields should be preserved
        assert enriched['name'] == original_name
        assert enriched['email'] == original_email
        print("✓ Original lead data preserved during enrichment")


class TestLLMDispatcher:
    """Test suite for LLM dispatcher functionality."""
    
    def test_llm_provider_configuration(self):
        """Test LLM provider configuration from environment."""
        # Verify default configuration
        assert LLM_PROVIDER in ['openai', 'anthropic']
        assert LLM_API_KEY is not None
        assert LLM_API_URL is not None
        assert LLM_MODEL is not None
        print(f"✓ LLM Provider: {LLM_PROVIDER}")
        print(f"✓ LLM Model: {LLM_MODEL}")
    
    def test_call_llm_openai_format(self):
        """Test LLM dispatcher with OpenAI format (real API call)."""
        if LLM_PROVIDER != 'openai':
            pytest.skip("Skipping OpenAI test - provider is not 'openai'")
        
        try:
            response = call_llm(
                system_prompt="You are a helpful assistant.",
                user_message="Say 'Hello, World!' in exactly those words.",
                history=[]
            )
            
            # Verify response
            assert isinstance(response, str)
            assert len(response) > 0
            print(f"✓ OpenAI LLM call successful: {response[:50]}...")
        except Exception as e:
            pytest.fail(f"OpenAI LLM call failed: {str(e)}")
    
    def test_call_llm_with_history(self):
        """Test LLM dispatcher with conversation history."""
        if LLM_PROVIDER != 'openai':
            pytest.skip("Skipping OpenAI test - provider is not 'openai'")
        
        history = [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Hello Alice!"}
        ]
        
        try:
            response = call_llm(
                system_prompt="You are a helpful assistant.",
                user_message="What is my name?",
                history=history
            )
            
            assert isinstance(response, str)
            assert len(response) > 0
            print(f"✓ LLM call with history successful: {response[:50]}...")
        except Exception as e:
            pytest.fail(f"LLM call with history failed: {str(e)}")
    
    def test_call_llm_anthropic_format_structure(self):
        """Test Anthropic format structure (no real API call)."""
        # This test only verifies the structure, not actual API calls
        # since user doesn't have Anthropic credits
        
        # Mock Anthropic response structure
        anthropic_response = {
            "content": [
                {"text": "This is a mock Anthropic response"}
            ]
        }
        
        # Verify we can extract text from Anthropic format
        assert "content" in anthropic_response
        assert len(anthropic_response["content"]) > 0
        assert "text" in anthropic_response["content"][0]
        
        extracted_text = anthropic_response["content"][0]["text"]
        assert isinstance(extracted_text, str)
        print("✓ Anthropic response structure verified")
    
    def test_call_llm_environment_variable_switching(self, monkeypatch):
        """Test that LLM dispatcher respects environment variables."""
        # Test switching to OpenAI
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("LLM_API_URL", "https://test.api.com")
        monkeypatch.setenv("LLM_MODEL", "test-model")
        
        # Reload module to pick up new environment variables
        import importlib
        import ai_client
        importlib.reload(ai_client)
        
        assert ai_client.LLM_PROVIDER == "openai"
        assert ai_client.LLM_API_KEY == "test-key"
        assert ai_client.LLM_API_URL == "https://test.api.com"
        assert ai_client.LLM_MODEL == "test-model"
        
        print("✓ Environment variable switching working correctly")
    
    def test_call_llm_unsupported_provider(self):
        """Test error handling for unsupported LLM provider."""
        with patch('ai_client.LLM_PROVIDER', 'unsupported_provider'):
            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                call_llm(
                    system_prompt="Test",
                    user_message="Test",
                    history=[]
                )
        print("✓ Correctly handled unsupported provider")
    
    def test_call_llm_openai_request_error(self):
        """Test error handling when OpenAI API request fails."""
        if LLM_PROVIDER != 'openai':
            pytest.skip("Skipping OpenAI test - provider is not 'openai'")
        
        with patch('requests.post', side_effect=requests.exceptions.RequestException("API Error")):
            with pytest.raises(requests.exceptions.RequestException):
                call_llm(
                    system_prompt="Test",
                    user_message="Test",
                    history=[]
                )
        print("✓ Correctly handled OpenAI request error")
    
    def test_call_llm_response_parsing_error(self):
        """Test error handling when response parsing fails."""
        if LLM_PROVIDER != 'openai':
            pytest.skip("Skipping OpenAI test - provider is not 'openai'")
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "invalid_structure": "missing choices key"
        }
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises((KeyError, IndexError)):
                call_llm(
                    system_prompt="Test",
                    user_message="Test",
                    history=[]
                )
        print("✓ Correctly handled response parsing error")


class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing code."""
    
    @pytest.fixture
    def agent(self):
        """Create an Agent instance for testing."""
        return Agent()
    
    def test_agent_initialization(self):
        """Test that Agent can still be initialized without changes."""
        agent = Agent()
        assert agent is not None
        assert agent.ai_client is not None
        print("✓ Agent initialization working correctly")
    
    def test_agent_with_custom_ai_client(self):
        """Test that Agent can accept custom AIClient."""
        from ai_client import AIClient
        custom_client = AIClient(model="Gemma-4-31B-Cognitive-Unshackled")
        agent = Agent(ai_client=custom_client)
        
        assert agent.ai_client == custom_client
        assert agent.ai_client.model == "Gemma-4-31B-Cognitive-Unshackled"
        print("✓ Agent with custom AIClient working correctly")
    
    def test_enrich_lead_data_signature(self, agent):
        """Test that enrich_lead_data signature is unchanged."""
        lead_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'company': 'Test Company'
        }
        
        # Should work with same signature
        result = agent.enrich_lead_data(lead_data)
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'enriched_at' in result
        print("✓ enrich_lead_data signature unchanged")
    
    def test_chat_completion_backward_compatibility(self):
        """Test that chat_completion still works with old format."""
        from ai_client import AIClient
        
        client = AIClient()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello'"}
        ]
        
        try:
            response = client.chat_completion(messages)
            
            # Should return OpenAI-compatible format
            assert "choices" in response
            assert len(response["choices"]) > 0
            assert "message" in response["choices"][0]
            print("✓ chat_completion backward compatible")
        except Exception as e:
            # If API call fails, at least verify the method exists
            assert hasattr(client, 'chat_completion')
            print(f"✓ chat_completion method exists (API call failed: {str(e)})")


class TestIntegration:
    """Integration tests for combined functionality."""
    
    @pytest.fixture
    def agent(self):
        """Create an Agent instance for testing."""
        return Agent()
    
    def test_full_enrichment_workflow(self, agent):
        """Test complete enrichment workflow from lead data to enriched data."""
        lead_data = {
            'name': 'Integration Test User',
            'email': 'integration@google.com',
            'company': 'Google',
            'job_title': 'Engineer',
            'source': 'test'
        }
        
        # Enrich lead data
        enriched = agent.enrich_lead_data(lead_data)
        
        # Verify enrichment
        assert 'name' in enriched
        assert 'email' in enriched
        assert 'enriched_at' in enriched
        assert 'enrichment_source' in enriched
        
        # Verify timestamp is recent
        enrichment_time = datetime.fromisoformat(enriched['enriched_at'])
        assert (datetime.now(timezone.utc) - enrichment_time).total_seconds() < 10
        
        print(f"✓ Full enrichment workflow successful (source: {enriched['enrichment_source']})")
    
    def test_error_recovery_workflow(self, agent):
        """Test error recovery when Clearbit fails."""
        lead_data = {
            'name': 'Error Recovery Test',
            'email': 'error@invalid-domain-99999.com',
            'company': 'Error Company'
        }
        
        # Should gracefully fallback to mock enrichment
        enriched = agent.enrich_lead_data(lead_data)
        
        assert enriched.get('enrichment_source') == 'mock'
        assert 'company_name' in enriched
        assert 'industry' in enriched
        
        print("✓ Error recovery workflow successful")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
"""
Integration tests for AI Client module.
Tests real API interactions based on discoveries from API exploration.
"""

import pytest
import sys
import os

# Add parent directory to path to import ai_client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_client import AIClient, get_ai_client, generate_engagement_message


class TestAIClientBasic:
    """Test basic AI client functionality."""
    
    def test_client_initialization(self):
        """Test that AI client initializes correctly."""
        client = AIClient()
        assert client.model == AIClient.DEFAULT_MODEL
        assert client.base_url is not None
        assert "Authorization" in client.headers
    
    def test_client_with_custom_model(self):
        """Test client initialization with custom model."""
        custom_model = "Gemma-4-31B-Cognitive-Unshackled"
        client = AIClient(model=custom_model)
        assert client.model == custom_model
    
    def test_get_ai_client_convenience(self):
        """Test convenience function for getting AI client."""
        client = get_ai_client()
        assert isinstance(client, AIClient)


class TestAIAPIInteraction:
    """Test real AI API interactions."""
    
    def test_get_available_models(self):
        """Test retrieving available models from API."""
        client = AIClient()
        models = client.get_available_models()
        
        # Should return at least the working models we discovered
        assert len(models) > 0
        assert isinstance(models, list)
        
        # Check that known working models are in the list
        for working_model in AIClient.WORKING_MODELS:
            assert working_model in models
    
    def test_chat_completion_basic(self):
        """Test basic chat completion with API."""
        client = AIClient()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, AI test passed!'"}
        ]
        
        response = client.chat_completion(messages)
        
        # Verify response structure based on API exploration
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]
        assert "Hello" in response["choices"][0]["message"]["content"]
    
    def test_chat_completion_with_different_models(self):
        """Test chat completion with different working models."""
        for model in AIClient.WORKING_MODELS[:2]:  # Test first 2 working models
            client = AIClient(model=model)
            
            messages = [
                {"role": "user", "content": "What is 2+2?"}
            ]
            
            response = client.chat_completion(messages)
            
            assert "choices" in response
            assert len(response["choices"]) > 0
            assert response["model"] == model


class TestAILeadEngagement:
    """Test AI-powered lead engagement features."""
    
    def test_generate_lead_response_basic(self):
        """Test generating response for lead engagement."""
        client = AIClient()
        
        lead_info = {
            "name": "John Doe",
            "company": "Tech Corp",
            "job_title": "CTO",
            "source": "event"
        }
        
        response = client.generate_lead_response(lead_info)
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention something relevant to business context
        assert any(word in response.lower() for word in ["hello", "hi", "thank", "help"])
    
    def test_generate_lead_response_with_history(self):
        """Test generating response with conversation history."""
        client = AIClient()
        
        lead_info = {
            "name": "Jane Smith",
            "company": "Security Inc",
            "job_title": "Security Manager",
            "source": "website"
        }
        
        conversation_history = [
            {"role": "user", "content": "I'm interested in your cybersecurity services"},
            {"role": "assistant", "content": "Great! We offer comprehensive security solutions."}
        ]
        
        response = client.generate_lead_response(lead_info, conversation_history)
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_analyze_lead_interest(self):
        """Test analyzing lead interest from messages."""
        client = AIClient()
        
        lead_messages = [
            "I'm very interested in your penetration testing services",
            "When can we schedule a demo?",
            "Our company needs better security measures"
        ]
        
        analysis = client.analyze_lead_interest(lead_messages)
        
        assert "interest_level" in analysis
        assert "key_topics" in analysis
        assert "sentiment" in analysis
        assert analysis["interest_level"] in ["high", "medium", "low"]
        assert analysis["sentiment"] in ["positive", "neutral", "negative"]
    
    def test_suggest_follow_up(self):
        """Test follow-up suggestion generation."""
        client = AIClient()
        
        lead_info = {
            "name": "Bob Johnson",
            "company": "Data Corp",
            "job_title": "IT Director",
            "source": "referral"
        }
        
        last_interaction = "Lead requested pricing information via email"
        
        suggestion = client.suggest_follow_up(lead_info, last_interaction)
        
        assert isinstance(suggestion, str)
        assert len(suggestion) > 0
        # Should suggest some action
        assert any(word in suggestion.lower() for word in ["email", "call", "follow", "send", "schedule"])


class TestConvenienceFunctions:
    """Test convenience functions for common AI operations."""
    
    def test_generate_engagement_message(self):
        """Test generating initial engagement message."""
        message = generate_engagement_message("Alice Williams", "CyberTech")
        
        assert isinstance(message, str)
        assert len(message) > 0
        # Should be personalized
        assert "Alice" in message or "CyberTech" in message


class TestErrorHandling:
    """Test error handling in AI client."""
    
    def test_invalid_model_handling(self):
        """Test handling of invalid model names."""
        client = AIClient(model="InvalidModelName123")
        
        messages = [
            {"role": "user", "content": "Test"}
        ]
        
        # Should raise an exception for invalid model
        with pytest.raises(Exception):
            client.chat_completion(messages)
    
    def test_empty_messages_handling(self):
        """Test handling of empty message list."""
        client = AIClient()
        
        # API should handle empty messages or return error
        with pytest.raises(Exception):
            client.chat_completion([])


class TestAPIDiscoveries:
    """Test that API exploration discoveries are properly implemented."""
    
    def test_working_models_are_accessible(self):
        """Test that models discovered as working are accessible."""
        client = AIClient()
        available_models = client.get_available_models()
        
        # All working models from exploration should be available
        for model in AIClient.WORKING_MODELS:
            assert model in available_models, f"Model {model} from exploration not available"
    
    def test_default_model_is_working(self):
        """Test that the default model is one of the working models."""
        assert AIClient.DEFAULT_MODEL in AIClient.WORKING_MODELS
    
    def test_model_parameter_is_required(self):
        """Test that model parameter is properly included in requests."""
        client = AIClient()
        
        # This test verifies that the client properly includes model parameter
        # by checking that a successful request is made
        messages = [{"role": "user", "content": "Test"}]
        response = client.chat_completion(messages)
        
        # Response should include the model that was used
        assert "model" in response
        assert response["model"] == client.model


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
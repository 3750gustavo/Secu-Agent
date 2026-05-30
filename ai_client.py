"""
AI Client Module for Secu-Agent
Implements ArliAI API integration based on API exploration discoveries.
Extended with Agent class for lead capture and automated lead management.
"""

import requests
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

# Load configuration
with open('airli_config.json', 'r') as f:
    config = json.load(f)

API_KEY = config['API_KEY']
BASE_URL = config['BASE_URL']

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIClient:
    """
    Client for interacting with ArliAI API.
    Based on API exploration: 21 available models, all require model parameter.
    """
    
    # Working models discovered from API exploration
    WORKING_MODELS = [
        "Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled",
        "Gemma-4-31B-Cognitive-Unshackled", 
        "Gemma-4-31B-DarkIdol"
    ]
    
    # Default model for general use
    DEFAULT_MODEL = "Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled"
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize AI client.
        
        Args:
            model: Model name to use. If None, uses DEFAULT_MODEL
        """
        self.model = model or self.DEFAULT_MODEL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        self.base_url = BASE_URL
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send chat completion request to AI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API request failed: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available models from API.
        
        Returns:
            List of model IDs
        """
        url = f"{self.base_url}/v1/models"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            
            if "data" in result:
                return [model.get("id", "") for model in result["data"]]
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return self.WORKING_MODELS  # Fallback to known working models
    
    def generate_lead_response(self, lead_info: Dict[str, str], conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate AI response for lead engagement.
        
        Args:
            lead_info: Dictionary containing lead information (name, company, etc.)
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text
        """
        system_prompt = f"""You are a helpful AI assistant for Vigil.AI, a cybersecurity company. 
Your role is to engage with potential leads professionally and help them understand our cybersecurity services.

Lead Information:
- Name: {lead_info.get('name', 'Unknown')}
- Company: {lead_info.get('company', 'Unknown')}
- Job Title: {lead_info.get('job_title', 'Unknown')}
- Source: {lead_info.get('source', 'Unknown')}

Be professional, helpful, and focus on cybersecurity topics. Keep responses concise and engaging."""

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        try:
            response = self.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Failed to generate lead response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again later."
    
    def analyze_lead_interest(self, lead_messages: List[str]) -> Dict[str, Any]:
        """
        Analyze lead's interest level based on their messages.
        
        Args:
            lead_messages: List of messages from the lead
            
        Returns:
            Dictionary with analysis results (interest_level, key_topics, sentiment)
        """
        system_prompt = """You are a sales analysis AI. Analyze the lead's messages and determine:
1. Interest level (high, medium, low)
2. Key topics mentioned
3. Overall sentiment (positive, neutral, negative)

Respond in JSON format with keys: interest_level, key_topics (array), sentiment"""

        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in lead_messages:
            messages.append({"role": "user", "content": msg})
        
        try:
            response = self.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback if response is not valid JSON
                return {
                    "interest_level": "medium",
                    "key_topics": ["general inquiry"],
                    "sentiment": "neutral"
                }
        except Exception as e:
            logger.error(f"Failed to analyze lead interest: {str(e)}")
            return {
                "interest_level": "low",
                "key_topics": [],
                "sentiment": "neutral"
            }
    
    def suggest_follow_up(self, lead_info: Dict[str, str], last_interaction: str) -> str:
        """
        Suggest follow-up action based on lead information and last interaction.
        
        Args:
            lead_info: Lead information dictionary
            last_interaction: Description of last interaction
            
        Returns:
            Suggested follow-up action
        """
        system_prompt = f"""You are a sales assistant. Suggest a follow-up action for this lead:

Lead: {lead_info.get('name', 'Unknown')} from {lead_info.get('company', 'Unknown')}
Last Interaction: {last_interaction}

Suggest a specific, actionable follow-up (email, call, meeting request, etc.) and provide a brief reason."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What follow-up action would you recommend?"}
        ]
        
        try:
            response = self.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Failed to suggest follow-up: {str(e)}")
            return "Send a follow-up email to check if they have any questions about our services."


# Convenience functions for common operations
def get_ai_client(model: Optional[str] = None) -> AIClient:
    """Get an AI client instance."""
    return AIClient(model)


def generate_engagement_message(lead_name: str, company: str) -> str:
    """
    Generate an initial engagement message for a lead.
    
    Args:
        lead_name: Name of the lead
        company: Company name
        
    Returns:
        Generated engagement message
    """
    client = get_ai_client()
    
    system_prompt = f"""Generate a personalized, professional engagement message for {lead_name} at {company}.
The message should:
1. Be warm and professional
2. Mention Vigil.AI's cybersecurity expertise
3. Encourage further conversation
4. Be concise (2-3 sentences)"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate the engagement message."}
    ]
    
    try:
        response = client.chat_completion(messages)
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to generate engagement message: {str(e)}")
        return f"Hi {lead_name}, I noticed your interest in cybersecurity solutions. I'd love to learn more about {company}'s security needs and how Vigil.AI can help."
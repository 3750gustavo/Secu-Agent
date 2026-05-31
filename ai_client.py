"""
AI Client Module for Secu-Agent
Implements ArliAI API integration based on API exploration discoveries.
Extended with Agent class for lead capture and automated lead management.
Enhanced with Clearbit enrichment and flexible LLM dispatcher.
"""

import requests
import json
import re
import os
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timezone

# Load configuration
with open('airli_config.json', 'r') as f:
    config = json.load(f)

API_KEY = config['API_KEY']
BASE_URL = config['BASE_URL']

# LLM Provider Configuration
# Priority: Environment variables > Config file > Defaults
LLM_PROVIDER = os.getenv("LLM_PROVIDER", config.get('LLM_PROVIDER', 'openai'))
LLM_API_KEY = os.getenv("LLM_API_KEY", API_KEY)
LLM_API_URL = os.getenv("LLM_API_URL", BASE_URL)
LLM_MODEL = os.getenv("LLM_MODEL", config.get('LLM_MODEL', 'Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    LLM dispatcher that abstracts provider differences.
    Supports OpenAI and Anthropic formats.
    
    Args:
        system_prompt: System prompt for the LLM
        user_message: User message to send
        history: Conversation history (list of message dicts with 'role' and 'content')
        
    Returns:
        LLM response text
    """
    if history is None:
        history = []
    
    try:
        if LLM_PROVIDER == "openai":
            # OpenAI-compatible format (ArliAI, OpenAI, etc.)
            headers = {
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": LLM_MODEL,
                "messages": [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}],
                "max_tokens": 1024
            }
            response = requests.post(f"{LLM_API_URL}/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        
        elif LLM_PROVIDER == "anthropic":
            # Anthropic format
            headers = {
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "claude-3-haiku-20240307",
                "system": system_prompt,
                "messages": history + [{"role": "user", "content": user_message}],
                "max_tokens": 1024
            }
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['content'][0]['text']
        
        else:
            logger.error(f"Unsupported LLM provider: {LLM_PROVIDER}")
            raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse LLM response: {str(e)}")
        raise


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
        # Extract system prompt and user message from messages
        system_prompt = ""
        user_message = ""
        history = []
        
        for msg in messages:
            if msg.get('role') == 'system':
                system_prompt = msg.get('content', '')
            elif msg.get('role') == 'user':
                if not user_message:  # First user message
                    user_message = msg.get('content', '')
                else:
                    history.append(msg)
            else:
                history.append(msg)
        
        # Use LLM dispatcher if available
        try:
            content = call_llm(system_prompt, user_message, history)
            # Return in OpenAI-compatible format
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": content
                    }
                }]
            }
        except Exception as e:
            logger.error(f"LLM dispatcher failed, falling back to direct API: {str(e)}")
            # Fallback to direct API call
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


class Agent:
    """
    Agent class for automated lead management and engagement.
    Uses AIClient for AI-powered decision-making and communication.
    """
    
    # Tool call patterns for parsing AI responses
    TOOL_PATTERNS = {
        'SEND_EMAIL': r'SEND_EMAIL\{recipient:\s*([^,]+),\s*subject:\s*([^,]+),\s*body:\s*([^}]+)\}',
        'SEND_SMS': r'SEND_SMS\{phone:\s*([^,]+),\s*message:\s*([^}]+)\}',
        'SCHEDULE_REMINDER': r'SCHEDULE_REMINDER\{when:\s*([^,]+),\s*message:\s*([^}]+)\}',
        'UPDATE_STATUS': r'UPDATE_STATUS\{new_status:\s*([^}]+)\}',
        'REQUEST_INFO': r'REQUEST_INFO\{field:\s*([^,]+),\s*reason:\s*([^}]+)\}'
    }
    
    # Lead lifecycle state machine
    STATUS_TRANSITIONS = {
        'new': ['contacted', 'unconfirmed'],
        'unconfirmed': ['contacted', 'lost'],
        'contacted': ['engaged', 'lost'],
        'engaged': ['meeting_scheduled', 'contacted'],
        'meeting_scheduled': ['attended', 'contacted'],
        'attended': ['converted', 'contacted'],
        'lost': ['new']  # Can restart the cycle
    }
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize Agent with AI client.
        
        Args:
            ai_client: AIClient instance. If None, creates default instance.
        """
        self.ai_client = ai_client or get_ai_client()
        self.logger = logging.getLogger(__name__)
    
    def parse_tool_calls(self, ai_response: str) -> List[Dict[str, Any]]:
        """
        Parse AI response to extract tool calls using regex patterns.
        
        Args:
            ai_response: AI-generated response text
            
        Returns:
            List of detected tool calls with their parameters
        """
        tool_calls = []
        
        for tool_name, pattern in self.TOOL_PATTERNS.items():
            matches = re.finditer(pattern, ai_response, re.IGNORECASE)
            for match in matches:
                tool_call = {
                    'tool': tool_name,
                    'parameters': match.groups(),
                    'raw_match': match.group(0)
                }
                tool_calls.append(tool_call)
                self.logger.info(f"Detected tool call: {tool_name} with parameters: {match.groups()}")
        
        return tool_calls
    
    def generate_welcome_message(self, lead: Dict[str, Any]) -> str:
        """
        Generate AI-powered personalized welcome message for new lead.
        
        Args:
            lead: Dictionary containing lead information
            
        Returns:
            Personalized welcome message
        """
        system_prompt = f"""You are a professional AI assistant for Vigil.AI, a cybersecurity company.
Generate a warm, personalized welcome message for a new lead.

Lead Information:
- Name: {lead.get('name', 'Unknown')}
- Company: {lead.get('company', 'Unknown')}
- Job Title: {lead.get('job_title', 'Unknown')}
- Source: {lead.get('source', 'Unknown')}

The message should:
1. Be warm and professional
2. Acknowledge their interest in cybersecurity
3. Briefly mention Vigil.AI's expertise
4. Encourage engagement
5. Be concise (3-4 sentences)
6. Include a call to action

Do NOT include any tool calls in this message."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate a personalized welcome message."}
        ]
        
        try:
            response = self.ai_client.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Failed to generate welcome message: {str(e)}")
            return f"Welcome {lead.get('name', 'there')}! Thank you for your interest in Vigil.AI's cybersecurity solutions. We're excited to help protect {lead.get('company', 'your organization')} from emerging threats. Let's start a conversation about your security needs."
    
    def determine_next_action(self, lead: Dict[str, Any], context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Use AI to determine the next action for a lead based on status and context.
        
        Args:
            lead: Lead information dictionary
            context: Conversation history context
            
        Returns:
            AI-generated recommendation for next action (may include tool calls)
        """
        system_prompt = f"""You are an intelligent sales agent for Vigil.AI cybersecurity company.
Analyze the lead's current situation and recommend the next action.

Lead Information:
- Name: {lead.get('name', 'Unknown')}
- Company: {lead.get('company', 'Unknown')}
- Job Title: {lead.get('job_title', 'Unknown')}
- Current Status: {lead.get('status', 'new')}
- Source: {lead.get('source', 'Unknown')}

Available Actions:
1. SEND_EMAIL - Send an email to the lead
2. SCHEDULE_REMINDER - Schedule a follow-up reminder
3. UPDATE_STATUS - Update the lead's status
4. REQUEST_INFO - Request additional information from the lead

Respond with a clear recommendation and include the appropriate tool call in the format:
TOOL_NAME{{parameter1: value1, parameter2: value2}}

Example: SEND_EMAIL{{recipient: john@company.com, subject: Following up, body: Hi John, I wanted to follow up...}}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": "What should be the next action for this lead?"})
        
        try:
            response = self.ai_client.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Failed to determine next action: {str(e)}")
            return "SEND_EMAIL{recipient: " + lead.get('email', '') + ", subject: Following up, body: Hi " + lead.get('name', 'there') + ", I wanted to check in and see if you have any questions about our cybersecurity services.}"
    
    def generate_contextual_message(self, lead: Dict[str, Any], context: List[Dict[str, str]],
                                   intent: str = "follow_up") -> str:
        """
        Generate context-aware message based on conversation history.
        
        Args:
            lead: Lead information dictionary
            context: Conversation history
            intent: Purpose of the message (follow_up, reminder, info_request, etc.)
            
        Returns:
            Context-aware personalized message
        """
        system_prompt = f"""You are a professional AI assistant for Vigil.AI cybersecurity company.
Generate a contextual message based on the conversation history.

Lead Information:
- Name: {lead.get('name', 'Unknown')}
- Company: {lead.get('company', 'Unknown')}
- Job Title: {lead.get('job_title', 'Unknown')}
- Current Status: {lead.get('status', 'new')}

Message Intent: {intent}

The message should:
1. Reference previous conversation context naturally
2. Be relevant to the lead's current status
3. Maintain professional tone
4. Include appropriate call to action
5. Be concise but informative

Do NOT include tool calls in this message."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": f"Generate a {intent} message based on the conversation history."})
        
        try:
            response = self.ai_client.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Failed to generate contextual message: {str(e)}")
            return f"Hi {lead.get('name', 'there')}, following up on our previous conversation. I'd love to continue discussing how Vigil.AI can help {lead.get('company', 'your organization')} with cybersecurity."
    
    def update_context(self, lead_id: int, message: str, response: str,
                      db_session) -> bool:
        """
        Update conversation context in database.
        
        Args:
            lead_id: ID of the lead
            message: Message sent to lead
            response: Response received from lead
            db_session: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from database import MessageOperations
            
            # Store outbound message
            MessageOperations.create_message(
                db=db_session,
                lead_id=lead_id,
                message_text=message,
                channel="email",
                direction="outbound"
            )
            
            # Store inbound response
            if response:
                MessageOperations.create_message(
                    db=db_session,
                    lead_id=lead_id,
                    message_text=response,
                    channel="email",
                    direction="inbound"
                )
            
            self.logger.info(f"Updated context for lead {lead_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update context for lead {lead_id}: {str(e)}")
            return False
    
    def get_conversation_context(self, lead_id: int, db_session,
                                limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieve conversation history for a lead.
        
        Args:
            lead_id: ID of the lead
            db_session: Database session
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries with role and content
        """
        try:
            from database import MessageOperations
            
            messages = MessageOperations.get_messages_by_lead(db_session, lead_id)
            
            # Convert to chat completion format
            context = []
            for msg in messages[-limit:]:  # Get most recent messages
                role = "user" if msg.direction == "inbound" else "assistant"
                context.append({
                    "role": role,
                    "content": msg.message_text
                })
            
            return context
        except Exception as e:
            self.logger.error(f"Failed to get conversation context for lead {lead_id}: {str(e)}")
            return []
    
    def execute_tool_call(self, tool_call: Dict[str, Any], lead: Dict[str, Any],
                         db_session) -> Dict[str, Any]:
        """
        Execute a parsed tool call.
        
        Args:
            tool_call: Tool call dictionary with tool name and parameters
            lead: Lead information
            db_session: Database session
            
        Returns:
            Execution result dictionary
        """
        tool_name = tool_call['tool']
        parameters = tool_call['parameters']
        
        try:
            if tool_name == 'SEND_EMAIL':
                # Use communication service to send email
                recipient, subject, body = parameters
                self.logger.info(f"SEND_EMAIL executed: To={recipient}, Subject={subject}")
                
                # Import and use communication service
                from communication import get_communication_service
                comm_service = get_communication_service()
                
                result = comm_service.send_email(
                    to=recipient.strip(),
                    subject=subject.strip(),
                    body=body.strip(),
                    lead_id=lead.get('id'),
                    db_session=db_session,
                    html=False
                )
                
                return {
                    "success": result.get("success", False),
                    "action": "email_sent",
                    "recipient": recipient,
                    "message_id": result.get("message_id"),
                    "status": result.get("status"),
                    "error": result.get("error")
                }
            
            elif tool_name == 'SEND_SMS':
                # Use communication service to send SMS
                phone, message = parameters
                self.logger.info(f"SEND_SMS executed: To={phone}")
                
                # Import and use communication service
                from communication import get_communication_service
                comm_service = get_communication_service()
                
                result = comm_service.send_sms(
                    phone=phone.strip(),
                    message=message.strip(),
                    lead_id=lead.get('id'),
                    db_session=db_session
                )
                
                return {
                    "success": result.get("success", False),
                    "action": "sms_sent",
                    "phone": phone,
                    "message_id": result.get("message_id"),
                    "status": result.get("status"),
                    "error": result.get("error")
                }
            
            elif tool_name == 'SCHEDULE_REMINDER':
                when, message = parameters
                self.logger.info(f"SCHEDULE_REMINDER executed: When={when}, Message={message}")
                return {"success": True, "action": "reminder_scheduled", "when": when}
            
            elif tool_name == 'UPDATE_STATUS':
                new_status = parameters[0].strip()
                from database import LeadOperations
                
                updated_lead = LeadOperations.update_lead_status(
                    db=db_session,
                    lead_id=lead.get('id'),
                    new_status=new_status
                )
                
                if updated_lead:
                    self.logger.info(f"UPDATE_STATUS executed: {lead.get('status')} -> {new_status}")
                    return {"success": True, "action": "status_updated", "new_status": new_status}
                else:
                    return {"success": False, "error": "Failed to update status"}
            
            elif tool_name == 'REQUEST_INFO':
                field, reason = parameters
                self.logger.info(f"REQUEST_INFO executed: Field={field}, Reason={reason}")
                
                # Generate and send info request message
                info_message = f"I'd like to learn more about {field} to better assist you. {reason}"
                from database import MessageOperations
                MessageOperations.create_message(
                    db=db_session,
                    lead_id=lead.get('id'),
                    message_text=info_message,
                    channel="email",
                    direction="outbound"
                )
                
                return {"success": True, "action": "info_requested", "field": field}
            
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            self.logger.error(f"Failed to execute tool call {tool_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_lead(self, lead_id: int, db_session) -> Dict[str, Any]:
        """
        Main processing logic for a lead - determines and executes next actions.
        
        Args:
            lead_id: ID of the lead to process
            db_session: Database session
            
        Returns:
            Processing result with actions taken
        """
        try:
            from database import LeadOperations
            
            # Get lead information
            lead = LeadOperations.get_lead(db_session, lead_id)
            if not lead:
                return {"success": False, "error": "Lead not found"}
            
            lead_dict = {
                'id': lead.id,
                'name': lead.name,
                'email': lead.email,
                'company': lead.company,
                'job_title': lead.job_title,
                'status': lead.status,
                'source': lead.source
            }
            
            # Get conversation context
            context = self.get_conversation_context(lead_id, db_session)
            
            # Determine next action based on lead status
            if lead.status == 'new':
                # New lead - send welcome message
                welcome_message = self.generate_welcome_message(lead_dict)
                self.update_context(lead_id, welcome_message, "", db_session)
                
                # Update status to contacted
                LeadOperations.update_lead_status(db_session, lead_id, "contacted")
                
                return {
                    "success": True,
                    "action": "welcome_sent",
                    "message": welcome_message,
                    "new_status": "contacted"
                }
            
            elif lead.status == 'contacted':
                # Use AI to determine next action
                ai_response = self.determine_next_action(lead_dict, context)
                
                # Parse and execute tool calls
                tool_calls = self.parse_tool_calls(ai_response)
                results = []
                
                for tool_call in tool_calls:
                    result = self.execute_tool_call(tool_call, lead_dict, db_session)
                    results.append(result)
                
                return {
                    "success": True,
                    "action": "ai_processed",
                    "ai_response": ai_response,
                    "tool_calls_executed": len(tool_calls),
                    "results": results
                }
            
            elif lead.status == 'engaged':
                # Generate contextual follow-up
                follow_up = self.generate_contextual_message(lead_dict, context, "follow_up")
                self.update_context(lead_id, follow_up, "", db_session)
                
                return {
                    "success": True,
                    "action": "follow_up_sent",
                    "message": follow_up
                }
            
            elif lead.status == 'meeting_scheduled':
                # Send meeting reminder
                reminder = self.generate_contextual_message(lead_dict, context, "meeting_reminder")
                self.update_context(lead_id, reminder, "", db_session)
                
                return {
                    "success": True,
                    "action": "reminder_sent",
                    "message": reminder
                }
            
            elif lead.status == 'attended':
                # Follow up after meeting
                follow_up = self.generate_contextual_message(lead_dict, context, "post_meeting")
                self.update_context(lead_id, follow_up, "", db_session)
                
                # Update status to engaged for further nurturing
                LeadOperations.update_lead_status(db_session, lead_id, "engaged")
                
                return {
                    "success": True,
                    "action": "post_meeting_followup",
                    "message": follow_up,
                    "new_status": "engaged"
                }
            
            else:
                return {
                    "success": True,
                    "action": "no_action",
                    "message": f"No action required for lead in status: {lead.status}"
                }
        
        except Exception as e:
            self.logger.error(f"Failed to process lead {lead_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def enrich_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-enrich lead data using Clearbit API with fallback to mock data.
        
        Args:
            lead_data: Original lead data
            
        Returns:
            Enriched lead data
        """
        enriched = lead_data.copy()
        
        # Try to get domain from email
        email = lead_data.get('email', '')
        domain = None
        if email and '@' in email:
            domain = email.split('@')[1]
        
        # Try Clearbit API if we have a domain
        if domain:
            try:
                response = requests.get(
                    f"https://company.clearbit.com/v1/companies/suggest?query={domain}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        company_info = data[0]
                        
                        # Extract available fields from Clearbit response
                        enriched['company_name'] = company_info.get('name', lead_data.get('company', 'Unknown'))
                        enriched['domain'] = company_info.get('domain', domain)
                        
                        # Extract industry from category structure
                        category = company_info.get('category', {})
                        if isinstance(category, dict):
                            enriched['industry'] = category.get('industry', 'Unknown')
                        else:
                            enriched['industry'] = 'Unknown'
                        
                        # Get logo URL
                        enriched['logo'] = company_info.get('logo', '')
                        
                        # Add company size if available
                        if 'metrics' in company_info and 'employees' in company_info['metrics']:
                            employees = company_info['metrics']['employees']
                            if employees < 50:
                                enriched['company_size'] = 'Small (1-50 employees)'
                            elif employees < 200:
                                enriched['company_size'] = 'Medium (51-200 employees)'
                            else:
                                enriched['company_size'] = 'Large (200+ employees)'
                        
                        logger.info(f"Successfully enriched lead data using Clearbit for domain: {domain}")
                        enriched['enrichment_source'] = 'clearbit'
                        enriched['enriched_at'] = datetime.now(timezone.utc).isoformat()
                        return enriched
                
            except requests.exceptions.Timeout:
                logger.warning(f"Clearbit API timeout for domain: {domain}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Clearbit API request failed for domain {domain}: {str(e)}")
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning(f"Failed to parse Clearbit response for domain {domain}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error during Clearbit enrichment: {str(e)}")
        
        # Fallback to mock enrichment if Clearbit fails or no domain available
        logger.info(f"Using mock enrichment fallback for lead")
        enriched = self._mock_enrichment(enriched)
        enriched['enrichment_source'] = 'mock'
        enriched['enriched_at'] = datetime.now(timezone.utc).isoformat()
        
        return enriched
    
    def _mock_enrichment(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock enrichment fallback when Clearbit API is unavailable.
        
        Args:
            lead_data: Original lead data
            
        Returns:
            Enriched lead data with mock information
        """
        enriched = lead_data.copy()
        
        # Mock enrichment based on company name
        company = lead_data.get('company', '')
        if company:
            # Mock company size based on name length (simple heuristic)
            if len(company) < 10:
                enriched['company_size'] = 'Small (1-50 employees)'
            elif len(company) < 20:
                enriched['company_size'] = 'Medium (51-200 employees)'
            else:
                enriched['company_size'] = 'Large (200+ employees)'
            
            # Mock industry based on keywords
            company_lower = company.lower()
            if any(keyword in company_lower for keyword in ['tech', 'software', 'digital', 'cloud']):
                enriched['industry'] = 'Technology'
            elif any(keyword in company_lower for keyword in ['bank', 'finance', 'financial']):
                enriched['industry'] = 'Finance'
            elif any(keyword in company_lower for keyword in ['health', 'medical', 'pharma']):
                enriched['industry'] = 'Healthcare'
            else:
                enriched['industry'] = 'General'
        
        # Ensure required fields exist
        enriched.setdefault('company_name', lead_data.get('company', 'Unknown'))
        enriched.setdefault('domain', '')
        enriched.setdefault('logo', '')
        
        return enriched
"""
AI Client Module for Secu-Agent
Implements ArliAI API integration based on API exploration discoveries.
Extended with Agent class for lead capture and automated lead management.
Enhanced with Clearbit enrichment and flexible LLM dispatcher.
"""

from __future__ import annotations

import requests
import json
import re
import os
import asyncio
import inspect
from typing import Dict, Any, List, Optional, Tuple, Callable
import logging
from datetime import datetime, timezone, timedelta
from pytz import timezone as tz

# Load configuration - try config file first, fall back to environment variables
config = {}
try:
    with open('airli_config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    # Config file not found, will use environment variables
    pass

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Priority: Environment variables > Config file > Defaults
API_KEY = os.getenv("AIRLI_API_KEY", config.get('API_KEY', ""))
BASE_URL = os.getenv("AIRLI_BASE_URL", config.get('BASE_URL', "https://api.arliai.dev/v1"))

# LLM Provider Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", config.get('LLM_PROVIDER', 'openai'))
LLM_API_KEY = os.getenv("LLM_API_KEY", API_KEY)
LLM_API_URL = os.getenv("LLM_API_URL", BASE_URL)
LLM_MODEL = os.getenv("LLM_MODEL", config.get('LLM_MODEL', 'Gemma-4-31B-Claude-4.6-Opus-Reasoning-Distilled'))

# Validate required configuration
if not API_KEY and not LLM_API_KEY:
    logger.warning("No API key configured. Set AIRLI_API_KEY or LLM_API_KEY environment variable, or create airli_config.json")

# Global semaphore for AI API rate limiting (1 concurrent request globally)
# Subscription allows 2 parallel requests, we limit to 1 to leave 1 free for owner
_ai_semaphore = asyncio.Semaphore(1)

# BRT timezone for logging
BRT_TZ = tz('America/Sao_Paulo')

# Scheduled task queue for non-critical AI calls
_scheduled_tasks: List[Dict[str, Any]] = []
_scheduled_tasks_lock = asyncio.Lock()
_scheduler_running = False

# Error tracking for cooldown system
_consecutive_errors = 0
_error_cooldown_until = None
_error_tracking_lock = asyncio.Lock()
COOLDOWN_DURATION = 3600  # 1 hour cooldown after 3 consecutive errors
MAX_CONSECUTIVE_ERRORS = 3

# Priority levels
PRIORITY_IMMEDIATE = "immediate"  # For dashboard, user-facing features
PRIORITY_SCHEDULED = "scheduled"  # For emails, background tasks

def get_brt_timestamp() -> str:
    """Get current timestamp in BRT timezone."""
    return datetime.now(BRT_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')

def get_caller_context() -> str:
    """Get the calling function context for logging."""
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller_frame = frame.f_back
        function_name = caller_frame.f_code.co_name
        filename = caller_frame.f_code.co_filename
        line_no = caller_frame.f_lineno
        return f"{os.path.basename(filename)}:{function_name}:{line_no}"
    return "unknown"

def is_off_peak_hours() -> bool:
    """Check if current time is within off-peak hours (2am-6am BRT)."""
    current_hour = datetime.now(BRT_TZ).hour
    return 2 <= current_hour < 6

async def start_scheduler():
    """Start the background scheduler for non-critical tasks."""
    global _scheduler_running
    if _scheduler_running:
        return
    
    _scheduler_running = True
    logger.info(f"[{get_brt_timestamp()}] AI Task Scheduler started")
    
    while _scheduler_running:
        try:
            if is_off_peak_hours() and _scheduled_tasks:
                async with _scheduled_tasks_lock:
                    if _scheduled_tasks:
                        task = _scheduled_tasks.pop(0)
                        logger.info(f"[{get_brt_timestamp()}] Processing scheduled task: {task['reason']}")
                        
                        # Execute the scheduled task
                        try:
                            result = await task['func'](*task['args'], **task['kwargs'])
                            logger.info(f"[{get_brt_timestamp()}] Scheduled task completed: {task['reason']}")
                        except Exception as e:
                            logger.error(f"[{get_brt_timestamp()}] Scheduled task failed: {task['reason']} | Error: {str(e)}")
            
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"[{get_brt_timestamp()}] Scheduler error: {str(e)}")
            await asyncio.sleep(60)

async def schedule_ai_call(func: Callable, *args, priority: str = PRIORITY_IMMEDIATE, reason: str = "unknown", **kwargs):
    """
    Schedule an AI call with priority.
    
    Args:
        func: The async function to call
        *args: Positional arguments for the function
        priority: Priority level (PRIORITY_IMMEDIATE or PRIORITY_SCHEDULED)
        reason: Business reason for this call (for logging)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result if immediate, None if scheduled
    """
    caller_context = get_caller_context()
    
    if priority == PRIORITY_IMMEDIATE:
        # Execute immediately
        logger.info(f"[{get_brt_timestamp()}] Immediate AI call - Reason: {reason} | Caller: {caller_context}")
        return await func(*args, **kwargs)
    else:
        # Schedule for off-peak hours
        async with _scheduled_tasks_lock:
            _scheduled_tasks.append({
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'reason': reason,
                'queued_at': get_brt_timestamp(),
                'caller': caller_context
            })
            logger.info(f"[{get_brt_timestamp()}] AI call SCHEDULED for off-peak - Reason: {reason} | Caller: {caller_context} | Queue size: {len(_scheduled_tasks)}")
        
        # Start scheduler if not running
        if not _scheduler_running:
            asyncio.create_task(start_scheduler())
        
        return None



async def call_llm_with_limit(system_prompt: str, user_message: str, history: Optional[List[Dict[str, str]]] = None, reason: str = "unknown", priority: str = PRIORITY_IMMEDIATE) -> str:
    """
    LLM dispatcher with global rate limiting using semaphore.
    Only 1 AI API call can execute at a time globally (leaves 1 free for owner).
    Requests are queued and processed in order.
    Implements cooldown after 3 consecutive errors to prevent shadowban.
    
    Args:
        system_prompt: System prompt for the LLM
        user_message: User message to send
        history: Conversation history (list of message dicts with 'role' and 'content')
        reason: Business reason/context for this AI call (for logging)
        priority: Priority level (PRIORITY_IMMEDIATE or PRIORITY_SCHEDULED)
        
    Returns:
        LLM response text
        
    Raises:
        Exception: If in cooldown period due to consecutive errors
    """
    global _consecutive_errors, _error_cooldown_until
    
    caller_context = get_caller_context()
    timestamp = get_brt_timestamp()
    
    # Check if we're in cooldown period
    async with _error_tracking_lock:
        if _error_cooldown_until and datetime.now(BRT_TZ) < _error_cooldown_until:
            cooldown_remaining = (_error_cooldown_until - datetime.now(BRT_TZ)).total_seconds()
            logger.warning(f"[{timestamp}] AI Request REJECTED - In cooldown period | Reason: {reason} | Caller: {caller_context} | Cooldown remaining: {cooldown_remaining:.0f}s")
            raise Exception(f"AI service in cooldown due to consecutive errors. Try again in {cooldown_remaining:.0f} seconds.")
    
    # Schedule based on priority
    if priority == PRIORITY_SCHEDULED:
        async with _scheduled_tasks_lock:
            _scheduled_tasks.append({
                'func': _call_llm_internal,
                'args': (system_prompt, user_message, history),
                'kwargs': {},
                'reason': reason,
                'queued_at': timestamp,
                'caller': caller_context
            })
            logger.info(f"[{timestamp}] AI call SCHEDULED for off-peak - Reason: {reason} | Caller: {caller_context} | Queue size: {len(_scheduled_tasks)}")
        
        # Start scheduler if not running
        if not _scheduler_running:
            asyncio.create_task(start_scheduler())
        
        # Return empty string for scheduled calls (caller should handle None appropriately)
        return ""
    
    # Immediate execution
    logger.info(f"[{timestamp}] AI Request QUEUED - Reason: {reason} | Caller: {caller_context}")
    
    async with _ai_semaphore:
        execution_timestamp = get_brt_timestamp()
        logger.info(f"[{execution_timestamp}] AI Request STARTING - Reason: {reason} | Caller: {caller_context}")
        try:
            result = await _call_llm_internal(system_prompt, user_message, history)
            
            # Reset error counter on success
            async with _error_tracking_lock:
                if _consecutive_errors > 0:
                    logger.info(f"[{get_brt_timestamp()}] Resetting consecutive error counter (was {_consecutive_errors})")
                    _consecutive_errors = 0
                    _error_cooldown_until = None
            
            completion_timestamp = get_brt_timestamp()
            logger.info(f"[{completion_timestamp}] AI Request COMPLETED - Reason: {reason} | Caller: {caller_context}")
            return result
            
        except Exception as e:
            error_timestamp = get_brt_timestamp()
            
            # Track consecutive errors
            async with _error_tracking_lock:
                _consecutive_errors += 1
                logger.error(f"[{error_timestamp}] AI Request FAILED - Reason: {reason} | Caller: {caller_context} | Error: {str(e)} | Consecutive errors: {_consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}")
                
                # Activate cooldown if threshold reached
                if _consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    _error_cooldown_until = datetime.now(BRT_TZ) + timedelta(seconds=COOLDOWN_DURATION)
                    logger.critical(f"[{error_timestamp}] COOLDOWN ACTIVATED - {MAX_CONSECUTIVE_ERRORS} consecutive errors | Cooldown until: {_error_cooldown_until.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            raise


async def _call_llm_internal(system_prompt: str, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Internal LLM dispatcher implementation.
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
            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(f"{LLM_API_URL}/v1/chat/completions", headers=headers, json=payload))
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
            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload))
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


def call_llm(system_prompt: str, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Synchronous wrapper for call_llm_with_limit for backward compatibility.
    Note: This will block until the semaphore is acquired.
    
    Args:
        system_prompt: System prompt for the LLM
        user_message: User message to send
        history: Conversation history (list of message dicts with 'role' and 'content')
        
    Returns:
        LLM response text
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(call_llm_with_limit(system_prompt, user_message, history))
    finally:
        loop.close()


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
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send chat completion request to AI API with global rate limiting.
        
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
        
        # Use LLM dispatcher with rate limiting
        try:
            content = await call_llm_with_limit(system_prompt, user_message, history)
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
            # Fallback to direct API call with semaphore
            async with _ai_semaphore:
                url = f"{self.base_url}/v1/chat/completions"
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    **kwargs
                }
                
                try:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, lambda: requests.post(url, headers=self.headers, json=payload))
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
    
    def __init__(self, ai_client: Optional[AIClient] = None, engagement_rules: Optional[EngagementRules] = None):
        """
        Initialize Agent with AI client and engagement rules engine.
        
        Args:
            ai_client: AIClient instance. If None, creates default instance.
            engagement_rules: EngagementRules instance. If None, creates default instance.
        """
        self.ai_client = ai_client or get_ai_client()
        self.engagement_rules = engagement_rules or EngagementRules()
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
    
    def process_lead_with_rules(self, lead_id: int, db_session) -> Dict[str, Any]:
        """
        Process lead with automatic engagement rules evaluation.
        This is the enhanced version of process_lead that includes rule evaluation.
        
        Args:
            lead_id: ID of the lead to process
            db_session: Database session
            
        Returns:
            Processing result with actions taken and rule evaluations
        """
        try:
            from database import LeadOperations
            
            # First, process lead normally
            basic_result = self.process_lead(lead_id, db_session)
            
            if not basic_result.get("success"):
                return basic_result
            
            # Get lead information for rule evaluation
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
            
            # Calculate engagement score
            engagement_score = self.engagement_rules.get_engagement_score(lead_dict, db_session)
            
            # Build context for rule evaluation
            context = {
                'engagement_score': engagement_score,
                'event_date': self.engagement_rules.event_date,
                'sessions_attended': [],
                'last_email_opened': None,
                'last_contact_date': lead.updated_at
            }
            
            # Evaluate and execute engagement rules
            rule_results = self.engagement_rules.evaluate_rules_for_lead(
                lead_dict, context, self, db_session
            )
            
            # Combine results
            return {
                "success": True,
                "basic_processing": basic_result,
                "engagement_score": engagement_score,
                "rules_evaluated": len(self.engagement_rules.rules),
                "rules_matched": len(rule_results),
                "rule_results": rule_results,
                "total_actions": basic_result.get("tool_calls_executed", 0) + len(rule_results)
            }
        
        except Exception as e:
            self.logger.error(f"Failed to process lead {lead_id} with rules: {str(e)}")
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


class EngagementRule:
    """
    Represents a single engagement rule with conditions, actions, and metadata.
    """
    
    def __init__(self, name: str, priority: int, conditions: List[Callable],
                 actions: List[Callable], cooldown_hours: int = 24,
                 rule_type: str = "time_based"):
        """
        Initialize an engagement rule.
        
        Args:
            name: Unique rule name
            priority: Higher priority rules execute first (1-10)
            conditions: List of callable functions that return True/False
            actions: List of callable functions to execute when conditions met
            cooldown_hours: Minimum time between executions
            rule_type: Type of rule (time_based, behavior_based, hybrid)
        """
        self.name = name
        self.priority = priority
        self.conditions = conditions
        self.actions = actions
        self.cooldown_hours = cooldown_hours
        self.rule_type = rule_type
        self.last_executed = None
    
    def evaluate(self, lead: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluate if rule conditions are met.
        
        Args:
            lead: Lead information dictionary
            context: Additional context (event date, engagement data, etc.)
            
        Returns:
            True if all conditions are met, False otherwise
        """
        # Check cooldown period
        if self.last_executed:
            hours_since = (datetime.now(timezone.utc) - self.last_executed).total_seconds() / 3600
            if hours_since < self.cooldown_hours:
                return False
        
        # Evaluate all conditions
        for condition in self.conditions:
            try:
                if not condition(lead, context):
                    return False
            except Exception as e:
                logger.error(f"Error evaluating condition for rule {self.name}: {str(e)}")
                return False
        
        return True
    
    def execute(self, lead: Dict[str, Any], context: Dict[str, Any],
                agent: 'Agent', db_session) -> List[Dict[str, Any]]:
        """
        Execute rule actions.
        
        Args:
            lead: Lead information dictionary
            context: Additional context
            agent: Agent instance for executing actions
            db_session: Database session
            
        Returns:
            List of execution results
        """
        results = []
        
        for action in self.actions:
            try:
                result = action(lead, context, agent, db_session)
                results.append(result)
                logger.info(f"Executed action for rule {self.name}: {result}")
            except Exception as e:
                logger.error(f"Error executing action for rule {self.name}: {str(e)}")
                results.append({"success": False, "error": str(e)})
        
        self.last_executed = datetime.now(timezone.utc)
        return results


class EngagementRules:
    """
    Engagement rules engine for automated lead management.
    Manages pre-event and post-event engagement rules with time-based and behavior-based triggers.
    """
    
    def __init__(self, event_date: Optional[datetime] = None):
        """
        Initialize engagement rules engine.
        
        Args:
            event_date: Date of the event (defaults to 14 days from now)
        """
        self.event_date = event_date or (datetime.now(timezone.utc) + timedelta(days=14))
        self.rules: List[EngagementRule] = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize all rules
        self._initialize_pre_event_rules()
        self._initialize_post_event_rules()
        self._initialize_behavior_based_rules()
    
    def _initialize_pre_event_rules(self):
        """Initialize pre-event engagement rules."""
        
        # Rule 1: New lead → immediate welcome message (within 1 hour)
        def condition_new_lead(lead, context):
            return lead.get('status') == 'new'
        
        def action_send_welcome(lead, context, agent, db_session):
            welcome_message = agent.generate_welcome_message(lead)
            from database import LeadOperations
            LeadOperations.update_lead_status(db_session, lead['id'], "contacted")
            agent.update_context(lead['id'], welcome_message, "", db_session)
            return {"success": True, "action": "welcome_sent", "message": welcome_message}
        
        self.rules.append(EngagementRule(
            name="new_lead_welcome",
            priority=10,
            conditions=[condition_new_lead],
            actions=[action_send_welcome],
            cooldown_hours=1,
            rule_type="time_based"
        ))
        
        # Rule 2: Unconfirmed lead → reminder 7 days before event
        def condition_reminder_7_days(lead, context):
            days_until = (self.event_date - datetime.now(timezone.utc)).days
            return (lead.get('status') in ['contacted', 'unconfirmed'] and
                    days_until == 7 and
                    self._is_business_hours())
        
        def action_reminder_7_days(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "reminder_7_days_before_event"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "reminder_7_days", "message": message}
        
        self.rules.append(EngagementRule(
            name="reminder_7_days_before",
            priority=8,
            conditions=[condition_reminder_7_days],
            actions=[action_reminder_7_days],
            cooldown_hours=168,  # 7 days
            rule_type="time_based"
        ))
        
        # Rule 3: Unconfirmed lead → reminder 3 days before event
        def condition_reminder_3_days(lead, context):
            days_until = (self.event_date - datetime.now(timezone.utc)).days
            return (lead.get('status') in ['contacted', 'unconfirmed'] and
                    days_until == 3 and
                    self._is_business_hours())
        
        def action_reminder_3_days(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "reminder_3_days_before_event"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "reminder_3_days", "message": message}
        
        self.rules.append(EngagementRule(
            name="reminder_3_days_before",
            priority=8,
            conditions=[condition_reminder_3_days],
            actions=[action_reminder_3_days],
            cooldown_hours=72,  # 3 days
            rule_type="time_based"
        ))
        
        # Rule 4: Unconfirmed lead → final reminder 1 day before event
        def condition_reminder_1_day(lead, context):
            days_until = (self.event_date - datetime.now(timezone.utc)).days
            return (lead.get('status') in ['contacted', 'unconfirmed'] and
                    days_until == 1 and
                    self._is_business_hours())
        
        def action_reminder_1_day(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "final_reminder_before_event"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "reminder_1_day", "message": message}
        
        self.rules.append(EngagementRule(
            name="reminder_1_day_before",
            priority=9,
            conditions=[condition_reminder_1_day],
            actions=[action_reminder_1_day],
            cooldown_hours=24,
            rule_type="time_based"
        ))
        
        # Rule 5: Engaged lead → personalized content 5 days before event
        def condition_personalized_content(lead, context):
            days_until = (self.event_date - datetime.now(timezone.utc)).days
            return (lead.get('status') == 'engaged' and
                    days_until == 5 and
                    self._is_business_hours())
        
        def action_personalized_content(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "personalized_content_before_event"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "personalized_content", "message": message}
        
        self.rules.append(EngagementRule(
            name="personalized_content_5_days",
            priority=7,
            conditions=[condition_personalized_content],
            actions=[action_personalized_content],
            cooldown_hours=120,  # 5 days
            rule_type="time_based"
        ))
        
        # Rule 6: Confirmed lead → confirmation email + agenda
        def condition_confirmed_lead(lead, context):
            return lead.get('status') == 'meeting_scheduled'
        
        def action_confirmation_email(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "event_confirmation_with_agenda"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "confirmation_email", "message": message}
        
        self.rules.append(EngagementRule(
            name="confirmed_lead_confirmation",
            priority=9,
            conditions=[condition_confirmed_lead],
            actions=[action_confirmation_email],
            cooldown_hours=48,
            rule_type="time_based"
        ))
    
    def _initialize_post_event_rules(self):
        """Initialize post-event follow-up rules."""
        
        # Rule 7: Attended lead → thank you message within 24 hours
        def condition_attended_thank_you(lead, context):
            days_since = (datetime.now(timezone.utc) - self.event_date).days
            return (lead.get('status') == 'attended' and
                    days_since == 0 and
                    self._is_business_hours())
        
        def action_thank_you(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "thank_you_for_attending"
            )
            agent.update_context(lead['id'], message, "", db_session)
            from database import LeadOperations
            LeadOperations.update_lead_status(db_session, lead['id'], "engaged")
            return {"success": True, "action": "thank_you_sent", "message": message}
        
        self.rules.append(EngagementRule(
            name="attended_thank_you",
            priority=10,
            conditions=[condition_attended_thank_you],
            actions=[action_thank_you],
            cooldown_hours=24,
            rule_type="time_based"
        ))
        
        # Rule 8: Attended lead → meeting request 3 days after event
        def condition_meeting_request(lead, context):
            days_since = (datetime.now(timezone.utc) - self.event_date).days
            return (lead.get('status') == 'engaged' and
                    days_since == 3 and
                    self._is_business_hours())
        
        def action_meeting_request(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "follow_up_meeting_request"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "meeting_request", "message": message}
        
        self.rules.append(EngagementRule(
            name="attended_meeting_request",
            priority=8,
            conditions=[condition_meeting_request],
            actions=[action_meeting_request],
            cooldown_hours=72,
            rule_type="time_based"
        ))
        
        # Rule 9: No-show lead → reschedule invitation 2 days after event
        def condition_no_show_reschedule(lead, context):
            days_since = (datetime.now(timezone.utc) - self.event_date).days
            return (lead.get('status') == 'meeting_scheduled' and
                    days_since == 2 and
                    self._is_business_hours())
        
        def action_reschedule_invitation(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "reschedule_invitation"
            )
            agent.update_context(lead['id'], message, "", db_session)
            from database import LeadOperations
            LeadOperations.update_lead_status(db_session, lead['id'], "contacted")
            return {"success": True, "action": "reschedule_invitation", "message": message}
        
        self.rules.append(EngagementRule(
            name="no_show_reschedule",
            priority=9,
            conditions=[condition_no_show_reschedule],
            actions=[action_reschedule_invitation],
            cooldown_hours=48,
            rule_type="time_based"
        ))
        
        # Rule 10: Engaged lead → personalized content based on sessions attended
        def condition_session_based_content(lead, context):
            days_since = (datetime.now(timezone.utc) - self.event_date).days
            return (lead.get('status') == 'engaged' and
                    days_since >= 1 and
                    days_since <= 7 and
                    context.get('sessions_attended'))
        
        def action_session_content(lead, context, agent, db_session):
            sessions = context.get('sessions_attended', [])
            message = agent.generate_contextual_message(
                lead, [], f"session_followup_{sessions[0] if sessions else 'general'}"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "session_based_content", "message": message}
        
        self.rules.append(EngagementRule(
            name="session_based_content",
            priority=7,
            conditions=[condition_session_based_content],
            actions=[action_session_content],
            cooldown_hours=168,  # 7 days
            rule_type="time_based"
        ))
    
    def _initialize_behavior_based_rules(self):
        """Initialize behavior-based engagement rules."""
        
        # Rule: High engagement → escalate priority
        def condition_high_engagement(lead, context):
            engagement_score = context.get('engagement_score', 0)
            return engagement_score >= 8 and lead.get('status') in ['contacted', 'engaged']
        
        def action_escalate_priority(lead, context, agent, db_session):
            from database import LeadOperations
            # Add priority note or update status
            LeadOperations.update_lead_status(db_session, lead['id'], "engaged")
            return {"success": True, "action": "priority_escalated", "new_status": "engaged"}
        
        self.rules.append(EngagementRule(
            name="high_engagement_escalate",
            priority=6,
            conditions=[condition_high_engagement],
            actions=[action_escalate_priority],
            cooldown_hours=48,
            rule_type="behavior_based"
        ))
        
        # Rule: No response → de-priority
        def condition_no_response(lead, context):
            last_contact = context.get('last_contact_date')
            if not last_contact:
                return False
            
            # Handle both timezone-aware and naive datetimes
            now = datetime.now(timezone.utc)
            if last_contact.tzinfo is None:
                last_contact = last_contact.replace(tzinfo=timezone.utc)
            
            days_since_contact = (now - last_contact).days
            return days_since_contact >= 14 and lead.get('status') == 'contacted'
        
        def action_de_priority(lead, context, agent, db_session):
            from database import LeadOperations
            LeadOperations.update_lead_status(db_session, lead['id'], "lost")
            return {"success": True, "action": "de_prioritized", "new_status": "lost"}
        
        self.rules.append(EngagementRule(
            name="no_response_de_prioritize",
            priority=5,
            conditions=[condition_no_response],
            actions=[action_de_priority],
            cooldown_hours=168,  # 7 days
            rule_type="behavior_based"
        ))
        
        # Rule: Email opened → follow up within 24 hours
        def condition_email_opened(lead, context):
            return (context.get('last_email_opened') and
                    lead.get('status') in ['contacted', 'engaged'] and
                    self._is_business_hours())
        
        def action_email_opened_followup(lead, context, agent, db_session):
            message = agent.generate_contextual_message(
                lead, [], "email_opened_followup"
            )
            agent.update_context(lead['id'], message, "", db_session)
            return {"success": True, "action": "email_opened_followup", "message": message}
        
        self.rules.append(EngagementRule(
            name="email_opened_followup",
            priority=7,
            conditions=[condition_email_opened],
            actions=[action_email_opened_followup],
            cooldown_hours=24,
            rule_type="behavior_based"
        ))
    
    def _is_business_hours(self) -> bool:
        """
        Check if current time is within business hours (9 AM - 6 PM, Monday-Friday).
        
        Returns:
            True if within business hours, False otherwise
        """
        now = datetime.now(timezone.utc)
        
        # Check if weekday (Monday=0, Friday=4)
        if now.weekday() > 4:  # Saturday or Sunday
            return False
        
        # Check if between 9 AM and 6 PM UTC
        hour = now.hour
        return 9 <= hour < 18
    
    def evaluate_rules_for_lead(self, lead: Dict[str, Any],
                                context: Dict[str, Any],
                                agent: 'Agent',
                                db_session) -> List[Dict[str, Any]]:
        """
        Evaluate and execute applicable rules for a lead.
        
        Args:
            lead: Lead information dictionary
            context: Additional context (engagement data, behavior metrics, etc.)
            agent: Agent instance for executing actions
            db_session: Database session
            
        Returns:
            List of execution results from matched rules
        """
        # Sort rules by priority (higher priority first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        results = []
        
        for rule in sorted_rules:
            try:
                if rule.evaluate(lead, context):
                    self.logger.info(f"Rule {rule.name} matched for lead {lead.get('id')}")
                    execution_results = rule.execute(lead, context, agent, db_session)
                    results.append({
                        "rule_name": rule.name,
                        "priority": rule.priority,
                        "rule_type": rule.rule_type,
                        "results": execution_results
                    })
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.name}: {str(e)}")
                results.append({
                    "rule_name": rule.name,
                    "error": str(e)
                })
        
        return results
    
    def get_all_rules(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered rules.
        
        Returns:
            List of rule information dictionaries
        """
        return [
            {
                "name": rule.name,
                "priority": rule.priority,
                "rule_type": rule.rule_type,
                "cooldown_hours": rule.cooldown_hours,
                "last_executed": rule.last_executed.isoformat() if rule.last_executed else None
            }
            for rule in self.rules
        ]
    
    def get_upcoming_actions(self, leads: List[Dict[str, Any]],
                            context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get upcoming scheduled actions based on time-based rules.
        
        Args:
            leads: List of lead dictionaries
            context: Additional context
            
        Returns:
            List of upcoming action predictions
        """
        upcoming = []
        
        for lead in leads:
            for rule in self.rules:
                if rule.rule_type == "time_based":
                    # Predict when rule will trigger
                    prediction = self._predict_rule_trigger(rule, lead, context)
                    if prediction:
                        upcoming.append({
                            "lead_id": lead.get('id'),
                            "lead_name": lead.get('name'),
                            "rule_name": rule.name,
                            "predicted_trigger": prediction,
                            "priority": rule.priority
                        })
        
        # Sort by predicted trigger time
        upcoming.sort(key=lambda x: x['predicted_trigger'])
        return upcoming
    
    def _predict_rule_trigger(self, rule: EngagementRule,
                             lead: Dict[str, Any],
                             context: Dict[str, Any]) -> Optional[str]:
        """
        Predict when a time-based rule will trigger.
        
        Args:
            rule: Engagement rule to predict
            lead: Lead information
            context: Additional context
            
        Returns:
            ISO format datetime string or None if not predictable
        """
        try:
            # Check if conditions are already met (excluding time)
            now = datetime.now(timezone.utc)
            days_until = (self.event_date - now).days
            days_since = (now - self.event_date).days
            
            # Mock prediction logic based on rule names
            if "7_days_before" in rule.name and days_until > 7:
                trigger_date = self.event_date - timedelta(days=7)
                return trigger_date.isoformat()
            elif "3_days_before" in rule.name and days_until > 3:
                trigger_date = self.event_date - timedelta(days=3)
                return trigger_date.isoformat()
            elif "1_day_before" in rule.name and days_until > 1:
                trigger_date = self.event_date - timedelta(days=1)
                return trigger_date.isoformat()
            elif "thank_you" in rule.name and days_since < 0:
                trigger_date = self.event_date + timedelta(hours=12)
                return trigger_date.isoformat()
            elif "meeting_request" in rule.name and days_since < 3:
                trigger_date = self.event_date + timedelta(days=3)
                return trigger_date.isoformat()
            
            return None
        except Exception as e:
            self.logger.error(f"Error predicting rule trigger: {str(e)}")
            return None
    
    def set_event_date(self, event_date: datetime):
        """
        Update the event date for time-based rules.
        
        Args:
            event_date: New event date
        """
        self.event_date = event_date
        self.logger.info(f"Event date updated to {event_date.isoformat()}")
    
    def get_engagement_score(self, lead: Dict[str, Any],
                            db_session) -> int:
        """
        Calculate engagement score for a lead based on behavior.
        
        Args:
            lead: Lead information dictionary
            db_session: Database session
            
        Returns:
            Engagement score (0-10)
        """
        try:
            from database import MessageOperations
            
            messages = MessageOperations.get_messages_by_lead(db_session, lead['id'])
            
            if not messages:
                return 0
            
            score = 0
            
            # Base score for having messages
            score += min(len(messages) * 0.5, 3)  # Max 3 points for message count
            
            # Bonus for recent activity
            if messages:
                last_message = max(messages, key=lambda m: m.timestamp)
                # Handle both timezone-aware and naive datetimes
                now = datetime.now(timezone.utc)
                msg_time = last_message.timestamp
                
                # Convert naive datetime to aware if needed
                if msg_time.tzinfo is None:
                    msg_time = msg_time.replace(tzinfo=timezone.utc)
                
                days_since = (now - msg_time).days
                if days_since <= 7:
                    score += 2
                elif days_since <= 14:
                    score += 1
            
            # Bonus for inbound responses
            inbound_count = sum(1 for msg in messages if msg.direction == "inbound")
            score += min(inbound_count * 1.5, 3)  # Max 3 points for responses
            
            # Bonus for status progression
            status_scores = {
                'new': 0,
                'contacted': 1,
                'engaged': 2,
                'meeting_scheduled': 3,
                'attended': 4,
                'converted': 5
            }
            score += status_scores.get(lead.get('status', 'new'), 0)
            
            return min(int(score), 10)  # Cap at 10
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement score: {str(e)}")
            return 0
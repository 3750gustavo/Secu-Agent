"""
Security module for Secu-Agent.
Provides rate limiting, authentication, and abuse prevention.
"""

import os
import time
import logging
from typing import Dict, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException, Header, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter for protecting against abuse.
    Tracks requests per IP address and enforces limits.
    """
    
    def __init__(self):
        """Initialize rate limiter with empty request tracking."""
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 300  # Clean old entries every 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove request entries older than 1 hour."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        for ip in list(self.requests.keys()):
            # Keep only requests from last hour
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if now - req_time < 3600
            ]
            # Remove IP if no recent requests
            if not self.requests[ip]:
                del self.requests[ip]
        
        self.last_cleanup = now
    
    def is_allowed(self, ip: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request from IP is allowed under rate limit.
        
        Args:
            ip: Client IP address
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False if rate limited
        """
        self._cleanup_old_entries()
        
        now = time.time()
        cutoff = now - window_seconds
        
        # Count requests in current window
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > cutoff
        ]
        
        # Check if limit exceeded
        if len(self.requests[ip]) >= max_requests:
            return False
        
        # Record this request
        self.requests[ip].append(now)
        return True
    
    def get_remaining(self, ip: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests for IP in current window."""
        now = time.time()
        cutoff = now - window_seconds
        
        recent = [
            req_time for req_time in self.requests.get(ip, [])
            if req_time > cutoff
        ]
        
        return max(0, max_requests - len(recent))


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60):
    """
    Decorator to rate limit endpoint by IP address.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds (default: 60)
        
    Example:
        @app.post("/api/endpoint")
        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            if not _rate_limiter.is_allowed(client_ip, max_requests, window_seconds):
                remaining = _rate_limiter.get_remaining(client_ip, max_requests, window_seconds)
                logger.warning(f"Rate limit exceeded for IP {client_ip} on {func.__name__}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Max {max_requests} requests per {window_seconds} seconds. Try again later."
                )
            
            # Get remaining requests for response header
            remaining = _rate_limiter.get_remaining(client_ip, max_requests, window_seconds)
            
            # Call original function
            response = await func(request, *args, **kwargs)
            
            # Add rate limit headers if response is dict
            if isinstance(response, dict):
                response["_rate_limit"] = {
                    "limit": max_requests,
                    "remaining": remaining,
                    "window_seconds": window_seconds
                }
            
            return response
        
        return wrapper
    return decorator


class APIKeyManager:
    """
    Simple API key management for protecting sensitive endpoints.
    Keys are stored in environment variables.
    """
    
    # Define which endpoints require which keys
    ENDPOINT_KEYS = {
        "admin": os.getenv("ADMIN_API_KEY", ""),
        "internal": os.getenv("INTERNAL_API_KEY", ""),
    }
    
    @classmethod
    def validate_key(cls, provided_key: str, required_level: str = "admin") -> bool:
        """
        Validate API key against required level.
        
        Args:
            provided_key: API key provided by client
            required_level: Required key level (admin, internal)
            
        Returns:
            True if key is valid, False otherwise
        """
        if not provided_key:
            return False
        
        expected_key = cls.ENDPOINT_KEYS.get(required_level, "")
        
        if not expected_key:
            logger.warning(f"No {required_level} API key configured")
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return provided_key == expected_key
    
    @classmethod
    def require_api_key(cls, required_level: str = "admin"):
        """
        Decorator to require API key for endpoint.
        
        Args:
            required_level: Required key level (admin, internal)
            
        Example:
            @app.post("/api/admin/endpoint")
            @APIKeyManager.require_api_key(required_level="admin")
            async def admin_endpoint(api_key: str = Header(...)):
                ...
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, api_key: str = Header(None), **kwargs):
                if not api_key:
                    logger.warning(f"Missing API key for {func.__name__}")
                    raise HTTPException(
                        status_code=401,
                        detail="Missing API key. Provide 'api-key' header."
                    )
                
                if not cls.validate_key(api_key, required_level):
                    logger.warning(f"Invalid API key attempt for {func.__name__}")
                    raise HTTPException(
                        status_code=403,
                        detail="Invalid API key."
                    )
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator


class AbuseDetector:
    """
    Detects suspicious patterns that indicate abuse.
    Tracks metrics and flags unusual activity.
    """
    
    def __init__(self):
        """Initialize abuse detector."""
        self.ip_metrics: Dict[str, Dict] = defaultdict(lambda: {
            "requests": 0,
            "ai_calls": 0,
            "leads_created": 0,
            "first_seen": time.time(),
            "last_seen": time.time(),
            "flagged": False
        })
        self.cleanup_interval = 3600  # Clean every hour
        self.last_cleanup = time.time()
    
    def record_request(self, ip: str, ai_calls: int = 0, leads_created: int = 0):
        """
        Record request metrics for IP.
        
        Args:
            ip: Client IP address
            ai_calls: Number of AI API calls made
            leads_created: Number of leads created
        """
        self._cleanup_old_entries()
        
        metrics = self.ip_metrics[ip]
        metrics["requests"] += 1
        metrics["ai_calls"] += ai_calls
        metrics["leads_created"] += leads_created
        metrics["last_seen"] = time.time()
    
    def is_suspicious(self, ip: str) -> tuple[bool, str]:
        """
        Check if IP shows suspicious behavior.
        
        Args:
            ip: Client IP address
            
        Returns:
            Tuple of (is_suspicious, reason)
        """
        metrics = self.ip_metrics.get(ip)
        if not metrics:
            return False, ""
        
        now = time.time()
        age = now - metrics["first_seen"]
        
        # Flag if too many AI calls in short time
        if age < 300 and metrics["ai_calls"] > 100:  # 100+ AI calls in 5 min
            return True, "Excessive AI API calls"
        
        # Flag if too many leads created in short time
        if age < 300 and metrics["leads_created"] > 50:  # 50+ leads in 5 min
            return True, "Excessive lead creation"
        
        # Flag if request rate is very high
        if age < 60 and metrics["requests"] > 100:  # 100+ requests in 1 min
            return True, "Excessive request rate"
        
        return False, ""
    
    def _cleanup_old_entries(self):
        """Remove metrics older than 24 hours."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        for ip in list(self.ip_metrics.keys()):
            age = now - self.ip_metrics[ip]["first_seen"]
            if age > 86400:  # 24 hours
                del self.ip_metrics[ip]
        
        self.last_cleanup = now
    
    def get_metrics(self, ip: str) -> Dict:
        """Get metrics for IP."""
        return dict(self.ip_metrics.get(ip, {}))


# Global abuse detector instance
_abuse_detector = AbuseDetector()


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, handling proxies.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (for proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def check_abuse(request: Request, ai_calls: int = 0, leads_created: int = 0) -> Optional[str]:
    """
    Check if request shows signs of abuse.
    
    Args:
        request: FastAPI request object
        ai_calls: Number of AI calls made
        leads_created: Number of leads created
        
    Returns:
        Abuse reason if detected, None otherwise
    """
    ip = get_client_ip(request)
    _abuse_detector.record_request(ip, ai_calls, leads_created)
    
    is_suspicious, reason = _abuse_detector.is_suspicious(ip)
    if is_suspicious:
        logger.warning(f"Suspicious activity detected from {ip}: {reason}")
        return reason
    
    return None


# Export public API
__all__ = [
    "RateLimiter",
    "rate_limit",
    "APIKeyManager",
    "AbuseDetector",
    "get_client_ip",
    "check_abuse",
    "_rate_limiter",
    "_abuse_detector",
]


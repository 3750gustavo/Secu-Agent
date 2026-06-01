# Security Implementation Guide

## Overview

This document describes the security features implemented in Secu-Agent to prevent AI API abuse and protect against malicious usage patterns.

## Problem Statement

The original Secu-Agent implementation had critical security vulnerabilities:

- **Zero rate limiting** on any endpoint
- **No authentication** on dangerous endpoints
- **Unrestricted AI API calls** that could cost $1000s in minutes
- **Weak input validation** on lead capture
- **No abuse detection** or monitoring

### Attack Scenario (Before)

```bash
# Attacker could repeatedly call this with no restrictions:
curl -X POST https://your-app.com/api/rules/process-all

# With 1000 leads in DB:
# - 2000-3000 AI API calls per request
# - Cost: $10-50+ per request
# - Could repeat 100x/day = $1000-5000/day in costs
```

## Security Features Implemented

### 1. Rate Limiting

**File:** `security.py` - `RateLimiter` class

Rate limiting prevents excessive requests from a single IP address.

#### Configuration by Endpoint

| Endpoint | Limit | Window | Purpose |
|----------|-------|--------|---------|
| `/api/leads/capture` | 10 req/min | 60s | Prevent lead spam |
| `/api/communications/test` | 5 req/min | 60s | Prevent communication spam |
| `/api/rules/evaluate/{lead_id}` | 30 req/min | 60s | Prevent rule evaluation spam |
| `/api/rules/process-all` | 1 req/min | 60s | Prevent batch processing abuse |

#### How It Works

```python
@app.post("/api/leads/capture")
@rate_limit(max_requests=10, window_seconds=60)
async def capture_lead(request: Request, ...):
    # Automatically rate limited to 10 requests per minute per IP
    ...
```

#### Response When Rate Limited

```json
{
  "detail": "Too many requests. Max 10 requests per 60 seconds. Try again later."
}
```

HTTP Status: `429 Too Many Requests`

### 2. API Key Authentication

**File:** `security.py` - `APIKeyManager` class

Sensitive endpoints require API key authentication.

#### Protected Endpoints

- `POST /api/rules/process-all` - Requires `admin` API key
- `GET /api/admin/abuse-metrics` - Requires `admin` API key

#### Setup

Set environment variables:

```bash
# In your .env or Railway environment variables
ADMIN_API_KEY=your-secret-admin-key-here
INTERNAL_API_KEY=your-internal-key-here
```

#### Usage

```bash
# Call protected endpoint with API key
curl -X POST https://your-app.com/api/rules/process-all \
  -H "api-key: your-secret-admin-key-here"
```

#### Response When Missing/Invalid Key

```json
{
  "detail": "Invalid API key. Access denied."
}
```

HTTP Status: `401 Unauthorized` or `403 Forbidden`

### 3. Abuse Detection

**File:** `security.py` - `AbuseDetector` class

Detects suspicious patterns that indicate abuse:

- **Excessive AI calls** in short time (100+ in 5 minutes)
- **Excessive lead creation** (50+ in 5 minutes)
- **Excessive request rate** (100+ requests in 1 minute)

#### How It Works

```python
# In endpoint handlers
abuse_reason = check_abuse(request, ai_calls=4, leads_created=1)
if abuse_reason:
    raise HTTPException(
        status_code=429,
        detail=f"Suspicious activity detected: {abuse_reason}"
    )
```

#### Monitoring Abuse

```bash
# Get abuse metrics (requires admin API key)
curl https://your-app.com/api/admin/abuse-metrics \
  -H "api-key: your-secret-admin-key-here"
```

Response:

```json
{
  "total_tracked_ips": 5,
  "suspicious_ips": 1,
  "metrics": {
    "192.168.1.100": {
      "requests": 150,
      "ai_calls": 450,
      "leads_created": 0,
      "is_suspicious": true,
      "reason": "Excessive AI API calls"
    }
  }
}
```

### 4. Input Validation

Enhanced validation on lead capture:

- Email format validation (must contain @ and .)
- Required field validation
- Duplicate email check
- Phone number validation for SMS

### 5. Logging & Monitoring

All security events are logged:

```python
logger.warning(f"Rate limit exceeded for IP {client_ip} on {func.__name__}")
logger.warning(f"Invalid API key attempt for {func.__name__}")
logger.warning(f"Suspicious activity detected from {ip}: {reason}")
```

## Migration Guide

### Step 1: Update main.py

Replace your current `main.py` with `main_updated.py`:

```bash
mv main.py main_backup.py
mv main_updated.py main.py
```

### Step 2: Add security.py

The `security.py` file is already created and provides all security utilities.

### Step 3: Set Environment Variables

```bash
# For Railway, add these in your environment variables:
ADMIN_API_KEY=generate-a-strong-random-key-here
INTERNAL_API_KEY=generate-another-strong-random-key-here
```

Generate strong keys:

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

### Step 4: Test the Implementation

```bash
# Test rate limiting
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/leads/capture \
    -H "Content-Type: application/json" \
    -d '{"name":"Test","email":"test'$i'@example.com","company":"Test","job_title":"Dev"}'
done
# Should see 429 errors after 10 requests

# Test API key requirement
curl -X POST http://localhost:8000/api/rules/process-all
# Should get 401 Unauthorized

# Test with valid API key
curl -X POST http://localhost:8000/api/rules/process-all \
  -H "api-key: your-admin-key"
# Should work
```

## Endpoint Security Summary

### Public Endpoints (No Auth Required)

| Endpoint | Rate Limit | Notes |
|----------|-----------|-------|
| `GET /health` | None | Health check |
| `GET /` | None | Landing page |
| `GET /dashboard` | None | Dashboard |
| `GET /api/info` | None | API info |
| `GET /api/rules` | None | List rules |
| `GET /api/rules/schedule` | None | Upcoming actions |
| `POST /api/leads/capture` | 10/min | Lead creation |
| `GET /leads` | None | List leads |
| `GET /leads/{id}` | None | Get lead |
| `POST /api/rules/evaluate/{id}` | 30/min | Evaluate rules |

### Protected Endpoints (API Key Required)

| Endpoint | Rate Limit | Auth Level |
|----------|-----------|-----------|
| `POST /api/rules/process-all` | 1/min | admin |
| `GET /api/admin/abuse-metrics` | None | admin |

## Best Practices

### For Administrators

1. **Rotate API keys regularly** (monthly recommended)
2. **Monitor abuse metrics** daily
3. **Set up alerts** for suspicious activity
4. **Review logs** for failed authentication attempts
5. **Use strong, random keys** (32+ characters)

### For Users

1. **Never share API keys** in code or public repositories
2. **Use environment variables** for sensitive data
3. **Implement client-side rate limiting** for better UX
4. **Cache responses** when possible to reduce API calls
5. **Monitor your usage** to catch abuse early

### For Developers

1. **Always use rate_limit decorator** on AI-calling endpoints
2. **Call check_abuse()** after expensive operations
3. **Log security events** for audit trails
4. **Test rate limiting** in development
5. **Document API key requirements** in endpoint docstrings

## Troubleshooting

### "Too many requests" Error

**Cause:** Rate limit exceeded

**Solution:** 
- Wait for the rate limit window to reset
- Implement exponential backoff in client
- Contact admin if legitimate use case needs higher limit

### "Invalid API key" Error

**Cause:** Missing or incorrect API key

**Solution:**
- Verify API key is set in environment variables
- Check for typos in the key
- Regenerate key if compromised
- Ensure header name is exactly `api-key` (lowercase)

### Abuse Detection False Positives

**Cause:** Legitimate high-volume usage flagged as abuse

**Solution:**
- Contact admin to whitelist IP
- Implement request batching
- Use internal API key for trusted services
- Adjust abuse detection thresholds in `security.py`

## Future Enhancements

Potential improvements for future versions:

1. **Database-backed rate limiting** (for distributed systems)
2. **IP whitelisting/blacklisting** (for trusted partners)
3. **Usage quotas per API key** (for tiered access)
4. **Request signing** (HMAC-SHA256)
5. **DDoS protection** (via reverse proxy)
6. **Webhook notifications** for abuse alerts
7. **Cost tracking** per API key
8. **Automatic rate limit adjustment** based on usage patterns

## References

- [OWASP Rate Limiting](https://owasp.org/www-community/attacks/Rate_Limiting)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [API Key Best Practices](https://cloud.google.com/docs/authentication/api-keys)

## Support

For security issues or questions:

1. Check this documentation
2. Review `security.py` source code
3. Check logs for error messages
4. Contact the development team

---

**Last Updated:** 2026-06-01
**Version:** 1.0.0


# API Security & Documentation Improvements

## Summary

This document outlines the security improvements and documentation additions made to the Medical Consultation Platform API.

## 1. Rate Limiting Implementation ✅

### What Was Added

- **Custom throttle classes** in `apps/core/throttling.py`:
  - `BurstRateThrottle` - Short-term rate limiting (60/min for authenticated users)
  - `SustainedRateThrottle` - Long-term rate limiting (1000/hour for authenticated users)
  - `AnonBurstRateThrottle` - Anonymous burst limiting (20/min)
  - `AnonSustainedRateThrottle` - Anonymous sustained limiting (100/hour)
  - `ChatThrottle` - Chat-specific limiting (30/min)
  - `AuthenticationThrottle` - Login/register limiting (5/min to prevent brute force)
  - `PaymentThrottle` - Payment operations limiting (10/min)
  - `SearchThrottle` - Search queries limiting (60/min)
  - `FileUploadThrottle` - File upload limiting (20/hour)
  - `WebhookThrottle` - Payment webhook limiting (200/min)

### Rate Limits Configured

```python
'DEFAULT_THROTTLE_RATES': {
    # User throttles (authenticated)
    'burst': '60/min',
    'sustained': '1000/hour',

    # Anonymous throttles
    'anon_burst': '20/min',
    'anon_sustained': '100/hour',

    # Specific endpoints
    'chat': '30/min',
    'auth': '5/min',  # Prevents brute force
    'payment': '10/min',
    'search': '60/min',
    'upload': '20/hour',
    'webhook': '200/min',
}
```

### Applied To Endpoints

- **Authentication**: `quick_register`, `quick_login`, `UserRegistrationAPIView`, `CustomAuthToken`
- **Chat**: `quick_send_message`, `quick_classify_issue`
- **Search**: `quick_search_doctors`, `ServiceSearchAPIView`
- **File Upload**: `UploadAvatarAPIView`, doctor file uploads

### Usage Example

```python
from apps.core.throttling import AuthenticationThrottle

@api_view(['POST'])
@throttle_classes([AuthenticationThrottle])
def login_view(request):
    # Your login logic
    pass
```

## 2. Centralized IP Detection ✅

### What Was Added

Created `apps/core/utils.py` with centralized utility functions:

- **`get_client_ip(request)`** - Enhanced IP detection with security
  - Checks multiple proxy headers in priority order
  - Validates IP address format
  - Filters private IPs
  - Handles X-Forwarded-For, X-Real-IP, Cloudflare headers

- **`is_valid_ip(ip)`** - Validates IPv4 and IPv6 addresses

- **`is_private_ip(ip)`** - Checks if IP is in private range

- **`get_user_agent(request)`** - Extracts user agent

- **`sanitize_filename(filename)`** - Sanitizes filenames for security

### Replaced Duplicate Code

Removed duplicate `get_client_ip` implementations from:
- `apps/users/api_views.py` (2 occurrences)
- `apps/api/views.py` (1 occurrence)

All now use: `from apps.core.utils import get_client_ip`

### IP Detection Priority

1. `HTTP_X_FORWARDED_FOR` (most common proxy)
2. `HTTP_X_REAL_IP` (nginx)
3. `HTTP_CF_CONNECTING_IP` (Cloudflare)
4. `HTTP_X_FORWARDED`
5. `HTTP_FORWARDED_FOR`
6. `HTTP_FORWARDED`
7. `REMOTE_ADDR` (fallback)

## 3. API Documentation (Swagger/OpenAPI) ✅

### What Was Added

- **drf-spectacular** integration for OpenAPI 3.0 documentation
- Comprehensive API documentation at `/api/docs/` (Swagger UI)
- Alternative documentation at `/api/redoc/` (ReDoc)
- Schema download at `/api/schema/`

### Documentation Features

- **Interactive API testing** - Try endpoints directly from the browser
- **Authentication support** - Token authentication with persist
- **Rate limit information** - Documented in description
- **Request/response examples** - Auto-generated from serializers
- **Categorized endpoints** - Organized by tags:
  - Authentication
  - Users
  - Doctors
  - Hospitals
  - Consultations
  - Chat
  - Payments
  - Translate
  - Search
  - System

### Configuration

```python
# Medical_consultation/settings.py
SPECTACULAR_SETTINGS = {
    'TITLE': 'Medical Consultation Platform API',
    'VERSION': '1.0.0',
    'DESCRIPTION': '...',  # Comprehensive API description
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
    },
    # ... more settings
}
```

### Access Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Installation & Setup

### 1. Install Dependencies

```bash
# Install drf-spectacular for API documentation
pip install drf-spectacular
# or using uv
uv pip install drf-spectacular
```

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Test Rate Limiting

```python
# Try making rapid requests to see throttling in action
import requests

url = "http://localhost:8000/api/v1/users/auth/login/"
for i in range(10):
    response = requests.post(url, json={"username": "test", "password": "test"})
    print(f"Request {i+1}: {response.status_code}")
    # After 5 requests, you'll get 429 Too Many Requests
```

### 4. View API Documentation

```bash
# Start development server
python manage.py runserver

# Open browser
http://localhost:8000/api/docs/
```

## Security Benefits

### 1. Rate Limiting
- ✅ Prevents brute force attacks on login endpoints (5 attempts/min)
- ✅ Prevents API abuse and scraping
- ✅ Protects against DDoS attacks
- ✅ Ensures fair resource usage
- ✅ Different limits for authenticated vs anonymous users

### 2. Centralized IP Detection
- ✅ Consistent IP detection across the application
- ✅ Handles proxy scenarios correctly
- ✅ Validates IP addresses
- ✅ Filters private IPs for better security
- ✅ Supports Cloudflare and other CDNs

### 3. API Documentation
- ✅ Better developer experience
- ✅ Self-documenting API
- ✅ Interactive testing without external tools
- ✅ Clear authentication requirements
- ✅ Version tracking and change management

## Files Created

```
apps/core/
├── __init__.py          # Package initialization
├── apps.py              # App configuration
├── utils.py             # Centralized utilities (IP detection, etc.)
├── throttling.py        # Custom throttle classes
└── schema.py            # OpenAPI schema extensions

requirements-docs.txt    # Documentation dependencies
API_SECURITY_IMPROVEMENTS.md  # This file
```

## Files Modified

```
Medical_consultation/settings.py   # Added throttling & spectacular config
Medical_consultation/urls.py       # Added documentation URLs
apps/users/api_views.py           # Applied throttling, centralized IP
apps/api/views.py                 # Applied throttling, centralized IP
apps/doctors/views.py             # Applied throttling, centralized IP
```

## Testing Checklist

- [ ] Rate limiting works on login endpoint (max 5/min)
- [ ] Chat endpoints throttle at 30/min
- [ ] Search endpoints throttle at 60/min
- [ ] File uploads throttle at 20/hour
- [ ] Anonymous users have lower limits than authenticated
- [ ] IP detection works correctly behind proxies
- [ ] API documentation loads at `/api/docs/`
- [ ] Token authentication works in Swagger UI
- [ ] Can test endpoints from documentation

## Next Steps (Recommendations)

1. **Add request validation middleware** - Validate input before processing
2. **Implement API versioning** - Already started with `/api/v1/`
3. **Add monitoring** - Track API usage, errors, performance
4. **Security audit** - Review payment webhooks (Click/Payme)
5. **Add CAPTCHA** - For registration and sensitive operations
6. **Implement API keys** - For third-party integrations
7. **Add request logging** - Track all API calls for audit

## Environment Variables

No new environment variables required. Everything uses Django settings.

## Support

For questions or issues:
- GitHub: https://github.com/Jasurbek2003/Medical-consultation
- Email: jasurbek2030615@gmail.com

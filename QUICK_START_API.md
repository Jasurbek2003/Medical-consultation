# Quick Start Guide - API Security & Documentation

## 🚀 Getting Started

### 1. Install New Dependencies

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install drf-spectacular
uv pip install "drf-spectacular>=0.27.0"
```

### 2. Apply Migrations (if needed)

```bash
python manage.py migrate
```

### 3. Start Development Server

```bash
python manage.py runserver
```

### 4. Access API Documentation

Open your browser and visit:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

---

## 📖 Using the API Documentation

### Swagger UI Features

1. **Authentication**
   - Click "Authorize" button (top right)
   - Enter: `Token <your-token>`
   - Click "Authorize"
   - Now all requests will include your token

2. **Try Endpoints**
   - Expand any endpoint
   - Click "Try it out"
   - Fill in parameters
   - Click "Execute"
   - See response below

3. **Search Endpoints**
   - Use the search box at top
   - Filter by tags (Authentication, Users, Doctors, etc.)

4. **Download Schema**
   - Visit http://localhost:8000/api/schema/
   - Save as `schema.yml` or `schema.json`

### Getting an Auth Token

1. **Via Swagger UI**:
   - Go to http://localhost:8000/api/docs/
   - Find "Authentication" section
   - Expand `POST /api/v1/users/auth/login/`
   - Click "Try it out"
   - Enter credentials
   - Copy token from response

2. **Via cURL**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/users/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username": "your_username", "password": "your_password"}'
   ```

3. **Via Python**:
   ```python
   import requests

   response = requests.post(
       "http://localhost:8000/api/v1/users/auth/login/",
       json={"username": "your_username", "password": "your_password"}
   )
   token = response.json()["token"]
   print(f"Token: {token}")
   ```

---

## 🔒 Understanding Rate Limits

### General Limits

| User Type | Burst | Sustained |
|-----------|-------|-----------|
| **Authenticated** | 60/min | 1000/hr |
| **Anonymous** | 20/min | 100/hr |

### Endpoint-Specific Limits

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| Login/Register | 5/min | Prevent brute force |
| Chat | 30/min | Prevent spam |
| Search | 60/min | Prevent scraping |
| File Upload | 20/hr | Prevent storage abuse |
| Payments | 10/min | Prevent fraud |
| Webhooks | 200/min | Allow payment providers |

### Rate Limit Response

When you exceed the limit, you'll get:

```json
{
  "detail": "Request was throttled. Expected available in 45 seconds."
}
```

**Status Code**: `429 Too Many Requests`

**Headers**:
- `Retry-After`: Seconds until you can retry
- `X-RateLimit-Limit`: Your rate limit
- `X-RateLimit-Remaining`: Requests remaining

---

## 💡 Code Examples

### 1. Making Authenticated Requests

**Python**:
```python
import requests

headers = {
    "Authorization": "Token YOUR_TOKEN_HERE",
    "Content-Type": "application/json"
}

response = requests.get(
    "http://localhost:8000/api/v1/users/profile/",
    headers=headers
)

print(response.json())
```

**JavaScript**:
```javascript
const token = 'YOUR_TOKEN_HERE';

fetch('http://localhost:8000/api/v1/users/profile/', {
  headers: {
    'Authorization': `Token ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log(data));
```

**cURL**:
```bash
curl -H "Authorization: Token YOUR_TOKEN_HERE" \
     http://localhost:8000/api/v1/users/profile/
```

### 2. Handling Rate Limits

**Python with Retry**:
```python
import requests
import time

def api_call_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")

# Usage
headers = {"Authorization": "Token YOUR_TOKEN"}
response = api_call_with_retry(
    "http://localhost:8000/api/v1/doctors/",
    headers
)
```

### 3. Search Doctors

```python
import requests

# Search by name or specialty
params = {
    'q': 'cardiologist',
    'region': 'Tashkent',
    'online_only': 'true'
}

response = requests.get(
    'http://localhost:8000/api/doctors/search/',
    params=params
)

doctors = response.json()
for doctor in doctors['results']:
    print(f"{doctor['name']} - {doctor['specialty']}")
```

### 4. Send Chat Message

```python
import requests

headers = {"Authorization": "Token YOUR_TOKEN"}

response = requests.post(
    'http://localhost:8000/api/chat/quick-message/',
    headers=headers,
    json={
        'message': 'I have a headache and fever'
    }
)

result = response.json()
print(f"AI Response: {result['ai_response']['content']}")
print(f"Recommended Doctors: {len(result['recommended_doctors'])}")
```

### 5. Upload Doctor Files

```python
import requests

headers = {"Authorization": "Token YOUR_DOCTOR_TOKEN"}

files = {
    'file': open('medical_license.pdf', 'rb')
}

data = {
    'file_type': 'license',
    'description': 'Medical license document'
}

response = requests.post(
    'http://localhost:8000/api/v1/doctors/upload-file/',
    headers=headers,
    files=files,
    data=data
)

print(response.json())
```

---

## 🔧 Developer Tools

### 1. Test Rate Limiting

```python
import requests

url = "http://localhost:8000/api/v1/users/auth/login/"

# This will hit the rate limit after 5 requests
for i in range(10):
    response = requests.post(url, json={
        "username": "test",
        "password": "test"
    })
    print(f"Request {i+1}: {response.status_code}")
    if response.status_code == 429:
        print(f"Rate limited! Retry after: {response.headers.get('Retry-After')} seconds")
        break
```

### 2. Get Client IP (Backend)

```python
from apps.core.utils import get_client_ip

def my_view(request):
    client_ip = get_client_ip(request)
    print(f"Request from IP: {client_ip}")

    # Use IP for logging, analytics, etc.
    # ...
```

### 3. Apply Custom Throttling (Backend)

```python
from rest_framework.decorators import api_view, throttle_classes
from apps.core.throttling import SearchThrottle

@api_view(['GET'])
@throttle_classes([SearchThrottle])
def my_search_view(request):
    # This endpoint is now limited to 60 requests/min
    query = request.GET.get('q')
    # ... search logic
```

---

## 📊 Monitoring

### Check Rate Limit Status

Most endpoints return rate limit headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

### Track API Usage

```python
import requests

response = requests.get(
    'http://localhost:8000/api/stats/',
    headers={'Authorization': 'Token YOUR_TOKEN'}
)

stats = response.json()
print(f"Total API calls today: {stats['total_requests']}")
```

---

## 🐛 Troubleshooting

### Issue: "429 Too Many Requests"

**Solution**: You've hit the rate limit. Wait for the time specified in `Retry-After` header.

```python
retry_after = response.headers.get('Retry-After', 60)
time.sleep(int(retry_after))
# Retry request
```

### Issue: "Invalid token" in Swagger UI

**Solution**: Make sure to include "Token " prefix:
- ✅ Correct: `Token abc123def456`
- ❌ Wrong: `abc123def456`

### Issue: CORS errors in frontend

**Solution**: Your frontend domain should be in `CORS_ALLOWED_ORIGINS`:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://yourdomain.com",
]
```

### Issue: IP detection behind proxy

**Solution**: Configure proxy headers in your web server:

**Nginx**:
```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**Cloudflare**: Already supported via `HTTP_CF_CONNECTING_IP`

---

## 🎯 Best Practices

### 1. Always Use Authentication
```python
# ✅ Good
headers = {"Authorization": f"Token {token}"}
response = requests.get(url, headers=headers)

# ❌ Bad - will hit anonymous rate limits
response = requests.get(url)
```

### 2. Handle Rate Limits Gracefully
```python
# ✅ Good
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    time.sleep(retry_after)
    # Retry

# ❌ Bad
response = requests.get(url)
# Ignore errors
```

### 3. Cache Responses When Possible
```python
# ✅ Good - cache doctor list
doctors = cache.get('doctors_list')
if not doctors:
    doctors = fetch_doctors()
    cache.set('doctors_list', doctors, 300)  # 5 min

# ❌ Bad - fetch every time
doctors = fetch_doctors()
```

### 4. Use Batch Endpoints
```python
# ✅ Good - one request
response = requests.post('/api/translate/batch/', json={
    'texts': ['text1', 'text2', 'text3']
})

# ❌ Bad - three requests
for text in texts:
    requests.post('/api/translate/', json={'text': text})
```

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/api/docs/
- **Rate Limiting Details**: [API_SECURITY_IMPROVEMENTS.md](./API_SECURITY_IMPROVEMENTS.md)
- **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **Project Guide**: [CLAUDE.md](./CLAUDE.md)

---

## 🆘 Support

- **GitHub Issues**: https://github.com/Jasurbek2003/Medical-consultation/issues
- **Email**: jasurbek2030615@gmail.com

---

**Happy coding!** 🎉

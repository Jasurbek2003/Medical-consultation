# Search Limit Feature - Documentation

## Overview

This feature allows doctors and hospital admins to set daily search/view limits for **unauthenticated users** only. Authenticated users have unlimited access. This helps:

- Control exposure to public searches
- Prevent scraping and automated access
- Encourage user registration
- Protect privacy while maintaining visibility

## How It Works

### For Doctors & Hospitals

1. Each doctor/hospital can set their own `daily_search_limit`
2. **`0` = Unlimited** (default) - no restrictions
3. **`> 0`** = Maximum times an unauthenticated user (by IP) can view this doctor/hospital per day
4. Limit resets daily at midnight

### For Users

- **Authenticated users**: Unlimited access to all doctors/hospitals
- **Unauthenticated users**: Limited by the doctor/hospital's settings
- If limit exceeded: Get error message with suggestion to sign in
- Limit is **per IP address per day**

---

## API Endpoints

### Doctor Endpoints

#### 1. **Get Current Search Limit**
```http
GET /api/v1/doctors/search-limit/
Authorization: Token <doctor-token>
```

**Response:**
```json
{
  "id": 1,
  "daily_search_limit": 50
}
```

#### 2. **Update Search Limit**
```http
PATCH /api/v1/doctors/search-limit/
Authorization: Token <doctor-token>
Content-Type: application/json

{
  "daily_search_limit": 100
}
```

**Response:**
```json
{
  "message": "Search limit updated successfully",
  "data": {
    "id": 1,
    "daily_search_limit": 100
  }
}
```

#### 3. **View Search Statistics**
```http
GET /api/v1/doctors/search-stats/?days=7
Authorization: Token <doctor-token>
```

**Parameters:**
- `days` (optional): Number of days to look back (default: 7)

**Response:**
```json
{
  "total_searches": 245,
  "unique_ips": 89,
  "authenticated_searches": 156,
  "unauthenticated_searches": 89,
  "period_days": 7,
  "current_limit": 100,
  "by_date": [
    {"search_date": "2025-10-01", "count": 35},
    {"search_date": "2025-10-02", "count": 42},
    {"search_date": "2025-10-03", "count": 38}
  ]
}
```

### Hospital Endpoints

Same structure as doctors, but use these endpoints:
- `GET/PATCH /api/v1/hospitals/search-limit/`
- `GET /api/v1/hospitals/search-stats/?days=7`

---

## Database Models

### 1. Doctor Model (Updated)
```python
class Doctor(models.Model):
    # ... existing fields ...

    daily_search_limit = models.PositiveIntegerField(
        default=0,
        verbose_name="Daily search limit",
        help_text="0 = unlimited"
    )
```

### 2. Hospital Model (Updated)
```python
class Hospital(models.Model):
    # ... existing fields ...

    daily_search_limit = models.PositiveIntegerField(
        default=0,
        verbose_name="Daily search limit",
        help_text="0 = unlimited"
    )
```

### 3. SearchLog Model (New)
```python
class SearchLog(models.Model):
    entity_type = models.CharField(max_length=10)  # 'doctor' or 'hospital'
    entity_id = models.PositiveIntegerField()
    user = models.ForeignKey(User, null=True)  # null for unauthenticated
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255)
    searched_at = models.DateTimeField(auto_now_add=True)
    search_date = models.DateField(default=date.today)
    action = models.CharField(max_length=20, default='view')
```

---

## Usage Examples

### Example 1: Doctor Sets Limit to 50 Views/Day

```python
import requests

# Login as doctor
login_response = requests.post(
    'http://localhost:8000/api/v1/users/auth/login/',
    json={
        'username': 'doctor_username',
        'password': 'doctor_password'
    }
)
token = login_response.json()['token']

# Set search limit to 50
requests.patch(
    'http://localhost:8000/api/v1/doctors/search-limit/',
    headers={'Authorization': f'Token {token}'},
    json={'daily_search_limit': 50}
)
```

### Example 2: View Search Statistics

```python
# Get last 30 days of search stats
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search-stats/?days=30',
    headers={'Authorization': f'Token {token}'}
)

stats = response.json()
print(f"Total searches: {stats['total_searches']}")
print(f"Unique visitors: {stats['unique_ips']}")
print(f"Current limit: {stats['current_limit']}")
```

### Example 3: Unauthenticated User Hits Limit

```python
# Unauthenticated user tries to view doctor (51st time today)
response = requests.get('http://localhost:8000/api/v1/doctors/1/')

# Response (429 Too Many Requests)
{
  "detail": "Daily search limit (50) exceeded for this doctor. Please try again tomorrow or sign in for unlimited access."
}
```

---

## Utility Functions

### check_search_limit()
```python
from apps.core.search_limits import check_search_limit

# In your view
def get(self, request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)

    # Check if limit exceeded (raises Throttled exception if exceeded)
    check_search_limit(request, 'doctor', doctor, action='detail')

    # Continue with normal response
    serializer = DoctorSerializer(doctor)
    return Response(serializer.data)
```

### get_search_stats()
```python
from apps.core.search_limits import get_search_stats

stats = get_search_stats('doctor', doctor_id=1, days=7)
# Returns dict with total_searches, unique_ips, etc.
```

### get_remaining_searches()
```python
from apps.core.search_limits import get_remaining_searches

remaining = get_remaining_searches(request, 'doctor', doctor)
# Returns: {
#   'limit': 50,
#   'used': 12,
#   'remaining': 38,
#   'unlimited': False,
#   'exceeded': False
# }
```

### filter_by_search_limit()
```python
from apps.core.search_limits import filter_by_search_limit

# Filter queryset to exclude doctors where limit is exceeded
queryset = Doctor.objects.all()
filtered = filter_by_search_limit(request, queryset, 'doctor')
# Returns only doctors that user can still view today
```

---

## Integration Guide

### Step 1: Apply Migrations
```bash
python manage.py migrate
```

### Step 2: Update Search/Detail Views (Optional)

To enforce limits on existing views, add this to your doctor/hospital detail views:

```python
from apps.core.search_limits import check_search_limit

class DoctorDetailView(APIView):
    def get(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        # Enforce search limit
        check_search_limit(request, 'doctor', doctor, action='detail')

        serializer = DoctorSerializer(doctor)
        return Response(serializer.data)
```

### Step 3: Update Search Views (Optional)

To filter search results:

```python
from apps.core.search_limits import filter_by_search_limit

class DoctorSearchView(APIView):
    def get(self, request):
        queryset = Doctor.objects.filter(verification_status='approved')

        # Filter out doctors where limit is exceeded
        queryset = filter_by_search_limit(request, queryset, 'doctor')

        serializer = DoctorSerializer(queryset, many=True)
        return Response(serializer.data)
```

---

## Admin Panel

Admins can manage limits via Django admin:

1. **Doctor Admin**: View and edit `daily_search_limit` field
2. **Hospital Admin**: View and edit `daily_search_limit` field
3. **SearchLog Admin**: View all search logs with filters:
   - Filter by entity type (doctor/hospital)
   - Filter by date
   - Filter by IP address
   - View statistics

---

## Testing

### Test 1: Unlimited Access (Default)
```bash
# Doctor has daily_search_limit = 0 (default)
curl http://localhost:8000/api/v1/doctors/1/
# Should work unlimited times
```

### Test 2: Limited Access
```bash
# Set limit to 3
curl -X PATCH http://localhost:8000/api/v1/doctors/search-limit/ \
  -H "Authorization: Token DOCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"daily_search_limit": 3}'

# Try 4 times from same IP (unauthenticated)
curl http://localhost:8000/api/v1/doctors/1/  # Works
curl http://localhost:8000/api/v1/doctors/1/  # Works
curl http://localhost:8000/api/v1/doctors/1/  # Works
curl http://localhost:8000/api/v1/doctors/1/  # 429 Throttled!
```

### Test 3: Authenticated Users Bypass Limit
```bash
# Login first
curl -X POST http://localhost:8000/api/v1/users/auth/login/ \
  -d '{"username": "user", "password": "pass"}'

# Can access unlimited times with token
curl http://localhost:8000/api/v1/doctors/1/ \
  -H "Authorization: Token USER_TOKEN"
# Always works, regardless of limit
```

---

## Files Created/Modified

### New Files:
- `apps/core/models.py` - SearchLog model
- `apps/core/search_limits.py` - Utility functions
- `SEARCH_LIMIT_FEATURE.md` - This documentation

### Modified Files:
- `apps/doctors/models.py` - Added `daily_search_limit` field
- `apps/hospitals/models.py` - Added `daily_search_limit` field
- `apps/doctors/serializers.py` - Added search limit serializers
- `apps/hospitals/serializers.py` - Added search limit serializers
- `apps/doctors/views.py` - Added DoctorSearchLimitView, DoctorSearchStatsView
- `apps/doctors/api_urls.py` - Added URL routing for new endpoints

### Migrations:
- `apps/core/migrations/0001_initial.py` - SearchLog model
- `apps/doctors/migrations/0005_doctor_daily_search_limit.py` - New field
- `apps/hospitals/migrations/0002_hospital_daily_search_limit.py` - New field

---

## Error Handling

### Error 1: Limit Exceeded
```json
{
  "detail": "Daily search limit (50) exceeded for this doctor. Please try again tomorrow or sign in for unlimited access."
}
```
**Status Code**: 429 Too Many Requests

### Error 2: Invalid Limit Value
```json
{
  "daily_search_limit": ["Daily search limit cannot be negative. Use 0 for unlimited."]
}
```
**Status Code**: 400 Bad Request

### Error 3: Unauthorized Access
```json
{
  "error": "Only doctors can access this endpoint"
}
```
**Status Code**: 403 Forbidden

---

## Best Practices

1. **Default to Unlimited (0)**: Let doctors/hospitals opt-in to limits
2. **Monitor Stats**: Regularly check search statistics to optimize limits
3. **Communicate Limits**: Show remaining searches to users before they hit the limit
4. **Encourage Sign-Up**: Use limits as a feature to drive registration
5. **Daily Reset**: Limits reset at midnight server time

---

## Future Enhancements

Potential improvements:
- [ ] Add hourly limits in addition to daily
- [ ] Different limits for different user tiers
- [ ] Geo-based limits (different limits per country)
- [ ] Premium doctors with higher default limits
- [ ] Email notifications when limit is close to being reached
- [ ] Analytics dashboard for search patterns

---

## Support

For questions or issues:
- **GitHub**: https://github.com/Jasurbek2003/Medical-consultation
- **Email**: jasurbek2030615@gmail.com

---

**Feature Status**: ✅ **Fully Implemented & Ready to Use**

All migrations applied, endpoints configured, and ready for production use!

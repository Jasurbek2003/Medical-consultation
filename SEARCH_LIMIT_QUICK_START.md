# Search Limit Feature - Quick Start Guide

## ✅ Installation Complete!

All migrations have been applied and the feature is ready to use.

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Set a Search Limit (As Doctor)

```bash
# Login as a doctor
curl -X POST http://localhost:8000/api/v1/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "doctor_username",
    "password": "doctor_password"
  }'

# You'll get a token in the response
# TOKEN=your_token_here

# Set daily search limit to 100 views per IP per day
curl -X PATCH http://localhost:8000/api/v1/doctors/search-limit/ \
  -H "Authorization: Token TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"daily_search_limit": 100}'

# Response:
# {
#   "message": "Search limit updated successfully",
#   "data": {
#     "id": 1,
#     "daily_search_limit": 100
#   }
# }
```

### Step 2: View Your Statistics

```bash
curl http://localhost:8000/api/v1/doctors/search-stats/?days=7 \
  -H "Authorization: Token TOKEN"

# Response:
# {
#   "total_searches": 0,
#   "unique_ips": 0,
#   "authenticated_searches": 0,
#   "unauthenticated_searches": 0,
#   "period_days": 7,
#   "current_limit": 100,
#   "by_date": []
# }
```

### Step 3: Test the Limit (Optional)

The limit will automatically be enforced when you integrate it into your doctor detail/search views.

---

## 🔧 Integration into Existing Views

To enforce search limits on doctor/hospital detail views, add this code:

### Example: Doctor Detail View

```python
# apps/doctors/views.py

from apps.core.search_limits import check_search_limit
from rest_framework.exceptions import Throttled

class DoctorDetailView(APIView):
    def get(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        # ✨ Add this line to enforce search limits
        try:
            check_search_limit(request, 'doctor', doctor, action='detail')
        except Throttled as e:
            return Response(
                {'error': str(e.detail)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Rest of your code...
        serializer = DoctorSerializer(doctor)
        return Response(serializer.data)
```

### Example: Doctor Search View

```python
# apps/doctors/views.py

from apps.core.search_limits import filter_by_search_limit

class DoctorSearchView(APIView):
    def get(self, request):
        queryset = Doctor.objects.filter(verification_status='approved')

        # ✨ Add this line to filter out doctors where limit exceeded
        queryset = filter_by_search_limit(request, queryset, 'doctor')

        # Rest of your code...
        serializer = DoctorSerializer(queryset, many=True)
        return Response(serializer.data)
```

---

## 📊 Monitor Usage

### Check Your Search Stats

```python
import requests

response = requests.get(
    'http://localhost:8000/api/v1/doctors/search-stats/?days=30',
    headers={'Authorization': f'Token {your_token}'}
)

stats = response.json()
print(f"Total Searches: {stats['total_searches']}")
print(f"Unique Visitors: {stats['unique_ips']}")
print(f"Authenticated: {stats['authenticated_searches']}")
print(f"Unauthenticated: {stats['unauthenticated_searches']}")
```

### Update Your Limit Based on Traffic

```python
# If you're getting too much traffic, increase the limit
requests.patch(
    'http://localhost:8000/api/v1/doctors/search-limit/',
    headers={'Authorization': f'Token {your_token}'},
    json={'daily_search_limit': 200}  # Increased to 200
)

# Or set to unlimited
requests.patch(
    'http://localhost:8000/api/v1/doctors/search-limit/',
    headers={'Authorization': f'Token {your_token}'},
    json={'daily_search_limit': 0}  # 0 = unlimited
)
```

---

## 🎯 How Users Experience It

### Authenticated Users
✅ **Unlimited access** - No restrictions at all

```bash
# User is logged in with token
curl http://localhost:8000/api/v1/doctors/1/ \
  -H "Authorization: Token USER_TOKEN"

# Always works! Can access 1000+ times per day
```

### Unauthenticated Users
⚠️ **Limited by doctor's setting** - After limit is reached:

```bash
# First 100 requests work fine
curl http://localhost:8000/api/v1/doctors/1/  # ✅ OK
curl http://localhost:8000/api/v1/doctors/1/  # ✅ OK
# ... (98 more times) ...

# 101st request from same IP:
curl http://localhost:8000/api/v1/doctors/1/  # ❌ 429 Error

# Response:
{
  "error": "Daily search limit (100) exceeded for this doctor. Please try again tomorrow or sign in for unlimited access."
}
```

---

## 🏥 Hospital Admins

Same endpoints, just replace `/doctors/` with `/hospitals/`:

```bash
# Get hospital search limit
curl http://localhost:8000/api/v1/hospitals/search-limit/ \
  -H "Authorization: Token HOSPITAL_ADMIN_TOKEN"

# Update hospital search limit
curl -X PATCH http://localhost:8000/api/v1/hospitals/search-limit/ \
  -H "Authorization: Token HOSPITAL_ADMIN_TOKEN" \
  -d '{"daily_search_limit": 150}'

# View hospital search stats
curl http://localhost:8000/api/v1/hospitals/search-stats/?days=7 \
  -H "Authorization: Token HOSPITAL_ADMIN_TOKEN"
```

---

## 💡 Common Use Cases

### Use Case 1: Popular Doctor Wants Privacy
```python
# Set low limit to reduce public exposure
{"daily_search_limit": 10}
# Result: Only 10 anonymous views per IP per day
```

### Use Case 2: New Doctor Wants Maximum Exposure
```python
# Set unlimited to get discovered
{"daily_search_limit": 0}
# Result: Anyone can view unlimited times
```

### Use Case 3: Balanced Approach
```python
# Moderate limit encourages sign-ups
{"daily_search_limit": 50}
# Result: Casual browsers can view, heavy users need to register
```

---

## 🔍 Admin Panel Access

Admins can view and manage all search logs:

1. Go to Django Admin: `http://localhost:8000/admin/`
2. Navigate to **Core > Search Logs**
3. Filter by:
   - Entity type (Doctor/Hospital)
   - Date
   - IP address
   - User (if authenticated)

---

## 📝 Database Schema

Your database now has these new fields/tables:

### Doctor Table (Updated)
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| daily_search_limit | PositiveInteger | 0 | 0 = unlimited |

### Hospital Table (Updated)
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| daily_search_limit | PositiveInteger | 0 | 0 = unlimited |

### SearchLog Table (New)
| Field | Type | Description |
|-------|------|-------------|
| entity_type | CharField | 'doctor' or 'hospital' |
| entity_id | PositiveInteger | ID of doctor/hospital |
| user | ForeignKey | User (null if unauthenticated) |
| ip_address | GenericIPAddressField | User's IP |
| user_agent | CharField | Browser/device info |
| searched_at | DateTimeField | Timestamp |
| search_date | DateField | Date for daily grouping |
| action | CharField | 'view', 'search', 'detail' |

---

## 🎓 API Endpoints Reference

### Doctor Endpoints
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/doctors/search-limit/` | Required (Doctor) | Get current limit |
| PATCH | `/api/v1/doctors/search-limit/` | Required (Doctor) | Update limit |
| GET | `/api/v1/doctors/search-stats/?days=7` | Required (Doctor) | View statistics |

### Hospital Endpoints
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/hospitals/search-limit/` | Required (Hospital Admin) | Get current limit |
| PATCH | `/api/v1/hospitals/search-limit/` | Required (Hospital Admin) | Update limit |
| GET | `/api/v1/hospitals/search-stats/?days=7` | Required (Hospital Admin) | View statistics |

---

## ✅ Verification Checklist

- [x] Migrations applied (`python manage.py migrate`)
- [x] SearchLog model created
- [x] Doctor.daily_search_limit field added
- [x] Hospital.daily_search_limit field added
- [x] API endpoints configured
- [x] Serializers created
- [x] Utility functions available
- [ ] Integration into detail views (optional)
- [ ] Integration into search views (optional)

---

## 🆘 Troubleshooting

### Issue: "Field 'daily_search_limit' doesn't exist"
**Solution**: Run migrations
```bash
python manage.py migrate
```

### Issue: "SearchLog matching query does not exist"
**Solution**: This is normal on first use. Logs are created automatically when users search.

### Issue: "Only doctors can access this endpoint"
**Solution**: Make sure you're logged in as a doctor, not a patient or hospital admin.

### Issue: Limit not being enforced
**Solution**: You need to integrate `check_search_limit()` into your detail/search views (see integration examples above).

---

## 📚 Full Documentation

For complete documentation, see: [SEARCH_LIMIT_FEATURE.md](./SEARCH_LIMIT_FEATURE.md)

---

**Ready to use!** 🎉

Start by setting a limit as a doctor, then test it out!

# Doctor List/Search API - Complete Guide

## 🎯 Main Endpoint

```
GET /api/v1/doctors/list/
```

This is the **primary endpoint** for searching and listing doctors with:
- ✅ Full search & filtering capabilities
- ✅ Automatic search logging
- ✅ Search limit enforcement (for unauthenticated users)
- ✅ Automatic charging (for authenticated users)
- ✅ Rate limiting to prevent abuse

---

## 🔒 Rate Limits

| User Type | Limit |
|-----------|-------|
| **Authenticated** | 60 requests/min |
| **Unauthenticated** | 20 requests/min |

**What happens when limit exceeded:**
```json
{
  "detail": "Request was throttled. Expected available in 45 seconds."
}
```
**Status Code**: 429 Too Many Requests

---

## 💰 Charging System

### How It Works

1. **Unauthenticated Users**: No charges (free access)
2. **Authenticated Users**: Charged per doctor shown in search results (if doctor has configured search charge)

### Charging Rules

- ✅ Only charged **once per doctor per day** per user
- ✅ Charge amount set by each doctor individually
- ✅ Default: 0 (free) - doctors opt-in to charging
- ✅ Uses user's wallet balance
- ✅ Automatic deduction when searching

### Search Charges

When you search, you may be charged for each doctor in the results:

```python
# Doctor has configured search_charge = 1000 UZS
# When you search and this doctor appears in results:
# - First time today: Charged 1000 UZS
# - Later searches today: FREE (already paid)
# - Tomorrow: Charged again 1000 UZS (new day)
```

### How Doctors Set Charges

Doctors can configure their search charge:

```bash
# As a doctor, set your search charge
curl -X PATCH http://localhost:8000/api/v1/doctors/charges/ \
  -H "Authorization: Token DOCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "search_charge": 1000,
    "view_card_charge": 2000,
    "view_phone_charge": 5000
  }'
```

### Check Your Wallet Balance

```bash
# Check wallet before searching
curl http://localhost:8000/api/v1/payments/wallet/balance/ \
  -H "Authorization: Token YOUR_TOKEN"

# Response:
{
  "balance": 50000,
  "currency": "UZS"
}
```

---

## 🔍 Search & Filter Options

### 1. **Text Search**

```bash
# Search by name, specialty, workplace, bio, location
curl "http://localhost:8000/api/v1/doctors/list/?search=cardiologist"
```

### 2. **Filter by Specialty**

```bash
curl "http://localhost:8000/api/v1/doctors/list/?specialty=kardiolog"

# Available specialties:
# terapevt, stomatolog, kardiolog, urolog, ginekolog, pediatr,
# dermatolog, nevrolog, oftalmolog, lor, ortoped, psixiatr,
# endokrinolog, gastroenterolog, pulmonolog
```

### 3. **Filter by Location**

```bash
# By region
curl "http://localhost:8000/api/v1/doctors/list/?region=1"

# By district
curl "http://localhost:8000/api/v1/doctors/list/?district=5"

# Both
curl "http://localhost:8000/api/v1/doctors/list/?region=1&district=5"
```

### 4. **Filter by Price**

```bash
# Price range
curl "http://localhost:8000/api/v1/doctors/list/?min_price=50000&max_price=200000"

# Under 100k
curl "http://localhost:8000/api/v1/doctors/list/?max_price=100000"
```

### 5. **Filter by Experience**

```bash
# Minimum years
curl "http://localhost:8000/api/v1/doctors/list/?min_experience=10"

# By level
curl "http://localhost:8000/api/v1/doctors/list/?experience_level=senior"
# Options: junior (0-5), mid (6-15), senior (16+)
```

### 6. **Filter by Rating**

```bash
# 4 stars and above
curl "http://localhost:8000/api/v1/doctors/list/?min_rating=4.0"
```

### 7. **Filter by Availability**

```bash
# Currently available
curl "http://localhost:8000/api/v1/doctors/list/?is_available=true"

# Online consultation available
curl "http://localhost:8000/api/v1/doctors/list/?is_online_consultation=true"

# Available right now (based on schedule)
curl "http://localhost:8000/api/v1/doctors/list/?available_now=true"
```

### 8. **Filter by Hospital**

```bash
curl "http://localhost:8000/api/v1/doctors/list/?hospital=1"
```

### 9. **Combined Search**

```bash
curl "http://localhost:8000/api/v1/doctors/list/\
?specialty=kardiolog\
&region=1\
&min_rating=4.0\
&max_price=200000\
&is_available=true\
&ordering=-rating"
```

---

## 📊 Sorting

```bash
# Sort by rating (highest first)
curl "http://localhost:8000/api/v1/doctors/list/?ordering=-rating"

# Sort by price (lowest first)
curl "http://localhost:8000/api/v1/doctors/list/?ordering=consultation_price"

# Sort by experience (most first)
curl "http://localhost:8000/api/v1/doctors/list/?ordering=-experience"

# Sort by total reviews
curl "http://localhost:8000/api/v1/doctors/list/?ordering=-total_reviews"

# Default: Sorted by search_charge (highest paying doctors appear first), then rating
```

**Available ordering fields:**
- `rating`
- `total_reviews`
- `consultation_price`
- `experience`
- `charges__search_charge` (doctor's payment for ranking)

**Tip**: Use `-` prefix for descending order

---

## 📄 Pagination

Results are paginated (20 per page):

```bash
# Page 1 (default)
curl "http://localhost:8000/api/v1/doctors/list/"

# Page 2
curl "http://localhost:8000/api/v1/doctors/list/?page=2"

# Page 3
curl "http://localhost:8000/api/v1/doctors/list/?page=3"
```

**Response Format:**
```json
{
  "count": 156,
  "next": "http://localhost:8000/api/v1/doctors/list/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "first_name": "John",
        "last_name": "Doe"
      },
      "specialty": "kardiolog",
      "rating": 4.8,
      "consultation_price": 150000,
      "charges": {
        "search_charge": 1000,
        "view_card_charge": 2000
      }
    }
  ]
}
```

---

## 🚫 Search Limits (Unauthenticated Users)

Doctors can set daily search limits for unauthenticated users:

### How It Works

- Doctor sets `daily_search_limit = 50`
- Unauthenticated user can view this doctor **50 times per day** (per IP)
- After 50 views: Doctor is **hidden from search results**
- Next day: Limit resets

### Why You Might Not See Some Doctors

If you're searching without logging in and don't see many results, you may have hit search limits. **Sign in for unlimited access!**

```bash
# Sign in to bypass limits
curl -X POST http://localhost:8000/api/v1/users/auth/login/ \
  -d '{"username": "user", "password": "pass"}'

# Use token in subsequent requests
curl http://localhost:8000/api/v1/doctors/list/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 💡 Complete Examples

### Example 1: Find Affordable Cardiologists

```python
import requests

response = requests.get(
    'http://localhost:8000/api/v1/doctors/list/',
    params={
        'specialty': 'kardiolog',
        'max_price': 150000,
        'min_rating': 4.0,
        'ordering': 'consultation_price'  # Cheapest first
    }
)

doctors = response.json()['results']
print(f"Found {len(doctors)} affordable cardiologists:")
for doctor in doctors:
    name = f"{doctor['user']['first_name']} {doctor['user']['last_name']}"
    price = doctor['consultation_price']
    rating = doctor['rating']
    print(f"  - {name}: {price} UZS, {rating}⭐")
```

### Example 2: Find Top-Rated Doctors in Tashkent

```python
response = requests.get(
    'http://localhost:8000/api/v1/doctors/list/',
    params={
        'region': 1,  # Tashkent
        'min_rating': 4.5,
        'ordering': '-rating,-total_reviews'
    },
    headers={'Authorization': 'Token YOUR_TOKEN'}  # To avoid charges
)

doctors = response.json()['results'][:10]  # Top 10
for i, doc in enumerate(doctors, 1):
    print(f"{i}. Dr. {doc['user']['last_name']} - {doc['rating']}⭐ ({doc['total_reviews']} reviews)")
```

### Example 3: With Wallet Balance Check

```python
# Check balance first
wallet = requests.get(
    'http://localhost:8000/api/v1/payments/wallet/balance/',
    headers={'Authorization': 'Token YOUR_TOKEN'}
).json()

print(f"Wallet Balance: {wallet['balance']} UZS")

# Search (may incur charges)
response = requests.get(
    'http://localhost:8000/api/v1/doctors/list/',
    params={'specialty': 'kardiolog'},
    headers={'Authorization': 'Token YOUR_TOKEN'}
)

# Check balance after
wallet_after = requests.get(
    'http://localhost:8000/api/v1/payments/wallet/balance/',
    headers={'Authorization': 'Token YOUR_TOKEN'}
).json()

charged = wallet['balance'] - wallet_after['balance']
print(f"Charged: {charged} UZS")
print(f"New Balance: {wallet_after['balance']} UZS")
```

### Example 4: Handle Rate Limiting

```python
import requests
import time

def search_with_retry(params, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(
            'http://localhost:8000/api/v1/doctors/list/',
            params=params
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        if response.status_code == 200:
            return response.json()

        raise Exception(f"Error: {response.status_code}")

    raise Exception("Max retries exceeded")

# Usage
doctors = search_with_retry({'specialty': 'kardiolog'})
```

---

## 🔐 Authentication Benefits

### Unauthenticated Users

❌ Limited by doctor's daily_search_limit
❌ Subject to stricter rate limits (20/min)
✅ No charges
✅ Can still search and view

### Authenticated Users

✅ **Unlimited searches** (bypass daily limits)
✅ Higher rate limits (60/min)
❌ May be charged per doctor (if doctor configured)
✅ Charges are once per doctor per day
✅ Can track search history

---

## ⚠️ Error Responses

### 429 - Too Many Requests (Rate Limit)

```json
{
  "detail": "Request was throttled. Expected available in 45 seconds."
}
```

**Solution**: Wait and retry, or sign in for higher limits

### 402 - Payment Required (Insufficient Balance)

```json
{
  "error": "Insufficient wallet balance"
}
```

**Solution**: Top up your wallet

### 400 - Bad Request

```json
{
  "detail": "Invalid filter parameter"
}
```

**Solution**: Check your filter values

---

## 📈 Cost Management

### How to Minimize Charges

1. **Search Once, Cache Results**: Don't repeat searches
2. **Use Specific Filters**: Narrow results to what you need
3. **Search as Guest First**: Browse freely, sign in to book
4. **Monitor Wallet**: Check balance regularly
5. **Daily Limit**: You're only charged once per doctor per day

### Estimated Costs

If doctors set average search_charge = 1000 UZS:

| Action | Cost |
|--------|------|
| Search returns 10 doctors | ~10,000 UZS (first time) |
| Same search again today | 0 UZS (already paid) |
| Search tomorrow | ~10,000 UZS (new day) |
| Search with filters (5 doctors) | ~5,000 UZS |

**Note**: Most doctors have search_charge = 0 (free)

---

## 🎓 Best Practices

1. **Use Filters**: Be specific to reduce costs
2. **Check Wallet**: Monitor balance before searching
3. **Authenticate**: Get higher rate limits and unlimited searches
4. **Cache Results**: Store locally to avoid repeated searches
5. **Paginate**: Process one page at a time
6. **Handle Errors**: Implement retry logic for rate limits

---

## 📋 Complete Parameter Reference

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search` | string | Text search | `?search=heart` |
| `specialty` | string | Doctor specialty | `?specialty=kardiolog` |
| `region` | integer | Region ID | `?region=1` |
| `district` | integer | District ID | `?district=5` |
| `min_price` | integer | Min consultation price | `?min_price=50000` |
| `max_price` | integer | Max consultation price | `?max_price=200000` |
| `min_experience` | integer | Min years of experience | `?min_experience=10` |
| `max_experience` | integer | Max years of experience | `?max_experience=20` |
| `min_rating` | float | Minimum rating | `?min_rating=4.0` |
| `experience_level` | string | junior/mid/senior | `?experience_level=senior` |
| `is_available` | boolean | Only available doctors | `?is_available=true` |
| `is_online_consultation` | boolean | Online consultation | `?is_online_consultation=true` |
| `available_now` | boolean | Available right now | `?available_now=true` |
| `hospital` | integer | Hospital ID | `?hospital=1` |
| `ordering` | string | Sort field(s) | `?ordering=-rating` |
| `page` | integer | Page number | `?page=2` |

---

## 🆘 Troubleshooting

### Issue: "Request was throttled"
**Cause**: Rate limit exceeded (20/min for guests, 60/min for users)
**Solution**: Wait 60 seconds or sign in

### Issue: Few/No results when searching
**Cause**: You may have hit search limits on popular doctors
**Solution**: Sign in to bypass limits

### Issue: "Insufficient wallet balance"
**Cause**: Not enough funds for search charges
**Solution**: Top up wallet at `/api/v1/payments/wallet/topup/`

### Issue: Unexpected charges
**Cause**: Doctors have configured search charges
**Solution**: Check `charges.search_charge` in doctor data before searching

---

## 📚 Related Endpoints

- **Doctor Detail**: `GET /api/v1/doctors/{id}/`
- **Wallet Balance**: `GET /api/v1/payments/wallet/balance/`
- **Top Up Wallet**: `POST /api/v1/payments/wallet/topup/`
- **Search Stats** (Doctors): `GET /api/v1/doctors/search-stats/`
- **Set Search Limit** (Doctors): `PATCH /api/v1/doctors/search-limit/`
- **Set Charges** (Doctors): `PATCH /api/v1/doctors/charges/`

---

## 🎯 Quick Reference

```bash
# Simple search
curl "http://localhost:8000/api/v1/doctors/list/?search=doctor+name"

# With filters
curl "http://localhost:8000/api/v1/doctors/list/?specialty=kardiolog&region=1&min_rating=4.0"

# Authenticated (higher limits, bypass search limits)
curl "http://localhost:8000/api/v1/doctors/list/?specialty=kardiolog" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

**Ready to search!** 🔍

For more details, visit: http://localhost:8000/api/docs/

# How to Search for Doctors - Complete Guide

## 📍 Available Search Endpoints

### 1. **Advanced Search** (Recommended)
```
GET /api/v1/doctors/search/
```
Most flexible with advanced filtering and sorting

### 2. **Simple List**
```
GET /api/v1/doctors/
```
Basic list with ViewSet capabilities

### 3. **Quick Search** (Public API)
```
GET /api/doctors/search/
```
Legacy endpoint for backward compatibility

---

## 🔍 Search Methods

### Method 1: Text Search (General Search)

Search by name, specialty, workplace, bio, or location:

```bash
# Search for "cardiologist"
curl "http://localhost:8000/api/v1/doctors/search/?search=cardiologist"

# Search by doctor name
curl "http://localhost:8000/api/v1/doctors/search/?name=John"

# General text search
curl "http://localhost:8000/api/v1/doctors/search/?search=heart+specialist"
```

**Python Example:**
```python
import requests

# Search for cardiologists
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={'search': 'cardiologist'}
)

doctors = response.json()
for doctor in doctors['results']:
    print(f"{doctor['user']['first_name']} {doctor['user']['last_name']} - {doctor['specialty']}")
```

---

### Method 2: Filter by Specialty

```bash
# Find all cardiologists
curl "http://localhost:8000/api/v1/doctors/search/?specialty=kardiolog"

# Available specialties:
# - terapevt (General Practitioner)
# - stomatolog (Dentist)
# - kardiolog (Cardiologist)
# - urolog (Urologist)
# - ginekolog (Gynecologist)
# - pediatr (Pediatrician)
# - dermatolog (Dermatologist)
# - nevrolog (Neurologist)
# - oftalmolog (Ophthalmologist)
# - lor (ENT)
# - ortoped (Orthopedist)
# - psixiatr (Psychiatrist)
# - endokrinolog (Endocrinologist)
# - gastroenterolog (Gastroenterologist)
# - pulmonolog (Pulmonologist)
```

**Python Example:**
```python
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={'specialty': 'kardiolog'}
)
```

---

### Method 3: Filter by Location

```bash
# By region
curl "http://localhost:8000/api/v1/doctors/search/?region=1"

# By district
curl "http://localhost:8000/api/v1/doctors/search/?district=5"

# By both (district in specific region)
curl "http://localhost:8000/api/v1/doctors/search/?region=1&district=5"
```

**Get list of regions/districts first:**
```bash
# Get all regions
curl "http://localhost:8000/api/v1/doctors/regions/"

# Get districts for a specific region
curl "http://localhost:8000/api/v1/doctors/regions/1/districts/"
```

**Python Example:**
```python
# Get regions
regions = requests.get('http://localhost:8000/api/v1/doctors/regions/').json()
print("Available regions:", regions)

# Search doctors in Tashkent (region_id=1)
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={'region': 1}
)
```

---

### Method 4: Filter by Price Range

```bash
# Doctors with consultation price between 50,000 and 200,000
curl "http://localhost:8000/api/v1/doctors/search/?min_price=50000&max_price=200000"

# Doctors under 100,000
curl "http://localhost:8000/api/v1/doctors/search/?max_price=100000"
```

**Python Example:**
```python
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={
        'min_price': 50000,
        'max_price': 200000
    }
)
```

---

### Method 5: Filter by Experience

```bash
# Doctors with at least 10 years experience
curl "http://localhost:8000/api/v1/doctors/search/?min_experience=10"

# Experience between 5 and 15 years
curl "http://localhost:8000/api/v1/doctors/search/?min_experience=5&max_experience=15"

# By experience level
curl "http://localhost:8000/api/v1/doctors/search/?experience_level=senior"
# Options: junior (0-5 years), mid (6-15 years), senior (16+ years)
```

**Python Example:**
```python
# Find senior doctors (16+ years)
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={'experience_level': 'senior'}
)
```

---

### Method 6: Filter by Rating

```bash
# Doctors with rating 4.0 or higher
curl "http://localhost:8000/api/v1/doctors/search/?min_rating=4.0"

# Highly rated doctors (4.5+)
curl "http://localhost:8000/api/v1/doctors/search/?min_rating=4.5"
```

---

### Method 7: Filter by Availability

```bash
# Only available doctors
curl "http://localhost:8000/api/v1/doctors/search/?is_available=true"

# Only online consultation doctors
curl "http://localhost:8000/api/v1/doctors/search/?is_online_consultation=true"

# Available right now (based on schedule)
curl "http://localhost:8000/api/v1/doctors/search/?available_now=true"

# Doctors with defined schedules
curl "http://localhost:8000/api/v1/doctors/search/?has_schedule=true"
```

---

### Method 8: Filter by Hospital

```bash
# All doctors from a specific hospital
curl "http://localhost:8000/api/v1/doctors/search/?hospital=1"
```

---

### Method 9: Combined Filters (Advanced Search)

You can combine multiple filters:

```bash
# Cardiologists in Tashkent with 10+ years experience, rating 4+, under 200k
curl "http://localhost:8000/api/v1/doctors/search/\
?specialty=kardiolog\
&region=1\
&min_experience=10\
&min_rating=4.0\
&max_price=200000\
&is_available=true\
&is_online_consultation=true"
```

**Python Example:**
```python
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={
        'specialty': 'kardiolog',
        'region': 1,
        'min_experience': 10,
        'min_rating': 4.0,
        'max_price': 200000,
        'is_available': True,
        'is_online_consultation': True
    }
)

doctors = response.json()['results']
print(f"Found {len(doctors)} doctors matching criteria")
```

---

## 📊 Sorting Results

### Available Sort Fields

```bash
# Sort by rating (highest first)
curl "http://localhost:8000/api/v1/doctors/search/?ordering=-rating"

# Sort by price (lowest first)
curl "http://localhost:8000/api/v1/doctors/search/?ordering=consultation_price"

# Sort by experience (most experienced first)
curl "http://localhost:8000/api/v1/doctors/search/?ordering=-experience"

# Sort by total reviews (most reviewed first)
curl "http://localhost:8000/api/v1/doctors/search/?ordering=-total_reviews"

# Multiple sort (rating desc, then price asc)
curl "http://localhost:8000/api/v1/doctors/search/?ordering=-rating,consultation_price"
```

**Available ordering fields:**
- `rating` - Doctor rating
- `total_reviews` - Number of reviews
- `consultation_price` - Price
- `experience` - Years of experience
- `-field` - Add `-` prefix for descending order

**Python Example:**
```python
# Get top-rated doctors
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={'ordering': '-rating,-total_reviews'}
)
```

---

## 📄 Pagination

Results are paginated (20 doctors per page by default):

```bash
# Get first page
curl "http://localhost:8000/api/v1/doctors/search/"

# Get second page
curl "http://localhost:8000/api/v1/doctors/search/?page=2"

# Get third page
curl "http://localhost:8000/api/v1/doctors/search/?page=3"
```

**Response Structure:**
```json
{
  "count": 156,
  "next": "http://localhost:8000/api/v1/doctors/search/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
      },
      "specialty": "kardiolog",
      "experience": 15,
      "rating": 4.8,
      "total_reviews": 245,
      "consultation_price": 150000,
      "is_available": true,
      "is_online_consultation": true,
      "workplace": "City Hospital",
      "bio": "Experienced cardiologist..."
    }
  ]
}
```

**Python Example:**
```python
# Get all doctors (handle pagination)
all_doctors = []
page = 1

while True:
    response = requests.get(
        'http://localhost:8000/api/v1/doctors/search/',
        params={'page': page, 'specialty': 'kardiolog'}
    ).json()

    all_doctors.extend(response['results'])

    if not response['next']:
        break
    page += 1

print(f"Total doctors found: {len(all_doctors)}")
```

---

## 🎯 Real-World Examples

### Example 1: Find Affordable Dentists Nearby

```python
import requests

# Get available dentists in Tashkent under 100k
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={
        'specialty': 'stomatolog',
        'region': 1,  # Tashkent
        'max_price': 100000,
        'is_available': True,
        'ordering': 'consultation_price'  # Cheapest first
    }
)

doctors = response.json()['results']
for doctor in doctors:
    print(f"{doctor['user']['first_name']} {doctor['user']['last_name']}")
    print(f"  Price: {doctor['consultation_price']} UZS")
    print(f"  Rating: {doctor['rating']}/5.0")
    print(f"  Experience: {doctor['experience']} years")
    print()
```

### Example 2: Find Top-Rated Specialists

```python
# Find highly-rated cardiologists with 15+ years experience
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={
        'specialty': 'kardiolog',
        'min_rating': 4.5,
        'min_experience': 15,
        'ordering': '-rating,-total_reviews'
    }
)

doctors = response.json()['results'][:5]  # Top 5
print("Top 5 Cardiologists:")
for i, doctor in enumerate(doctors, 1):
    print(f"{i}. Dr. {doctor['user']['last_name']} - {doctor['rating']}⭐ ({doctor['total_reviews']} reviews)")
```

### Example 3: Find Doctors Available Now

```python
# Find doctors available for immediate consultation
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={
        'available_now': True,
        'is_online_consultation': True,
        'ordering': '-rating'
    }
)

doctors = response.json()['results']
print(f"Found {len(doctors)} doctors available right now!")
```

### Example 4: Search with Full-Text

```python
# Search for "heart specialist in Tashkent"
response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    params={
        'search': 'heart specialist',
        'region': 1,
        'ordering': '-rating'
    }
)
```

---

## 🌐 Using with Frontend (JavaScript)

### Example: React/Vue.js Search Component

```javascript
async function searchDoctors(filters) {
  const params = new URLSearchParams(filters);

  const response = await fetch(
    `http://localhost:8000/api/v1/doctors/search/?${params}`
  );

  const data = await response.json();
  return data.results;
}

// Usage
const doctors = await searchDoctors({
  specialty: 'kardiolog',
  region: 1,
  min_rating: 4.0,
  max_price: 200000,
  ordering: '-rating'
});

console.log(`Found ${doctors.length} doctors`);
doctors.forEach(doctor => {
  console.log(`${doctor.user.first_name} ${doctor.user.last_name} - ${doctor.rating}⭐`);
});
```

---

## 📋 Complete Parameter Reference

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search` | string | General text search | `?search=heart` |
| `name` | string | Search by doctor name | `?name=John` |
| `specialty` | string | Filter by specialty | `?specialty=kardiolog` |
| `region` | integer | Filter by region ID | `?region=1` |
| `district` | integer | Filter by district ID | `?district=5` |
| `min_price` | integer | Minimum price | `?min_price=50000` |
| `max_price` | integer | Maximum price | `?max_price=200000` |
| `min_experience` | integer | Minimum years | `?min_experience=10` |
| `max_experience` | integer | Maximum years | `?max_experience=20` |
| `min_rating` | float | Minimum rating | `?min_rating=4.0` |
| `experience_level` | string | junior/mid/senior | `?experience_level=senior` |
| `is_available` | boolean | Only available | `?is_available=true` |
| `is_online_consultation` | boolean | Online only | `?is_online_consultation=true` |
| `available_now` | boolean | Available right now | `?available_now=true` |
| `has_schedule` | boolean | Has schedule defined | `?has_schedule=true` |
| `hospital` | integer | Filter by hospital ID | `?hospital=1` |
| `ordering` | string | Sort field(s) | `?ordering=-rating` |
| `page` | integer | Page number | `?page=2` |

---

## 🔐 Authentication

Most search endpoints work **without authentication** (AllowAny), but authenticated users get benefits:

```python
# Authenticated request
headers = {
    'Authorization': 'Token YOUR_TOKEN_HERE'
}

response = requests.get(
    'http://localhost:8000/api/v1/doctors/search/',
    headers=headers,
    params={'specialty': 'kardiolog'}
)

# Benefits:
# - Unlimited searches (no daily limit)
# - Access to more doctor details
# - Can save favorites (if implemented)
```

---

## 🚨 Error Handling

```python
response = requests.get('http://localhost:8000/api/v1/doctors/search/')

if response.status_code == 200:
    doctors = response.json()['results']
    print(f"Found {len(doctors)} doctors")
elif response.status_code == 404:
    print("Endpoint not found")
elif response.status_code == 429:
    print("Rate limit exceeded - please wait or sign in")
else:
    print(f"Error: {response.status_code}")
```

---

## 💡 Tips & Best Practices

1. **Start Broad, Then Narrow**: Begin with general search, add filters as needed
2. **Use Pagination**: Don't try to load all results at once
3. **Sort Wisely**: Default sorting is by rating, but you can customize
4. **Cache Results**: If searching repeatedly, cache results client-side
5. **Handle Empty Results**: Always check if results array is empty
6. **Combine Filters**: Multiple filters give more precise results

---

## 🎓 Testing the Search

```bash
# Test 1: Basic search
curl "http://localhost:8000/api/v1/doctors/search/"

# Test 2: Search by specialty
curl "http://localhost:8000/api/v1/doctors/search/?specialty=kardiolog"

# Test 3: Complex query
curl "http://localhost:8000/api/v1/doctors/search/?specialty=kardiolog&min_rating=4.0&region=1&ordering=-rating"
```

---

## 📚 Related Endpoints

- **Get Doctor Detail**: `GET /api/v1/doctors/{id}/`
- **Get Specialties**: `GET /api/v1/doctors/specialties/`
- **Get Regions**: `GET /api/v1/doctors/regions/`
- **Get Districts**: `GET /api/v1/doctors/regions/{id}/districts/`

---

**Happy Searching!** 🔍

For more information, see [API Documentation](http://localhost:8000/api/docs/)

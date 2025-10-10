# Doctor Statistics API Documentation

## Overview
This document describes the doctor statistics API endpoints that provide comprehensive analytics for doctors including views, contact information access, search appearances, consultations, and financial metrics.

## API Endpoints

### 1. Individual Doctor Statistics
**Endpoint:** `GET /api/admin_panel/doctors-statistics/<doctor_id>/`

**Description:** Get comprehensive statistics for a specific doctor.

**Path Parameters:**
- `doctor_id` (required): Doctor ID

**Example Request:**
```
GET /api/admin_panel/doctors-statistics/123/
```

**Example Response:**
```json
{
  "doctor_id": 123,
  "doctor_name": "Dr. John Doe",
  "doctor_phone": "+998901234567",
  "doctor_specialty": "kardiolog",
  "doctor_specialty_display": "Kardiolog",
  "hospital_name": "Central Hospital",

  "total_profile_views": 5420,
  "weekly_views": 234,
  "monthly_views": 1050,

  "total_searches": 1234,
  "total_card_views": 567,
  "total_phone_views": 234,

  "total_consultations": 150,
  "successful_consultations": 142,
  "success_rate": 94.67,

  "rating": 4.8,
  "total_reviews": 89,

  "total_charges": 2035,
  "total_charge_amount": "1234500.00",

  "wallet_balance": "245000.00",
  "is_blocked": false,

  "is_available": true,
  "verification_status": "approved",

  "created_at": "2024-01-15T10:30:00Z",
  "last_activity": "2025-10-10T14:25:00Z"
}
```

**Statistics Breakdown:**

**View Statistics:**
- `total_profile_views`: Total number of times doctor's profile was viewed
- `weekly_views`: Views in the last 7 days
- `monthly_views`: Views in the last 30 days

**Contact Statistics (from ChargeLog):**
- `total_searches`: Number of times doctor appeared in search results (charged)
- `total_card_views`: Number of times doctor's card/profile was viewed (charged)
- `total_phone_views`: Number of times doctor's phone number was revealed (charged)

**Consultation Statistics:**
- `total_consultations`: Total consultations conducted
- `successful_consultations`: Successfully completed consultations
- `success_rate`: Percentage of successful consultations

**Rating Statistics:**
- `rating`: Average rating (0-5)
- `total_reviews`: Total number of reviews received

**Financial Statistics:**
- `total_charges`: Total number of charges applied to this doctor
- `total_charge_amount`: Total amount charged from doctor's wallet

**Wallet Information:**
- `wallet_balance`: Current wallet balance
- `is_blocked`: Whether doctor is blocked due to low balance

---

### 2. All Doctors Statistics List
**Endpoint:** `GET /api/admin_panel/doctors-statistics/`

**Description:** Get statistics for all doctors with filtering, sorting, and pagination.

**Query Parameters:**
- `specialty` (optional): Filter by specialty (terapevt, kardiolog, etc.)
- `hospital_id` (optional): Filter by hospital ID
- `verification_status` (optional): Filter by status (pending, approved, rejected, suspended)
- `is_available` (optional): Filter by availability (true/false)
- `is_blocked` (optional): Filter by blocked status (true/false)
- `search` (optional): Search by doctor name or phone
- `sort_by` (optional): Sort field (profile_views, -profile_views, total_consultations, -total_consultations, rating, -rating, created_at, -created_at)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Example Request:**
```
GET /api/admin_panel/doctors-statistics/?specialty=kardiolog&sort_by=-profile_views&page=1&page_size=10
```

**Example Response:**
```json
{
  "doctors": [
    {
      "doctor_id": 123,
      "doctor_name": "Dr. John Doe",
      "doctor_phone": "+998901234567",
      "doctor_specialty": "kardiolog",
      "doctor_specialty_display": "Kardiolog",
      "hospital_name": "Central Hospital",
      "total_profile_views": 5420,
      "weekly_views": 234,
      "monthly_views": 1050,
      "total_searches": 1234,
      "total_card_views": 567,
      "total_phone_views": 234,
      "total_consultations": 150,
      "successful_consultations": 142,
      "success_rate": 94.67,
      "rating": 4.8,
      "total_reviews": 89,
      "total_charges": 2035,
      "total_charge_amount": "1234500.00",
      "wallet_balance": "245000.00",
      "is_blocked": false,
      "is_available": true,
      "verification_status": "approved",
      "created_at": "2024-01-15T10:30:00Z",
      "last_activity": "2025-10-10T14:25:00Z"
    },
    {
      "doctor_id": 124,
      "doctor_name": "Dr. Jane Smith",
      "doctor_phone": "+998901234568",
      "doctor_specialty": "kardiolog",
      "doctor_specialty_display": "Kardiolog",
      "hospital_name": "City Clinic",
      "total_profile_views": 4856,
      "weekly_views": 198,
      "monthly_views": 890,
      "total_searches": 987,
      "total_card_views": 432,
      "total_phone_views": 189,
      "total_consultations": 128,
      "successful_consultations": 121,
      "success_rate": 94.53,
      "rating": 4.7,
      "total_reviews": 76,
      "total_charges": 1608,
      "total_charge_amount": "987500.00",
      "wallet_balance": "187000.00",
      "is_blocked": false,
      "is_available": true,
      "verification_status": "approved",
      "created_at": "2024-02-20T09:15:00Z",
      "last_activity": "2025-10-10T13:40:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_items": 50,
    "has_next": true,
    "has_previous": false,
    "page_size": 10
  },
  "filters": {
    "specialties": {
      "terapevt": "Terapevt",
      "stomatolog": "Stomatolog",
      "kardiolog": "Kardiolog",
      "urolog": "Urolog",
      "ginekolog": "Ginekolog",
      "pediatr": "Pediatr",
      "dermatolog": "Dermatolog",
      "nevrolog": "Nevrolog",
      "oftalmolog": "Oftalmolog",
      "lor": "LOR (Quloq-Burun-Tomoq)",
      "ortoped": "Ortoped",
      "psixiatr": "Psixiatr",
      "endokrinolog": "Endokrinolog",
      "gastroenterolog": "Gastroenterolog",
      "pulmonolog": "Pulmonolog"
    },
    "verification_statuses": {
      "pending": "Kutilmoqda",
      "approved": "Tasdiqlangan",
      "rejected": "Rad etilgan",
      "suspended": "To'xtatilgan"
    },
    "current_filters": {
      "specialty": "kardiolog",
      "hospital_id": null,
      "verification_status": null,
      "is_available": null,
      "is_blocked": null,
      "search": "",
      "sort_by": "-profile_views"
    }
  }
}
```

**Sorting Options:**
- `profile_views`: Sort by profile views (ascending)
- `-profile_views`: Sort by profile views (descending) - **most popular first**
- `total_consultations`: Sort by consultations (ascending)
- `-total_consultations`: Sort by consultations (descending)
- `rating`: Sort by rating (ascending)
- `-rating`: Sort by rating (descending) - **highest rated first**
- `created_at`: Sort by creation date (ascending)
- `-created_at`: Sort by creation date (descending) - **newest first**

---

### 3. Doctors Statistics Summary
**Endpoint:** `GET /api/admin_panel/doctors-statistics/summary/`

**Description:** Get aggregated summary statistics for all doctors.

**Example Request:**
```
GET /api/admin_panel/doctors-statistics/summary/
```

**Example Response:**
```json
{
  "total_doctors": 250,
  "active_doctors": 234,
  "verified_doctors": 220,
  "blocked_doctors": 16,

  "total_profile_views": 1234567,
  "total_searches": 567890,
  "total_card_views": 234567,
  "total_phone_views": 123456,

  "total_consultations": 45678,
  "average_rating": 4.65,
  "total_reviews": 12345,

  "total_charges": 678901,
  "total_charge_amount": "345678900.00"
}
```

**Summary Statistics:**

**Doctor Counts:**
- `total_doctors`: Total number of doctors in the system
- `active_doctors`: Doctors with `is_available=True`
- `verified_doctors`: Doctors with `verification_status=approved`
- `blocked_doctors`: Doctors with `is_blocked=True` (low wallet balance)

**Engagement Metrics:**
- `total_profile_views`: Sum of all profile views across all doctors
- `total_searches`: Total number of search appearances (charged)
- `total_card_views`: Total number of card views (charged)
- `total_phone_views`: Total number of phone views (charged)

**Performance Metrics:**
- `total_consultations`: Total consultations across all doctors
- `average_rating`: Average rating across all doctors
- `total_reviews`: Total reviews received by all doctors

**Financial Metrics:**
- `total_charges`: Total number of charges applied
- `total_charge_amount`: Total amount charged from all doctors

---

## Authentication

All endpoints require admin authentication:
- User must be authenticated (logged in)
- User must have `is_staff=True`

**Headers:**
```
Authorization: Bearer <token>
```

---

## Use Cases

### 1. Find Most Popular Doctors
```
GET /api/admin_panel/doctors-statistics/?sort_by=-profile_views&page_size=10
```
Returns top 10 doctors by profile views.

### 2. Find Highest Earning Doctors
```
GET /api/admin_panel/doctors-statistics/?sort_by=-total_charge_amount&page_size=10
```
Returns doctors sorted by total charges (requires custom sorting implementation).

### 3. Monitor Blocked Doctors
```
GET /api/admin_panel/doctors-statistics/?is_blocked=true
```
Returns all blocked doctors (low wallet balance).

### 4. Find Best Rated Doctors by Specialty
```
GET /api/admin_panel/doctors-statistics/?specialty=kardiolog&sort_by=-rating
```
Returns cardiologists sorted by rating.

### 5. Search for Specific Doctor
```
GET /api/admin_panel/doctors-statistics/?search=John
```
Searches doctors by name or phone.

### 6. Monitor Doctor Activity
```
GET /api/admin_panel/doctors-statistics/?sort_by=-monthly_views
```
Returns doctors sorted by recent activity (monthly views).

---

## Example Usage

### Python Example
```python
import requests

url = "http://localhost:8000/api/admin_panel/doctors-statistics/"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

# Get top 10 most viewed doctors
params = {
    "sort_by": "-profile_views",
    "page_size": 10,
    "verification_status": "approved"
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

for doctor in data['doctors']:
    print(f"{doctor['doctor_name']}: {doctor['total_profile_views']} views")
    print(f"  - Searches: {doctor['total_searches']}")
    print(f"  - Card Views: {doctor['total_card_views']}")
    print(f"  - Phone Views: {doctor['total_phone_views']}")
    print(f"  - Rating: {doctor['rating']} ({doctor['total_reviews']} reviews)")
    print()
```

### JavaScript Example
```javascript
const url = 'http://localhost:8000/api/admin_panel/doctors-statistics/summary/';
const headers = {
  'Authorization': 'Bearer YOUR_TOKEN'
};

fetch(url, { headers })
  .then(response => response.json())
  .then(data => {
    console.log(`Total Doctors: ${data.total_doctors}`);
    console.log(`Active Doctors: ${data.active_doctors}`);
    console.log(`Total Profile Views: ${data.total_profile_views}`);
    console.log(`Average Rating: ${data.average_rating}`);
  });
```

---

## Data Updates

The statistics are updated in real-time based on:
- **Profile Views**: Updated when `doctor.increment_profile_views()` is called
- **Search/Card/Phone Views**: Updated when charges are logged via `ChargeLog`
- **Consultations**: Updated manually via `doctor.update_consultation_stats()`
- **Ratings**: Updated manually via `doctor.update_rating()`

---

## Notes

- All amounts are in Uzbek Som (UZS)
- Statistics are calculated in real-time from the database
- Pagination is recommended for large datasets
- Weekly and monthly views are reset periodically (requires scheduled task)
- Wallet balance affects doctor blocking status (threshold: 5000 som)

---

## Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found (for specific doctor):**
```json
{
  "detail": "Not found."
}
```

---

## Integration with Transaction API

The doctor statistics API complements the transaction API:
- **Transaction API**: Shows raw transaction/charge data
- **Doctor Statistics API**: Shows aggregated metrics for doctor performance

Use together for comprehensive analytics:
1. Get doctor statistics for overview
2. Use transaction API to drill down into specific charges
3. Use summary endpoint for dashboard metrics

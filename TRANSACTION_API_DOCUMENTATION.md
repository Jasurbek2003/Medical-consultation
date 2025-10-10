# Transaction API Documentation

## Overview
This document describes the new transaction API endpoints in the admin panel that allow administrators to view and manage all transactions from hospitals and doctors.

## API Endpoints

### 1. Wallet Transactions List
**Endpoint:** `GET /api/admin_panel/transactions/wallet/`

**Description:** Get all wallet transactions with filtering and pagination.

**Query Parameters:**
- `user_type` (optional): Filter by user type (doctor, patient, hospital_admin)
- `transaction_type` (optional): Filter by transaction type (credit, debit)
- `status` (optional): Filter by status (pending, completed, failed, cancelled)
- `date_from` (optional): Filter transactions from this date (YYYY-MM-DD)
- `date_to` (optional): Filter transactions up to this date (YYYY-MM-DD)
- `search` (optional): Search by user name, phone, or description
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Number of items per page (default: 20)

**Example Request:**
```
GET /api/admin_panel/transactions/wallet/?user_type=doctor&transaction_type=debit&page=1&page_size=20
```

**Example Response:**
```json
{
  "transactions": [
    {
      "id": "uuid",
      "user_id": 123,
      "user_name": "Dr. John Doe",
      "user_phone": "+998901234567",
      "user_type": "doctor",
      "transaction_type": "debit",
      "transaction_type_display": "Debit (Yechish)",
      "amount": "5000.00",
      "balance_before": "250000.00",
      "balance_after": "245000.00",
      "description": "Shifokor tasdiqlash to'lovi",
      "status": "completed",
      "status_display": "Tugallangan",
      "created_at": "2025-10-10T10:30:00Z",
      "updated_at": "2025-10-10T10:30:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_items": 100,
    "has_next": true,
    "has_previous": false,
    "page_size": 20
  },
  "filters": {
    "transaction_types": {
      "credit": "Kredit (Qo'shish)",
      "debit": "Debit (Yechish)"
    },
    "statuses": {
      "pending": "Kutilmoqda",
      "completed": "Tugallangan",
      "failed": "Muvaffaqiyatsiz",
      "cancelled": "Bekor qilingan"
    },
    "current_filters": {
      "user_type": "doctor",
      "transaction_type": "debit",
      "status": null,
      "date_from": null,
      "date_to": null,
      "search": ""
    }
  }
}
```

---

### 2. Doctor Charges List
**Endpoint:** `GET /api/admin_panel/transactions/doctor-charges/`

**Description:** Get all doctor charges (ChargeLog) with filtering and pagination.

**Query Parameters:**
- `doctor_id` (optional): Filter by doctor ID
- `hospital_id` (optional): Filter by hospital ID
- `charge_type` (optional): Filter by charge type (search, view_card, view_phone, first_register, add_service, add_speciality)
- `date_from` (optional): Filter charges from this date
- `date_to` (optional): Filter charges up to this date
- `search` (optional): Search by doctor name or phone
- `page` (optional): Page number
- `page_size` (optional): Items per page

**Example Request:**
```
GET /api/admin_panel/transactions/doctor-charges/?hospital_id=5&charge_type=search&page=1
```

**Example Response:**
```json
{
  "charges": [
    {
      "id": 456,
      "doctor_id": 789,
      "doctor_name": "Dr. Jane Smith",
      "doctor_phone": "+998901234568",
      "doctor_specialty": "Kardiolog",
      "hospital_id": 5,
      "hospital_name": "Central Hospital",
      "charge_type": "search",
      "charge_type_display": "Qidiruv",
      "amount": "500.00",
      "user": 123,
      "user_name": "Patient Name",
      "user_phone": "+998901234569",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "metadata": {},
      "created_at": "2025-10-10T11:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 3,
    "total_items": 50,
    "has_next": true,
    "has_previous": false,
    "page_size": 20
  },
  "filters": {
    "charge_types": {
      "search": "Qidiruv",
      "view_card": "Kartani ko'rish",
      "view_phone": "Telefon raqamini ko'rish",
      "first_register": "Birinchi ro'yxatdan o'tish",
      "add_service": "Xizmat qo'shish",
      "add_speciality": "Mutaxassislik qo'shish"
    },
    "current_filters": {
      "doctor_id": null,
      "hospital_id": "5",
      "charge_type": "search",
      "date_from": null,
      "date_to": null,
      "search": ""
    }
  }
}
```

---

### 3. Hospital Transactions
**Endpoint:** `GET /api/admin_panel/transactions/hospital/<hospital_id>/`

**Description:** Get all transactions for a specific hospital (all ChargeLog entries for doctors in this hospital).

**Path Parameters:**
- `hospital_id` (required): Hospital ID

**Query Parameters:**
- `charge_type` (optional): Filter by charge type
- `date_from` (optional): Filter from this date
- `date_to` (optional): Filter up to this date
- `search` (optional): Search by doctor name or phone
- `page` (optional): Page number
- `page_size` (optional): Items per page

**Example Request:**
```
GET /api/admin_panel/transactions/hospital/5/?charge_type=view_card&page=1
```

**Example Response:**
```json
{
  "hospital": {
    "id": 5,
    "name": "Central Hospital",
    "address": "123 Main Street, Tashkent"
  },
  "transactions": [
    {
      "id": 789,
      "doctor_id": 456,
      "doctor_name": "Dr. Alice Brown",
      "doctor_phone": "+998901234570",
      "doctor_specialty": "Terapevt",
      "hospital_id": 5,
      "hospital_name": "Central Hospital",
      "charge_type": "view_card",
      "charge_type_display": "Kartani ko'rish",
      "amount": "1000.00",
      "user": 321,
      "user_name": "Patient User",
      "user_phone": "+998901234571",
      "ip_address": "192.168.1.2",
      "created_at": "2025-10-10T12:00:00Z"
    }
  ],
  "statistics": {
    "total_amount": "150000.00",
    "total_transactions": 45
  },
  "pagination": {
    "current_page": 1,
    "total_pages": 3,
    "total_items": 45,
    "has_next": true,
    "has_previous": false,
    "page_size": 20
  },
  "filters": {
    "charge_types": {
      "search": "Qidiruv",
      "view_card": "Kartani ko'rish",
      "view_phone": "Telefon raqamini ko'rish",
      "first_register": "Birinchi ro'yxatdan o'tish",
      "add_service": "Xizmat qo'shish",
      "add_speciality": "Mutaxassislik qo'shish"
    },
    "current_filters": {
      "charge_type": "view_card",
      "date_from": null,
      "date_to": null,
      "search": ""
    }
  }
}
```

---

### 4. Doctor Transactions
**Endpoint:** `GET /api/admin_panel/transactions/doctor/<doctor_id>/`

**Description:** Get all transactions for a specific doctor (ChargeLog entries for this doctor).

**Path Parameters:**
- `doctor_id` (required): Doctor ID

**Query Parameters:**
- `charge_type` (optional): Filter by charge type
- `date_from` (optional): Filter from this date
- `date_to` (optional): Filter up to this date
- `page` (optional): Page number
- `page_size` (optional): Items per page

**Example Request:**
```
GET /api/admin_panel/transactions/doctor/789/?page=1&page_size=20
```

**Example Response:**
```json
{
  "doctor": {
    "id": 789,
    "name": "Dr. Jane Smith",
    "phone": "+998901234568",
    "specialty": "Kardiolog",
    "hospital": "Central Hospital",
    "wallet": {
      "balance": 245000.00,
      "total_spent": 55000.00,
      "total_topped_up": 300000.00,
      "is_blocked": false
    }
  },
  "transactions": [
    {
      "id": 123,
      "doctor_id": 789,
      "doctor_name": "Dr. Jane Smith",
      "doctor_phone": "+998901234568",
      "doctor_specialty": "Kardiolog",
      "hospital_id": 5,
      "hospital_name": "Central Hospital",
      "charge_type": "search",
      "charge_type_display": "Qidiruv",
      "amount": "500.00",
      "user": 456,
      "user_name": "Patient User",
      "user_phone": "+998901234572",
      "created_at": "2025-10-10T13:00:00Z"
    }
  ],
  "statistics": {
    "total_amount": "55000.00",
    "total_transactions": 25
  },
  "pagination": {
    "current_page": 1,
    "total_pages": 2,
    "total_items": 25,
    "has_next": true,
    "has_previous": false,
    "page_size": 20
  },
  "filters": {
    "charge_types": {
      "search": "Qidiruv",
      "view_card": "Kartani ko'rish",
      "view_phone": "Telefon raqamini ko'rish",
      "first_register": "Birinchi ro'yxatdan o'tish",
      "add_service": "Xizmat qo'shish",
      "add_speciality": "Mutaxassislik qo'shish"
    },
    "current_filters": {
      "charge_type": null,
      "date_from": null,
      "date_to": null
    }
  }
}
```

---

### 5. Transaction Statistics
**Endpoint:** `GET /api/admin_panel/transactions/statistics/`

**Description:** Get comprehensive transaction statistics.

**Example Request:**
```
GET /api/admin_panel/transactions/statistics/
```

**Example Response:**
```json
{
  "total_transactions": 500,
  "total_amount": "2500000.00",
  "credit_count": 200,
  "credit_amount": "2000000.00",
  "debit_count": 300,
  "debit_amount": "500000.00",
  "total_doctor_charges": 150,
  "total_charge_amount": "75000.00",
  "transactions_today": 25,
  "transactions_this_week": 120,
  "transactions_this_month": 450
}
```

---

## Authentication

All endpoints require admin authentication. Users must:
1. Be authenticated (logged in)
2. Have `is_staff=True` in their user profile

**Headers:**
```
Authorization: Bearer <token>
```

---

## Data Models

### WalletTransaction
Records all wallet-related transactions (credits and debits).

**Fields:**
- `id`: UUID
- `wallet`: Foreign key to UserWallet
- `transaction_type`: credit or debit
- `amount`: Transaction amount
- `balance_before`: Balance before transaction
- `balance_after`: Balance after transaction
- `description`: Transaction description
- `status`: pending, completed, failed, cancelled
- `created_at`: Timestamp

### ChargeLog
Records all charges applied to doctors.

**Fields:**
- `id`: Integer ID
- `doctor`: Foreign key to Doctor
- `charge_type`: Type of charge (search, view_card, etc.)
- `amount`: Charge amount
- `user`: User who triggered the charge (optional)
- `ip_address`: IP address
- `user_agent`: Browser user agent
- `metadata`: Additional data (JSON)
- `created_at`: Timestamp

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

**404 Not Found (for doctor/hospital specific endpoints):**
```json
{
  "detail": "Not found."
}
```

---

## Example Usage

### Get all transactions for a hospital
```python
import requests

url = "http://localhost:8000/api/admin_panel/transactions/hospital/5/"
headers = {"Authorization": "Bearer YOUR_TOKEN"}
params = {
    "charge_type": "search",
    "date_from": "2025-10-01",
    "date_to": "2025-10-10",
    "page": 1,
    "page_size": 20
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

print(f"Total transactions: {data['statistics']['total_transactions']}")
print(f"Total amount: {data['statistics']['total_amount']}")
```

### Get wallet transactions filtered by doctor user type
```python
url = "http://localhost:8000/api/admin_panel/transactions/wallet/"
headers = {"Authorization": "Bearer YOUR_TOKEN"}
params = {
    "user_type": "doctor",
    "transaction_type": "debit",
    "page": 1
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

for transaction in data['transactions']:
    print(f"{transaction['user_name']}: {transaction['amount']} so'm")
```

---

## Notes

- All amounts are in Uzbek Som (UZS)
- Dates should be in ISO 8601 format (YYYY-MM-DD)
- Pagination is supported on all list endpoints
- All responses include filter options for easy frontend implementation
- Transaction statistics are calculated in real-time

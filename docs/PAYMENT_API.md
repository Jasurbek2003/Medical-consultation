# Payment API Documentation

Complete API documentation for the Medical Consultation Platform payment system.

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Payment Gateways](#payment-gateways)
- [Payments](#payments)
- [Wallet Management](#wallet-management)
- [Billing & Service Charges](#billing--service-charges)
- [Webhooks](#webhooks)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)

---

## Overview

The Payment API provides comprehensive payment processing capabilities including:
- **Payment Gateways**: Click, Payme, UzCard, Humo support
- **Wallet System**: Digital wallet for users with balance management
- **Service Billing**: Pay-per-use billing for medical services
- **Multi-currency**: UZS, USD, EUR, RUB support
- **Secure Processing**: Signature validation, atomic transactions, race condition protection

---

## Authentication

Most endpoints require authentication using Bearer tokens.

```http
Authorization: Bearer <your_token_here>
```

### Public Endpoints (No Auth Required)
- `GET /payments/gateways/`
- `GET /payments/gateways/status/`
- `GET /payments/billing/rules/`
- All webhook endpoints

---

## Base URL

**Development:**
```
http://localhost:8000/api
```

**Production:**
```
https://admin.medikon.uz/api
```

---

## Payment Gateways

### 1. List Payment Gateways

Get all active payment gateways with configuration.

**Endpoint:** `GET /payments/gateways/`

**Auth Required:** No

**Response:**
```json
{
  "success": true,
  "gateways": [
    {
      "name": "click",
      "display_name": "Click",
      "is_active": true,
      "min_amount": 1000.00,
      "max_amount": 10000000.00,
      "commission_type": "percentage",
      "commission_percentage": 2.5,
      "commission_fixed": 0.00,
      "default_currency": "UZS"
    }
  ]
}
```

### 2. Check Gateway Status

Check real-time availability of payment gateways.

**Endpoint:** `GET /payments/gateways/status/`

**Auth Required:** No

**Response:**
```json
{
  "success": true,
  "gateways": [
    {
      "gateway": "Click",
      "name": "click",
      "available": true,
      "message": "Service available",
      "response_time": 0.234
    }
  ],
  "timestamp": "2024-01-15T12:00:00Z"
}
```

---

## Payments

### 1. Create Payment

Create a new payment for wallet top-up.

**Endpoint:** `POST /payments/create/`

**Auth Required:** Yes

**Request Body:**
```json
{
  "gateway": "click",
  "amount": 50000.00,
  "callback_url": "https://example.com/payment/callback"
}
```

**Response:**
```json
{
  "success": true,
  "payment": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": 50000.00,
    "total_amount": 51250.00,
    "commission": 1250.00,
    "status": "pending",
    "gateway": "Click",
    "payment_url": "https://my.click.uz/services/pay?...",
    "expires_at": "2024-01-15T12:30:00Z"
  }
}
```

**Payment Flow:**
1. Create payment → Get `payment_url`
2. Redirect user to `payment_url`
3. User completes payment on gateway site
4. Gateway sends webhook to our server
5. Wallet is credited automatically
6. User is redirected to `callback_url`

### 2. Get Payment Status

Check payment status by ID.

**Endpoint:** `GET /payments/{payment_id}/status/`

**Auth Required:** Yes

**Response:**
```json
{
  "success": true,
  "payment": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "reference_number": "PAY-1234567890-ABCD1234",
    "status": "completed",
    "amount": 50000.00,
    "gateway": "click",
    "created_at": "2024-01-15T12:00:00Z",
    "completed_at": "2024-01-15T12:05:00Z"
  }
}
```

**Payment Statuses:**
- `pending` - Payment created, awaiting user action
- `processing` - Payment being processed by gateway
- `completed` - Payment successful, wallet credited
- `failed` - Payment failed
- `cancelled` - Payment cancelled by user
- `expired` - Payment expired (not completed within time limit)

### 3. Cancel Payment

Cancel a pending payment.

**Endpoint:** `POST /payments/{payment_id}/cancel/`

**Auth Required:** Yes

**Response:**
```json
{
  "success": true,
  "message": "Payment cancelled successfully"
}
```

### 4. Payment History

Get user's payment history.

**Endpoint:** `GET /payments/history/`

**Auth Required:** Yes

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "reference_number": "PAY-1234567890",
    "amount": 50000.00,
    "status": "completed",
    "created_at": "2024-01-15T12:00:00Z"
  }
]
```

### 5. Estimate Payment Cost

Calculate total cost including commission before payment.

**Endpoint:** `POST /payments/estimate/`

**Auth Required:** Yes

**Request Body:**
```json
{
  "gateway": "click",
  "amount": 50000.00
}
```

**Response:**
```json
{
  "success": true,
  "estimate": {
    "amount": 50000.00,
    "commission": 1250.00,
    "total_amount": 51250.00,
    "gateway": "Click",
    "commission_percentage": 2.5,
    "commission_fixed": 0.00
  }
}
```

---

## Wallet Management

### 1. Get Wallet Info

Get comprehensive wallet information.

**Endpoint:** `GET /payments/wallet/`

**Auth Required:** Yes

**Response:**
```json
{
  "success": true,
  "wallet": {
    "balance": 150000.00,
    "total_spent": 45000.00,
    "total_topped_up": 195000.00,
    "is_blocked": false,
    "today_spending": 5000.00,
    "recent_transactions": [
      {
        "id": "trans-uuid",
        "type": "credit",
        "amount": 50000.00,
        "balance_after": 150000.00,
        "description": "Hamyon to'ldirish - Click",
        "status": "completed",
        "created_at": "2024-01-15T12:00:00Z"
      }
    ],
    "billing_settings": {
      "min_topup": 10000.00,
      "max_balance": 1000000.00,
      "free_views_per_day": 3,
      "enable_billing": true
    }
  }
}
```

### 2. Quick Balance Check

Fast endpoint for balance only.

**Endpoint:** `GET /payments/wallet/balance/`

**Auth Required:** Yes

**Response:**
```json
{
  "balance": 150000.00,
  "is_blocked": false
}
```

### 3. Get Wallet Transactions

Get paginated transaction history.

**Endpoint:** `GET /payments/wallet/transactions/`

**Auth Required:** Yes

**Query Parameters:**
- `type` - Filter by type (`credit` or `debit`)
- `status` - Filter by status (default: `completed`)
- `days` - Number of days to look back (default: 30)
- `page` - Page number (default: 1)
- `per_page` - Results per page (default: 20, max: 100)

**Example:**
```
GET /payments/wallet/transactions/?type=debit&days=7&page=1&per_page=20
```

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "id": "uuid",
      "type": "debit",
      "amount": 5000.00,
      "balance_before": 155000.00,
      "balance_after": 150000.00,
      "description": "Shifokor profilini ko'rish",
      "status": "completed",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_count": 45,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false
  }
}
```

### 4. Create Wallet Top-up

Create a payment to add funds to wallet.

**Endpoint:** `POST /payments/wallet/topup/`

**Auth Required:** Yes

**Request Body:**
```json
{
  "amount": 50000.00,
  "gateway": "click",
  "return_url": "https://example.com/wallet"
}
```

**Response:**
```json
{
  "success": true,
  "payment": {
    "id": "uuid",
    "reference_number": "PAY-1234567890",
    "amount": 50000.00,
    "total_amount": 51250.00,
    "commission": 1250.00,
    "status": "pending",
    "gateway": "Click",
    "payment_url": "https://my.click.uz/...",
    "expires_at": "2024-01-15T12:30:00Z"
  }
}
```

---

## Billing & Service Charges

### 1. Get Billing Rules

Get all service prices and billing configuration.

**Endpoint:** `GET /payments/billing/rules/`

**Auth Required:** No

**Response:**
```json
{
  "success": true,
  "billing_rules": [
    {
      "service_type": "doctor_view",
      "service_name": "Shifokor profilini ko'rish",
      "price": 5000.00,
      "discount_percentage": 10.00,
      "min_quantity_for_discount": 5,
      "effective_prices": {
        "1": 5000.00,
        "5": 4500.00,
        "10": 4500.00
      }
    }
  ],
  "settings": {
    "enable_billing": true,
    "maintenance_mode": false,
    "free_views_per_day": 3,
    "free_views_for_new_users": 5,
    "min_wallet_topup": 10000.00,
    "max_wallet_balance": 1000000.00
  }
}
```

**Service Types:**
- `doctor_view` - View doctor profile
- `consultation` - Medical consultation
- `chat_message` - Chat message
- `ai_diagnosis` - AI diagnosis
- `prescription` - Prescription

### 2. Check Service Access

Check if user can access a service without charging.

**Endpoint:** `POST /payments/billing/check-access/`

**Auth Required:** Yes

**Request Body:**
```json
{
  "service_type": "doctor_view",
  "quantity": 1
}
```

**Response:**
```json
{
  "success": true,
  "can_access": true,
  "message": "Sufficient balance",
  "price": 5000.00,
  "unit_price": 5000.00,
  "quantity": 1,
  "service_type": "doctor_view",
  "user_balance": 150000.00
}
```

### 3. Charge for Service

Charge user's wallet for service usage.

**Endpoint:** `POST /payments/billing/charge/`

**Auth Required:** Yes

**Request Body:**
```json
{
  "service_type": "doctor_view",
  "quantity": 1,
  "related_object_id": 123
}
```

**Response (Charged):**
```json
{
  "success": true,
  "charged": true,
  "service_type": "doctor_view",
  "quantity": 1,
  "transaction_id": "uuid",
  "amount_charged": 5000.00,
  "balance_after": 145000.00,
  "description": "Shifokor profilini ko'rish (ID: 123)"
}
```

**Response (Free - within quota):**
```json
{
  "success": true,
  "charged": false,
  "service_type": "doctor_view",
  "quantity": 1,
  "message": "Service accessed without charge (free)"
}
```

**Error Response (Insufficient Balance):**
```json
{
  "success": false,
  "error": "Insufficient balance"
}
```
**Status Code:** 402 Payment Required

### 4. Get Billing Summary

Get user's billing summary for a period.

**Endpoint:** `GET /payments/billing/summary/`

**Auth Required:** Yes

**Query Parameters:**
- `days` - Number of days (default: 30)

**Response:**
```json
{
  "success": true,
  "summary": {
    "period_days": 30,
    "wallet_info": {
      "current_balance": 150000.00,
      "total_credited": 200000.00,
      "total_debited": 50000.00,
      "credit_transactions": 4,
      "debit_transactions": 10,
      "net_change": 150000.00
    },
    "payment_summary": {
      "total_payments": 4,
      "completed_payments": 4,
      "total_amount": 200000.00,
      "pending_payments": 0,
      "failed_payments": 0
    },
    "service_summary": {
      "doctor_views": 8,
      "doctor_view_charges": 40000.00,
      "free_doctor_views": 2
    }
  }
}
```

### 5. Get Daily Usage

Get today's usage statistics.

**Endpoint:** `GET /billing/daily-usage/`

**Auth Required:** Yes

**Response:**
```json
{
  "success": true,
  "daily_usage": {
    "free_views_used": 2,
    "free_views_remaining": 1,
    "paid_views": 3,
    "total_views": 5,
    "spending_today": 15000.00,
    "current_balance": 150000.00
  }
}
```

### 6. Protected Doctor View

View doctor profile with automatic billing.

**Endpoint:** `GET /billing/doctor/{doctor_id}/view/`

**Auth Required:** Yes

**Automatic Behavior:**
1. Checks if billing is enabled
2. Checks if already viewed today (free)
3. Checks free daily quota
4. Charges wallet if needed
5. Returns doctor data

**Response:**
```json
{
  "success": true,
  "doctor": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "specialization": "Cardiologist",
    "rating": 4.8
  },
  "charged": true,
  "amount_charged": 5000.00,
  "new_balance": 145000.00,
  "message": "Successfully charged for Shifokor profilini ko'rish"
}
```

---

## Webhooks

Webhooks are internal endpoints called by payment gateways. **Do not call these manually.**

### Click Webhooks

#### Prepare
**Endpoint:** `POST /payments/click/prepare/`

Called by Click to verify payment is valid before processing.

#### Complete
**Endpoint:** `POST /payments/click/complete/`

Called by Click to finalize payment.

### Payme Webhooks

**Endpoint:** `POST /payments/payme/webhook/`

JSON-RPC 2.0 endpoint supporting methods:
- `CheckPerformTransaction` - Check if payment can be performed
- `CreateTransaction` - Create payment transaction
- `PerformTransaction` - Complete payment
- `CancelTransaction` - Cancel payment
- `CheckTransaction` - Check transaction status

---

## Error Handling

### Standard Error Response

```json
{
  "success": false,
  "error": "Error message here"
}
```

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid token)
- `402` - Payment Required (insufficient balance)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error
- `501` - Not Implemented (gateway not supported)

### Common Errors

**Insufficient Balance:**
```json
{
  "success": false,
  "error": "Insufficient balance",
  "current_balance": 1000.00,
  "required_amount": 5000.00
}
```

**Invalid Gateway:**
```json
{
  "success": false,
  "error": "Payment gateway not found"
}
```

**Payment Not Found:**
```json
{
  "success": false,
  "error": "Payment not found"
}
```

---

## Code Examples

### Python (requests)

#### Create Payment
```python
import requests

url = "http://localhost:8000/api/payments/create/"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "gateway": "click",
    "amount": 50000.00,
    "callback_url": "https://example.com/callback"
}

response = requests.post(url, json=data, headers=headers)
payment = response.json()

if payment['success']:
    print(f"Payment URL: {payment['payment']['payment_url']}")
    print(f"Payment ID: {payment['payment']['id']}")
```

#### Check Balance
```python
url = "http://localhost:8000/api/payments/wallet/balance/"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.get(url, headers=headers)
data = response.json()

print(f"Balance: {data['balance']} UZS")
```

#### Charge for Service
```python
url = "http://localhost:8000/api/payments/billing/charge/"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "service_type": "doctor_view",
    "quantity": 1,
    "related_object_id": 123
}

response = requests.post(url, json=data, headers=headers)
result = response.json()

if result['success']:
    if result['charged']:
        print(f"Charged: {result['amount_charged']} UZS")
        print(f"New balance: {result['balance_after']} UZS")
    else:
        print("Free access granted")
```

### JavaScript (fetch)

#### Create Payment
```javascript
const createPayment = async (amount, gateway) => {
  const response = await fetch('http://localhost:8000/api/payments/create/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${YOUR_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      gateway: gateway,
      amount: amount,
      callback_url: 'https://example.com/callback'
    })
  });

  const data = await response.json();

  if (data.success) {
    // Redirect to payment URL
    window.location.href = data.payment.payment_url;
  }
};

// Usage
createPayment(50000, 'click');
```

#### Check Balance
```javascript
const checkBalance = async () => {
  const response = await fetch('http://localhost:8000/api/payments/wallet/balance/', {
    headers: {
      'Authorization': `Bearer ${YOUR_TOKEN}`
    }
  });

  const data = await response.json();
  console.log(`Balance: ${data.balance} UZS`);
  return data.balance;
};
```

### cURL

#### Create Payment
```bash
curl -X POST http://localhost:8000/api/payments/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gateway": "click",
    "amount": 50000.00,
    "callback_url": "https://example.com/callback"
  }'
```

#### Get Wallet Info
```bash
curl -X GET http://localhost:8000/api/payments/wallet/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Charge for Service
```bash
curl -X POST http://localhost:8000/api/payments/billing/charge/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: "application/json" \
  -d '{
    "service_type": "doctor_view",
    "quantity": 1,
    "related_object_id": 123
  }'
```

---

## Best Practices

### 1. Always Estimate Before Payment
```python
# Check cost first
estimate = requests.post(
    f"{base_url}/payments/estimate/",
    json={"gateway": "click", "amount": 50000},
    headers=headers
).json()

print(f"You will pay: {estimate['estimate']['total_amount']} UZS")
print(f"Commission: {estimate['estimate']['commission']} UZS")
```

### 2. Check Service Access Before Charging
```python
# Check if user can access service
access = requests.post(
    f"{base_url}/payments/billing/check-access/",
    json={"service_type": "doctor_view"},
    headers=headers
).json()

if access['can_access']:
    # Proceed with charging
    charge = requests.post(
        f"{base_url}/payments/billing/charge/",
        json={"service_type": "doctor_view"},
        headers=headers
    ).json()
```

### 3. Handle Payment Callbacks
```python
@app.route('/payment/callback')
def payment_callback():
    payment_id = request.args.get('payment_id')

    # Check payment status
    response = requests.get(
        f"{base_url}/payments/{payment_id}/status/",
        headers=headers
    ).json()

    if response['payment']['status'] == 'completed':
        # Update user interface
        return "Payment successful!"
    else:
        return "Payment pending or failed"
```

### 4. Monitor Wallet Balance
```python
def ensure_sufficient_balance(required_amount):
    balance = requests.get(
        f"{base_url}/payments/wallet/balance/",
        headers=headers
    ).json()['balance']

    if balance < required_amount:
        raise InsufficientBalanceError(
            f"Need {required_amount}, have {balance}"
        )
```

---

## Support

For issues or questions:
- **Email:** jasurbek2030615@gmail.com
- **GitHub:** https://github.com/Jasurbek2003/Medical-consultation/issues

---

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial API documentation
- Click and Payme gateway support
- Wallet management system
- Service billing implementation
- Race condition protection for payments
- CSRF protection for webhooks

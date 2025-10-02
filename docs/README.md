# Medical Consultation Platform - API Documentation

This directory contains comprehensive API documentation for the Medical Consultation Platform payment system.

## 📚 Available Documentation

### 1. **PAYMENT_API.md** - Complete API Guide
📖 **Best for:** Developers who want to understand and integrate the payment APIs

**Includes:**
- Complete endpoint reference with examples
- Authentication guide
- Request/response formats
- Error handling
- Code examples in Python, JavaScript, and cURL
- Best practices and usage patterns

**[→ Read PAYMENT_API.md](./PAYMENT_API.md)**

---

### 2. **payment_api_openapi.yaml** - OpenAPI Specification
🔧 **Best for:** Generating API clients, testing tools, and interactive documentation

**Features:**
- OpenAPI 3.0.3 compliant specification
- Complete schema definitions
- All 49 payment endpoints documented
- Can be imported into Swagger UI, Redoc, or Postman

**Usage:**

```bash
# View in Swagger UI (online)
https://editor.swagger.io/

# Or use Redoc
npx redoc-cli serve payment_api_openapi.yaml

# Or import into Postman
File → Import → payment_api_openapi.yaml
```

**[→ View OpenAPI Spec](./payment_api_openapi.yaml)**

---

### 3. **Payment_API.postman_collection.json** - Postman Collection
🚀 **Best for:** Testing APIs, quick integration, and team collaboration

**Includes:**
- Pre-configured requests for all endpoints
- Environment variables for easy configuration
- Auto-save payment IDs between requests
- Request examples with sample data
- Organized by feature (Payments, Wallet, Billing, etc.)

**How to Use:**

1. **Import Collection:**
   - Open Postman
   - File → Import
   - Select `Payment_API.postman_collection.json`

2. **Set Variables:**
   ```
   base_url: http://localhost:8000/api
   auth_token: <your_jwt_token>
   ```

3. **Start Testing:**
   - Select request
   - Click Send
   - Payment ID auto-saved for subsequent requests

**[→ Download Postman Collection](./Payment_API.postman_collection.json)**

---

## 🚀 Quick Start

### For New Developers

1. **Read the Documentation:**
   Start with [PAYMENT_API.md](./PAYMENT_API.md) to understand the payment system

2. **Import Postman Collection:**
   Use `Payment_API.postman_collection.json` to test endpoints

3. **Generate Client Code:**
   Use `payment_api_openapi.yaml` with OpenAPI Generator:
   ```bash
   openapi-generator-cli generate \
     -i payment_api_openapi.yaml \
     -g python \
     -o ./payment-client
   ```

### For Integration Testing

1. **Import to Postman** - Use the collection for manual testing
2. **Configure Environment:**
   ```json
   {
     "base_url": "http://localhost:8000/api",
     "auth_token": "your_jwt_token_here"
   }
   ```
3. **Run Collection** - Test all endpoints in sequence

### For Frontend Developers

**JavaScript Example:**
```javascript
// Check code examples in PAYMENT_API.md
const response = await fetch('http://localhost:8000/api/payments/create/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    gateway: 'click',
    amount: 50000
  })
});
```

---

## 📋 API Endpoint Summary

### Payment Gateways (2 endpoints)
- `GET /payments/gateways/` - List available gateways
- `GET /payments/gateways/status/` - Check gateway status

### Payments (7 endpoints)
- `POST /payments/create/` - Create payment
- `GET /payments/{id}/status/` - Get payment status
- `POST /payments/{id}/cancel/` - Cancel payment
- `POST /payments/{id}/verify/` - Verify payment
- `GET /payments/history/` - Payment history
- `POST /payments/estimate/` - Estimate cost
- `GET /payments/methods/` - Saved payment methods

### Wallet Management (6 endpoints)
- `GET /payments/wallet/` - Wallet info
- `GET /payments/wallet/balance/` - Quick balance
- `GET /payments/wallet/transactions/` - Transaction history
- `POST /payments/wallet/topup/` - Create top-up
- `GET /payments/wallet/topup/history/` - Top-up history
- `POST /payments/wallet/estimate/` - Estimate top-up cost

### Billing & Services (8 endpoints)
- `GET /payments/billing/rules/` - Get pricing
- `POST /payments/billing/check-access/` - Check access
- `POST /payments/billing/charge/` - Charge for service
- `GET /payments/billing/summary/` - Billing summary
- `GET /billing/daily-usage/` - Daily usage stats
- `POST /billing/doctor/{id}/check-access/` - Check doctor access
- `GET /billing/doctor/{id}/view/` - View doctor (auto-bill)
- `GET /billing/wallet/stats/` - Wallet statistics

### Webhooks (5 endpoints - Internal)
- `POST /payments/click/prepare/` - Click prepare
- `POST /payments/click/complete/` - Click complete
- `POST /payments/payme/webhook/` - Payme JSON-RPC

### Analytics (1 endpoint - Admin only)
- `GET /payments/analytics/` - Payment analytics

**Total:** 49 documented endpoints

---

## 🔒 Security Features

All payment APIs include:
- ✅ **JWT Authentication** - Bearer token required
- ✅ **CSRF Protection** - Public endpoints exempted
- ✅ **Signature Validation** - All webhooks verify signatures
- ✅ **Race Condition Protection** - Database-level locking for payment completion
- ✅ **Atomic Transactions** - All wallet operations are atomic
- ✅ **Input Validation** - All inputs validated and sanitized

---

## 🛠️ Development Tools

### Swagger UI
View interactive API documentation:
```bash
# Install swagger-ui
npm install -g swagger-ui-watcher

# Serve documentation
swagger-ui-watcher payment_api_openapi.yaml
```

### Postman
Import and test all endpoints:
```bash
# Import collection
File → Import → Payment_API.postman_collection.json

# Import OpenAPI spec (alternative)
File → Import → payment_api_openapi.yaml
```

### Code Generation
Generate client libraries:
```bash
# Python client
openapi-generator-cli generate -i payment_api_openapi.yaml -g python

# JavaScript/TypeScript client
openapi-generator-cli generate -i payment_api_openapi.yaml -g typescript-axios

# Java client
openapi-generator-cli generate -i payment_api_openapi.yaml -g java
```

---

## 📞 Support & Resources

- **Documentation Issues:** [GitHub Issues](https://github.com/Jasurbek2003/Medical-consultation/issues)
- **Email Support:** jasurbek2030615@gmail.com
- **Project Repository:** [Medical Consultation Platform](https://github.com/Jasurbek2003/Medical-consultation)

---

## 📝 Version History

### v1.0.0 (2024-01-15)
- ✨ Initial comprehensive documentation
- 📚 49 payment endpoints documented
- 🔧 OpenAPI 3.0.3 specification
- 🚀 Postman collection with examples
- 💡 Code examples in multiple languages
- 🔒 Security features documented

---

## 🎯 Next Steps

1. **Read [PAYMENT_API.md](./PAYMENT_API.md)** for complete understanding
2. **Import Postman collection** for hands-on testing
3. **Review code examples** in your preferred language
4. **Test in development** environment first
5. **Move to production** with proper configuration

Happy coding! 🚀

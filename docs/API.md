# Tibbiy Konsultatsiya REST API Hujjatlari

## 🚀 Asosiy API Endpoints

### Base URL
```
http://localhost:8000/api/
```

## 1. 💬 Chat API

### 1.1 Chat Session Yaratish yoki Xabar Yuborish
```http
POST /api/chat/message/
Content-Type: application/json

{
    "message": "Boshim og'riyapti ikki kundan beri",
    "session_id": "optional-existing-session-id"
}
```

**Response:**
```json
{
    "success": true,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_message": {
        "id": 123,
        "content": "Boshim og'riyapti ikki kundan beri",
        "timestamp": "2025-07-02T10:30:00Z"
    },
    "ai_response": {
        "id": 124,
        "content": "**Sizning muammoingizni tahlil qildim.**\n\n🔍 **Tavsiya etilgan mutaxassis:** Nevrolog\n📊 **Ishonch darajasi:** 85%\n💡 **Sabab:** Bosh og'riq belgilari nevrolog ko'rigini talab qiladi\n\n**🏥 Nevrolog mutaxassislari:**\n\n1. **Dr. Ahmadjon Karimov**\n   - Tajriba: 15 yil\n   - Reyting: 4.8/5 ⭐ (45 sharh)\n   - Narx: 200,000 so'm\n   - Ish joyi: 1-son poliklinika\n   - Telefon: +998901234567",
        "timestamp": "2025-07-02T10:30:05Z",
        "metadata": {
            "classification": {
                "specialty": "nevrolog",
                "confidence": 0.85,
                "explanation": "Bosh og'riq belgilari nevrolog ko'rigini talab qiladi"
            },
            "doctors": [...],
            "response_type": "medical_analysis"
        }
    },
    "message_type": "medical_complaint",
    "ai_available": true
}
```

### 1.2 Faqat Klassifikatsiya (Tez Test)
```http
POST /api/chat/classify/
Content-Type: application/json

{
    "message": "Tishim og'riyapti"
}
```

**Response:**
```json
{
    "success": true,
    "classification": {
        "specialty": "stomatolog",
        "confidence": 0.95,
        "explanation": "Tish og'riq belgilari stomatolog ko'rigini talab qiladi",
        "processing_time": 0.5,
        "urgency_level": "medium"
    },
    "specialty_display": "Stomatolog",
    "ai_available": true
}
```

### 1.3 Chat Tarixini Olish
```http
GET /api/chat/history/{session_id}/
```

**Response:**
```json
{
    "success": true,
    "session": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "active",
        "detected_specialty": "stomatolog",
        "confidence_score": 0.95,
        "total_messages": 4,
        "created_at": "2025-07-02T10:00:00Z"
    },
    "messages": [
        {
            "id": 1,
            "sender_type": "user",
            "message_type": "text",
            "content": "Salom",
            "timestamp": "2025-07-02T10:00:00Z",
            "metadata": {}
        },
        {
            "id": 2,
            "sender_type": "ai",
            "message_type": "text",
            "content": "Salom! Men sizning tibbiy yordamchingizman...",
            "timestamp": "2025-07-02T10:00:02Z",
            "metadata": {"response_type": "greeting"}
        }
    ]
}
```

### 1.4 Fikr-mulohaza Yuborish
```http
POST /api/chat/feedback/
Content-Type: application/json

{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "overall_rating": 5,
    "ai_accuracy_rating": 4,
    "response_time_rating": 5,
    "would_recommend": true,
    "positive_feedback": "Juda foydali bo'ldi",
    "found_doctor": true,
    "contacted_doctor": true
}
```

## 2. 👨‍⚕️ Shifokorlar API

### 2.1 Barcha Shifokorlar Ro'yxati
```http
GET /api/doctors/
```

**Query Parameters:**
- `specialty` - Mutaxassislik (terapevt, stomatolog, ...)
- `region` - Viloyat
- `district` - Tuman
- `is_online_consultation` - Online konsultatsiya (true/false)
- `search` - Qidiruv (ism, ish joyi)
- `ordering` - Tartiblash (rating, -rating, consultation_price, -consultation_price)
- `page` - Sahifa raqami
- `page_size` - Sahifadagi elementlar soni

**Misol:**
```http
GET /api/doctors/?specialty=stomatolog&region=Toshkent&ordering=-rating&page=1&page_size=10
```

**Response:**
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/doctors/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "full_name": "Karimov Ahmadjon Bahtiyor o'g'li",
            "short_name": "Dr. Ahmadjon Karimov",
            "first_name": "Ahmadjon",
            "last_name": "Karimov",
            "specialty": "stomatolog",
            "specialty_display": "Stomatolog",
            "experience": 8,
            "degree": "birinchi",
            "rating": 4.8,
            "total_reviews": 42,
            "consultation_price": 200000.00,
            "workplace": "Smile Stomatologiya",
            "region": "Toshkent",
            "district": "Yashnobod",
            "phone": "+998902345678",
            "email": "ahmadjon@example.com",
            "is_available": true,
            "is_online_consultation": true,
            "photo": "/media/doctors/photos/ahmadjon.jpg",
            "work_start_time": "09:00:00",
            "work_end_time": "19:00:00",
            "languages": "uz",
            "age": 33
        }
    ]
}
```

### 2.2 Shifokor Detallari
```http
GET /api/doctors/{id}/
```

**Response:**
```json
{
    "id": 1,
    "full_name": "Karimov Ahmadjon Bahtiyor o'g'li",
    "short_name": "Dr. Ahmadjon Karimov",
    "first_name": "Ahmadjon",
    "last_name": "Karimov",
    "middle_name": "Bahtiyor o'g'li",
    "specialty": "stomatolog",
    "specialty_display": "Stomatolog",
    "experience": 8,
    "degree": "birinchi",
    "rating": 4.8,
    "total_reviews": 42,
    "consultation_price": 200000.00,
    "workplace": "Smile Stomatologiya",
    "region": "Toshkent",
    "district": "Yashnobod",
    "phone": "+998902345678",
    "email": "ahmadjon@example.com",
    "is_available": true,
    "is_online_consultation": true,
    "photo": "/media/doctors/photos/ahmadjon.jpg",
    "work_start_time": "09:00:00",
    "work_end_time": "19:00:00",
    "languages": "uz",
    "age": 33,
    "bio": "Zamonaviy stomatologiya usullarini qo'llovchi mutaxassis",
    "education": "ToshTibUniversiteti, 2015",
    "achievements": "Ko'plab sertifikatlar",
    "address": "Yashnobod tumani, 3-mavze",
    "workplace_address": "Amir Temur kochasi 25",
    "work_days": "1,2,3,4,5,6",
    "schedules": [
        {
            "id": 1,
            "weekday": 1,
            "weekday_display": "Dushanba",
            "start_time": "09:00:00",
            "end_time": "19:00:00",
            "is_available": true
        }
    ],
    "specializations": [
        {
            "id": 1,
            "name": "Estetik stomatologiya",
            "description": "Tish go'zallashish",
            "certificate": "/media/doctors/certificates/cert1.pdf"
        }
    ],
    "recent_reviews": [
        {
            "id": 1,
            "patient_name": "Anvar S.",
            "overall_rating": 5,
            "title": "A'lo xizmat",
            "comment": "Juda yaxshi shifokor, tavsiya qilaman...",
            "created_at": "02.07.2025"
        }
    ]
}
```

### 2.3 Mutaxassislik bo'yicha Shifokorlar
```http
GET /api/doctors/by_specialty/?specialty=stomatolog
```

### 2.4 Joylashuv bo'yicha Qidirish
```http
GET /api/doctors/search_by_location/?region=Toshkent&district=Yashnobod
```

### 2.5 Eng Yuqori Reytingli Shifokorlar
```http
GET /api/doctors/top_rated/?limit=5
```

### 2.6 Hozir Mavjud Shifokorlar
```http
GET /api/doctors/available_now/
```

### 2.7 Shifokor Ish Jadvali
```http
GET /api/doctors/{id}/schedule/
```

### 2.8 Shifokor Sharhlari
```http
GET /api/doctors/{id}/reviews/?page=1&per_page=10
```

## 3. 📋 Mutaxassisliklar API

### 3.1 Barcha Mutaxassisliklar
```http
GET /api/doctors/ajax/specialties/
```

**Response:**
```json
{
    "success": true,
    "specialties": [
        {
            "code": "terapevt",
            "name": "Terapevt",
            "count": 15
        },
        {
            "code": "stomatolog",
            "name": "Stomatolog", 
            "count": 12
        },
        {
            "code": "kardiolog",
            "name": "Kardiolog",
            "count": 8
        }
    ]
}
```

## 4. 🔍 Qidiruv API

### 4.1 Shifokor Qidirish (AJAX)
```http
GET /api/doctors/ajax/search/?specialty=stomatolog&region=Toshkent&max_price=300000&search=Ahmadjon
```

**Response:**
```json
{
    "success": true,
    "count": 3,
    "doctors": [
        {
            "id": 1,
            "name": "Dr. Ahmadjon Karimov",
            "specialty": "Stomatolog",
            "experience": 8,
            "rating": 4.8,
            "price": 200000.0,
            "workplace": "Smile Stomatologiya",
            "region": "Toshkent",
            "phone": "+998902345678",
            "is_online": true,
            "photo_url": "/media/doctors/photos/ahmadjon.jpg",
            "detail_url": "/doctors/1/"
        }
    ]
}
```

### 4.2 Mutaxassislik bo'yicha Shifokorlar (AJAX)
```http
GET /api/doctors/ajax/by-specialty/?specialty=stomatolog
```

## 5. 📊 Statistika API

### 5.1 Chat Statistikasi
```http
GET /api/chat/stats/
```

**Response:**
```json
{
    "total_sessions": 1250,
    "active_sessions": 45,
    "total_messages": 5680,
    "average_session_duration": 8.5,
    "most_requested_specialty": "terapevt",
    "ai_accuracy_rating": 4.2
}
```

## 6. ⚙️ Xatoliklar

### Xatolik Formati
```json
{
    "success": false,
    "error": "Xatolik tavsifi",
    "error_code": "VALIDATION_ERROR",
    "details": {
        "field": "Bu maydon talab qilinadi"
    }
}
```

### HTTP Status Kodlari
- `200` - Muvaffaqiyatli
- `201` - Yaratildi
- `400` - Noto'g'ri so'rov
- `404` - Topilmadi
- `500` - Server xatoligi

## 7. 🔐 Autentifikatsiya

Hozircha autentifikatsiya talab qilinmaydi. Barcha API'lar ochiq.

Kelajakda JWT autentifikatsiya qo'shilishi mumkin:
```http
Authorization: Bearer <token>
```

## 8. 📱 Frontend Uchun Misol Kodlar

### JavaScript fetch misoli:
```javascript
// Chat xabar yuborish
async function sendChatMessage(message, sessionId = null) {
    const response = await fetch('/api/chat/message/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            session_id: sessionId
        })
    });
    
    return await response.json();
}

// Shifokorlarni olish
async function getDoctors(specialty = null, region = null) {
    let url = '/api/doctors/';
    const params = new URLSearchParams();
    
    if (specialty) params.append('specialty', specialty);
    if (region) params.append('region', region);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    const response = await fetch(url);
    return await response.json();
}

// Mutaxassisliklarni olish
async function getSpecialties() {
    const response = await fetch('/api/doctors/ajax/specialties/');
    return await response.json();
}
```

### React Hook misoli:
```javascript
import { useState, useEffect } from 'react';

export function useDoctors(specialty, region) {
    const [doctors, setDoctors] = useState([]);
    const [loading, setLoading] = useState(false);
    
    useEffect(() => {
        async function fetchDoctors() {
            setLoading(true);
            try {
                const response = await getDoctors(specialty, region);
                setDoctors(response.results || []);
            } catch (error) {
                console.error('Error fetching doctors:', error);
            } finally {
                setLoading(false);
            }
        }
        
        fetchDoctors();
    }, [specialty, region]);
    
    return { doctors, loading };
}
```

## 9. 🚀 Deployment

### Development
```bash
python manage.py runserver
```

### Production
CORS sozlamalari `settings.py` da:
```python
CORS_ALLOWED_ORIGINS = [
    "https://yourfrontend.com",
    "https://mobile.yourapp.com"
]
```

## 10. 📚 Qo'shimcha Ma'lumotlar

- Barcha vaqtlar UTC formatida
- Narxlar so'm da qaytariladi
- Rasm URL'lari to'liq URL bo'lishi uchun `MEDIA_URL` ni frontend da qo'shish kerak
- Pagination standart Django REST framework formatida
- Barcha matnlar o'zbek tilida

Bu API'lar orqali frontend (React, Vue, Flutter, mobile apps) qurishingiz mumkin!
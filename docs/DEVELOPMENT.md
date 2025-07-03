# Tibbiy Konsultatsiya - Development Guide

## 🛠️ Development Environment Setup

### Prerequisites

- Python 3.13+
- UV package manager
- Node.js 18+ (frontend uchun)
- PostgreSQL 15+ (production uchun)
- Redis 7+ (WebSocket uchun)
- Git

### 1. UV O'rnatish

```bash
# UV o'rnatish
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows uchun
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Loyihani Clone Qilish va Sozlash

```bash
git clone <repository-url>
cd Medical_consultation

# Python 3.13 bilan loyiha sozlash
uv init --python 3.13
uv sync
```

### 3. Dependencies O'rnatish

```bash
# Barcha dependencies (production + dev)
uv sync --all-extras

# Faqat production dependencies
uv sync

# Development dependencies qo'shish
uv sync --extra dev

# Yangi package qo'shish
uv add django
uv add --dev pytest

# Requirements.txt dan o'rnatish (agar kerak bo'lsa)
uv pip install -r requirements.txt
```

### 4. Environment Configuration

`.env` fayl yarating:

```env
# Django Settings
SECRET_KEY=your-super-secret-development-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database (Development)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Database (Production alternative)
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=medical_consultation_db
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432

# AI Services
GOOGLE_API_KEY=your-gemini-api-key-here

# Redis (WebSocket support)
REDIS_URL=redis://localhost:6379/0

# Email (Development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Media and Static
MEDIA_ROOT=media/
STATIC_ROOT=staticfiles/

# Security (Development)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Logging
LOG_LEVEL=DEBUG
```

### 5. Database Setup

```bash
# Migrations yaratish
python manage.py makemigrations

# Database yaratish
python manage.py migrate

# Superuser yaratish
python manage.py createsuperuser

# Test data yuklash
python manage.py create_test_data
```

### 6. Development Server

```bash
# Django server
python manage.py runserver

# Redis server (alohida terminalda)
redis-server

# Celery (agar kerak bo'lsa)
celery -A Medical_consultation worker -l info
```

## 📁 Project Structure

```
Medical_consultation/
├── apps/
│   ├── ai_assistant/       # AI xizmatlari
│   │   ├── services.py     # Gemini AI service
│   │   ├── prompts.py      # AI promptlari
│   │   └── utils.py        # AI utility functions
│   ├── chat/              # Chat tizimi
│   │   ├── models.py       # Chat modellari
│   │   ├── views.py        # Chat views
│   │   ├── consumers.py    # WebSocket consumers
│   │   ├── api_views.py    # REST API views
│   │   └── serializers.py  # DRF serializers
│   ├── doctors/           # Shifokorlar
│   │   ├── models.py       # Doctor modeli
│   │   ├── admin.py        # Admin konfiguratsiya
│   │   ├── views.py        # Web views
│   │   ├── api_views.py    # API views
│   │   └── serializers.py  # Serializers
│   ├── users/             # Foydalanuvchilar
│   │   ├── models.py       # Custom User modeli
│   │   ├── admin.py        # User admin
│   │   └── api_views.py    # User API
│   ├── consultations/     # Konsultatsiyalar
│   │   ├── models.py       # Consultation modellari
│   │   ├── admin.py        # Admin panel
│   │   └── api_views.py    # API endpoints
│   └── api/               # Umumiy API
│       └── views.py        # Quick API endpoints
├── config/                # Konfiguratsiya
│   ├── database.py        # Database sozlamalari
│   ├── gemini_config.py   # AI konfiguratsiya
│   └── logging.py         # Logging sozlamalari
├── templates/             # HTML templates
│   ├── base.html          # Base template
│   ├── chat/              # Chat templates
│   ├── doctors/           # Doctor templates
│   └── api_docs.html      # API documentation
├── static/                # Static files
│   ├── css/               # CSS files
│   ├── js/                # JavaScript files
│   └── images/            # Images
├── media/                 # User uploads
├── logs/                  # Log files
├── tests/                 # Test files
├── utils/                 # Utility functions
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
├── requirements-dev.txt   # Development dependencies
├── manage.py             # Django management
└── Medical_consultation/ # Django project
    ├── settings.py       # Django settings
    ├── urls.py           # URL configuration
    ├── wsgi.py           # WSGI configuration
    └── asgi.py           # ASGI configuration
```

## 🧪 Testing

### Test Files

```bash
# Barcha testlar (parallel execution)
uv run pytest

# Muayyan app testi
uv run pytest apps/chat/tests/
uv run pytest apps/doctors/tests/

# Coverage bilan
uv run pytest --cov=apps --cov-report=html
uv run pytest --cov=apps --cov-report=term-missing

# Parallel testing (tezroq)
uv run pytest -n auto

# Specific test
uv run pytest apps/chat/tests/test_views.py::TestChatView::test_send_message
```

### Test Categories

- **Unit Tests**: `tests/test_*.py`
- **Integration Tests**: `tests/integration/`
- **API Tests**: `tests/api/`
- **Frontend Tests**: `tests/frontend/`

### Test Ma'lumotlari

```python
# Test fixtures
python manage.py loaddata fixtures/test_doctors.json
python manage.py loaddata fixtures/test_users.json
```

## 🔧 Development Tools

### Code Quality

```bash
# Ruff (flake8 + black replacement) - JUDA TEZKOR!
uv run ruff check apps/          # Linting
uv run ruff format apps/         # Code formatting
uv run ruff check --fix apps/    # Auto-fix

# Type checking
uv run mypy apps/ --ignore-missing-imports

# Pre-commit hooks o'rnatish
uv run pre-commit install
uv run pre-commit run --all-files
```

### Database Tools

```bash
# Migration status
python manage.py showmigrations

# SQL ko'rish
python manage.py sqlmigrate app_name migration_name

# Database reset
python manage.py flush
python manage.py migrate
```

### Debug Tools

```bash
# Django shell
python manage.py shell

# Django shell_plus (agar django-extensions o'rnatilgan bo'lsa)
python manage.py shell_plus

# Database shell
python manage.py dbshell
```

## 🔄 Development Workflow

### 1. Feature Development

```bash
# Yangi branch yaratish
git checkout -b feature/new-feature-name

# O'zgarishlar
git add .
git commit -m "feat: yangi feature qo'shildi"

# Push qilish
git push origin feature/new-feature-name
```

### 2. Migration Workflow

```bash
# Model o'zgarishlaridan so'ng
python manage.py makemigrations
python manage.py migrate

# Agar conflict bo'lsa
python manage.py migrate --merge
```

### 3. Static Files

```bash
# Development
python manage.py collectstatic --noinput

# Watch mode (agar npm ishlatilsa)
npm run watch
```

## 📊 Monitoring va Debugging

### Logging

Log fayllar `logs/` papkasida:
- `django.log` - Umumiy Django loglari
- `ai_assistant.log` - AI xizmati loglari
- `error.log` - Xatolik loglari

### Performance

```python
# Django Debug Toolbar (development)
pip install django-debug-toolbar

# Settings.py ga qo'shish
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### Memory Profiling

```bash
# Memory profiling
pip install memory-profiler
python -m memory_profiler manage.py runserver
```

## 🔐 Security (Development)

### Environment Variables

```bash
# .env faylni git'ga qo'shmaslik
echo ".env" >> .gitignore
```

### API Keys

```python
# AI API kalitlarini xavfsiz saqlash
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')

# Xatolik handling
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY sozlanmagan - AI fallback ishlatiladi")
```

## 📱 Frontend Development

### Template Development

```html
<!-- Base template extension -->
{% extends 'base.html' %}
{% load static %}

{% block content %}
<!-- Content here -->
{% endblock %}
```

### JavaScript

```javascript
// API so'rovlari
async function sendChatMessage(message) {
    const response = await fetch('/api/chat/send-message/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({message})
    });
    return await response.json();
}
```

### CSS

```css
/* Responsive design */
@media (max-width: 768px) {
    .chat-container {
        margin: 0;
        height: 100vh;
    }
}
```

## 🚀 API Development

### DRF ViewSets

```python
class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.filter(is_available=True)
    serializer_class = DoctorSerializer
    
    @action(detail=False, methods=['get'])
    def by_specialty(self, request):
        # Custom endpoint
        pass
```

### Serializers

```python
class DoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ['id', 'full_name', 'specialty', ...]
```

## 🔧 Troubleshooting

### Keng Uchraydigan Muammolar

1. **AI ishlamaydi**
   ```bash
   # API kalitni tekshiring
   echo $GOOGLE_API_KEY
   
   # Logs'ni ko'ring
   tail -f logs/django.log
   ```

2. **Migration xatoligi**
   ```bash
   # Migration holatini ko'ring
   python manage.py showmigrations
   
   # Fake migration (ehtiyotkorlik bilan)
   python manage.py migrate --fake app_name migration_name
   ```

3. **Static files yuklanalmaadi**
   ```bash
   python manage.py collectstatic --clear
   python manage.py collectstatic
   ```

4. **Port band**
   ```bash
   # Port ishlatilayotganini topish
   lsof -i :8000
   
   # Process o'ldirish
   kill -9 <PID>
   ```

## 📚 Useful Commands

```bash
# Django commands
python manage.py runserver 0.0.0.0:8000
python manage.py shell
python manage.py createsuperuser
python manage.py collectstatic
python manage.py makemigrations
python manage.py migrate

# Custom management commands
python manage.py create_test_data
python manage.py cleanup_old_sessions

# Database
python manage.py dumpdata > backup.json
python manage.py loaddata backup.json

# Debugging
python manage.py check
python manage.py check --deploy
```

## 🎯 Next Steps

1. **Frontend Framework** - React/Vue.js integratsiyasi
2. **Real-time Features** - WebSocket yaxshilash
3. **Payment Integration** - To'lov tizimi
4. **Mobile App** - React Native/Flutter
5. **AI Enhancement** - Ko'proq AI funksiyalar
6. **Analytics** - Foydalanuvchi tahlili

Bu development guide orqali loyihani rivojlantirish va debug qilish osonlashadi!
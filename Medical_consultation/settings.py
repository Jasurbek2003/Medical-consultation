import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

CSRF_TRUSTED_ORIGINS = [
    "https://inaf.avlo.app",
    "http://localhost:5173",
    "https://call.avlo.ai",
    "https://med.quloqai.uz",
    "https://admin.medikon.uz",
    "https://medikon.uz",
    "https://med-admin.quloqai.uz",
]
# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',
    'django_filters',
    'drf_spectacular',  # OpenAPI/Swagger documentation
]

LOCAL_APPS = [
    'apps.core',  # Core utilities and common functionality
    'apps.users',
    'apps.doctors',
    'apps.chat',
    'apps.consultations',
    'apps.translate',
    'apps.hospitals',
    'apps.admin_panel',
    'apps.billing',
    'apps.payments',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files uchun
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',  # Internationalization uchun
]

ROOT_URLCONF = 'Medical_consultation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',  # Internationalization
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'Medical_consultation.wsgi.application'
ASGI_APPLICATION = 'Medical_consultation.asgi.application'  # WebSocket uchun

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PostgreSQL uchun (Production da ishlatish uchun)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME', default='medical_consultation'),
#         'USER': config('DB_USER', default='postgres'),
#         'PASSWORD': config('DB_PASSWORD', default=''),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432'),
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'uz'  # O'zbek tili
TIME_ZONE = 'Asia/Tashkent'  # Toshkent vaqti
USE_I18N = True
USE_L10N = True
USE_TZ = True

# O'zbek va Ingliz tillarini qo'llash
LANGUAGES = [
    ('uz', "O'zbek"),
    ('ru', 'Русский'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Production uchun
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model (ixtiyoriy)
AUTH_USER_MODEL = 'users.User'

# REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Barcha foydalanuvchilar uchun
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',  # Ochiq API uchun
        'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.IsAdminUser',  # Admin uchun
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    # Throttling (Rate Limiting) Configuration
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.core.throttling.BurstRateThrottle',
        'apps.core.throttling.SustainedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # User throttles (authenticated)
        'burst': '60/min',  # 60 requests per minute for burst
        'sustained': '1000/hour',  # 1000 requests per hour sustained

        # Anonymous throttles (unauthenticated)
        'anon_burst': '20/min',  # 20 requests per minute for anonymous
        'anon_sustained': '100/hour',  # 100 requests per hour for anonymous

        # Specific endpoint throttles
        'chat': '30/min',  # Chat messages
        'auth': '5/min',  # Login/register attempts (prevents brute force)
        'payment': '10/min',  # Payment operations
        'search': '60/min',  # Search queries
        'upload': '20/hour',  # File uploads
        'webhook': '200/min',  # Payment webhooks (high rate for providers)
    },
    # Schema generation for API documentation
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# CORS Settings (Frontend bilan ishlash uchun)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
    "https://call.avlo.ai",
    "http://localhost:8000",
    "http://localhost:5173",  # Vite development server
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",  # Vite development server
    "http://192.168.0.29:5173",
    "https://inaf.avlo.app",
    "https://med-admin.quloqai.uz",
    "https://admin.medikon.uz",
    "https://medikon.uz",
]

CORS_ALLOW_CREDENTIALS = True

# Channels (WebSocket) Settings
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Redis bor bo'lmasa, In-memory channel layer ishlatish
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer'
#     }
# }

# Google Gemini AI Settings
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.ai_assistant': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Email Settings (ixtiyoriy)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Development uchun


# Security Settings (Production uchun)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Session Settings
SESSION_COOKIE_AGE = 86400  # 24 soat
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Admin Settings
ADMIN_URL = 'admin/'  # Admin panel URL'ini o'zgartirish mumkin

# Admin site customization
ADMIN_SITE_HEADER = "🏥 Tibbiy Konsultatsiya Admin"
ADMIN_SITE_TITLE = "Tibbiy Admin"
ADMIN_INDEX_TITLE = "Boshqaruv Paneli"

# drf-spectacular (OpenAPI/Swagger) Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Medical Consultation Platform API',
    'DESCRIPTION': """
    # Medical Consultation Platform API Documentation

    AI-powered medical consultation platform built with Django REST Framework.
    This platform connects patients with doctors through secure chat and video consultations,
    featuring real-time translation and AI-assisted medical guidance.

    ## Features
    - **Multi-language Support**: Uzbek, Russian, English
    - **Real-time Chat**: WebSocket-based messaging with translation
    - **AI Medical Assistant**: Google Gemini integration for medical guidance
    - **Doctor-Patient Matching**: Location-based doctor finding
    - **Secure Authentication**: Token-based API authentication
    - **Payment Integration**: Billing and payment processing

    ## Authentication
    All authenticated endpoints require a token in the Authorization header:
    ```
    Authorization: Token <your-token>
    ```

    Obtain a token by calling the `/api/v1/users/auth/login/` endpoint.

    ## Rate Limiting
    - **Authenticated users**: 60 requests/min (burst), 1000 requests/hour (sustained)
    - **Anonymous users**: 20 requests/min (burst), 100 requests/hour (sustained)
    - **Authentication endpoints**: 5 requests/min (prevents brute force)
    - **Chat endpoints**: 30 messages/min
    - **Search endpoints**: 60 requests/min
    - **File uploads**: 20 uploads/hour
    - **Payment endpoints**: 10 requests/min

    ## Support
    - **Repository**: https://github.com/Jasurbek2003/Medical-consultation
    - **Email**: jasurbek2030615@gmail.com
    """,
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and registration'},
        {'name': 'Users', 'description': 'User profile management'},
        {'name': 'Doctors', 'description': 'Doctor profiles and services'},
        {'name': 'Hospitals', 'description': 'Hospital information and services'},
        {'name': 'Consultations', 'description': 'Medical consultations management'},
        {'name': 'Chat', 'description': 'Real-time chat and AI assistance'},
        {'name': 'Payments', 'description': 'Payment processing and billing'},
        {'name': 'Translate', 'description': 'Multi-language translation'},
        {'name': 'Search', 'description': 'Search doctors and services'},
        {'name': 'System', 'description': 'System health and monitoring'},
    ],
    'CONTACT': {
        'name': 'Medical Consultation Support',
        'email': 'jasurbek2030615@gmail.com',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    'EXTERNAL_DOCS': {
        'description': 'GitHub Repository',
        'url': 'https://github.com/Jasurbek2003/Medical-consultation',
    },
    # Security schemes
    'SECURITY': [
        {
            'tokenAuth': [],
        }
    ],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'tokenAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Token-based authentication. Format: `Token <your-token>`'
            }
        }
    },
    'ENUM_NAME_OVERRIDES': {
        'ValidationErrorEnum': 'drf_spectacular.utils.validation_error_name',
    },
    'POSTPROCESSING_HOOKS': [],
    'PREPROCESSING_HOOKS': [],
    # Disable warnings for cleaner output
    'DISABLE_ERRORS_AND_WARNINGS': False,
    # Simplify schema generation by excluding problematic patterns
    'SCHEMA_PATH_PREFIX': r'/api/v1/',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    # Skip views that can't be properly introspected
    'SPECTACULAR_DEFAULTS': {
        'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    },
}

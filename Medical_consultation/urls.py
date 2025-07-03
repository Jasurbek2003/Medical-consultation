from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # =============================================
    # API ENDPOINTS (JSON responses only)
    # =============================================

    # Chat API - asosiy AI xizmatlari
    path('api/chat/', include('apps.chat.api_urls')),

    # Shifokorlar API
    path('api/doctors/', include('apps.doctors.api_urls')),

    # Foydalanuvchilar API
    path('api/users/', include('apps.users.api_urls')),

    # Konsultatsiyalar API
    path('api/consultations/', include('apps.consultations.api_urls')),

    # Tez API endpoint'lar
    path('api/', include('apps.api.urls')),

    # =============================================
    # WEB PAGES (Template responses only)
    # =============================================

    # Bosh sahifa
    path('', TemplateView.as_view(template_name='base.html'), name='home'),

    # Chat sahifalar
    path('chat/', include('apps.chat.web_urls')),

    # Shifokorlar sahifalar
    path('doctors/', include('apps.doctors.web_urls')),

    # Foydalanuvchilar sahifalar
    path('users/', include('apps.users.web_urls')),

    # API hujjatlari
    path('docs/', TemplateView.as_view(template_name='api_docs.html'), name='api_docs'),
]

# Development da media va static fayllarni serve qilish
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin panel sozlamalari
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE
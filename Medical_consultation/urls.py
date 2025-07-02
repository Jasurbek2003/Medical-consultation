from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/users/', include('apps.users.urls')),
    path('api/doctors/', include('apps.doctors.urls')),
    path('api/chat/', include('apps.chat.urls')),  # Bu yerda xatolik bor edi
    path('api/consultations/', include('apps.consultations.urls')),

    # Web pages
    path('', TemplateView.as_view(template_name='base.html'), name='home'),
    path('chat/', include('apps.chat.urls')),  # namespace olib tashlash
    path('doctors/', include('apps.doctors.urls')),  # namespace olib tashlash

    # API documentation
    path('api/', TemplateView.as_view(template_name='api_docs.html'), name='api_docs'),
]

# Development da media va static fayllarni serve qilish
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin panel title'ini o'zgartirish
admin.site.site_header = "Tibbiy Konsultatsiya Admin"
admin.site.site_title = "Tibbiy Konsultatsiya"
admin.site.index_title = "Boshqaruv Paneli"
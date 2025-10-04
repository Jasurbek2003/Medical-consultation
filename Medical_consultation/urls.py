from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Custom Admin Panel
    path('admin-panel/', include('apps.admin_panel.urls')),

    # API Documentation (Swagger/OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API endpoints
    path('api/v1/users/', include('apps.users.api_urls')),
    path('api/v1/doctors/', include('apps.doctors.api_urls')),
    path('api/v1/hospitals/', include('apps.hospitals.urls')),
    path('api/v1/consultations/', include('apps.consultations.api_urls')),
    path('api/v1/chat/', include('apps.chat.api_urls')),
    path('api/v1/translate/', include('apps.translate.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),

    # Translation API endpoints
    # path('api/translate/text/', translate_text_api, name='translate-text'),
    # path('api/translate/batch/', batch_translate_api, name='batch-translate'),
    # path('api/translate/all-doctors/', translate_all_doctors_api, name='translate-all-doctors'),
    # path('api/translate/languages/', get_translation_languages, name='translation-languages'),
]

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

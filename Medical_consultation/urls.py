from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.doctors.serializers import translate_text_api
from apps.doctors.views import batch_translate_api, translate_all_doctors_api, get_translation_languages

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Custom Admin Panel
    path('admin-panel/', include('apps.admin_panel.urls')),

    # Hospital Admin Panel
    # path('hospital-admin/', include('apps.hospitals.urls')),

    # API endpoints
    path('api/v1/users/', include('apps.users.api_urls')),
    path('api/v1/doctors/', include('apps.doctors.api_urls')),
    path('api/v1/hospitals/', include('apps.hospitals.urls')),
    path('api/v1/consultations/', include('apps.consultations.api_urls')),
    path('api/v1/chat/', include('apps.chat.api_urls')),

    # Web interface
    path('', include('apps.api.urls')),  # Landing page and quick API
    path('users/', include('apps.users.web_urls')),
    path('doctors/', include('apps.doctors.web_urls')),
    path('hospitals/', include('apps.hospitals.urls')),
    path('chat/', include('apps.chat.web_urls')),

    # Translation API endpoints
    path('api/translate/text/', translate_text_api, name='translate-text'),
    path('api/translate/batch/', batch_translate_api, name='batch-translate'),
    path('api/translate/all-doctors/', translate_all_doctors_api, name='translate-all-doctors'),
    path('api/translate/languages/', get_translation_languages, name='translation-languages'),
]

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add custom error handlers
handler404 = 'apps.api.views.custom_404'
handler500 = 'apps.api.views.custom_500'
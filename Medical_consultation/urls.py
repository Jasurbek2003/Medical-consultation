from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Custom Admin Panel
    path('admin-panel/', include('apps.admin_panel.urls')),

    # Hospital Admin Panel
    path('hospital-admin/', include('apps.hospitals.urls')),

    # API endpoints
    path('api/v1/users/', include('apps.users.api_urls')),
    path('api/v1/doctors/', include('apps.doctors.api_urls')),
    path('api/v1/hospitals/', include('apps.hospitals.urls')),
    path('users-web/', include(('apps.users.web_urls', 'users_web'))),
    path('api/v1/consultations/', include('apps.consultations.api_urls')),
    path('api/v1/chat/', include('apps.chat.api_urls')),

    # Web interface
    path('', include('apps.api.urls')),  # Landing page and quick API
    path('users/', include('apps.users.web_urls')),
    path('doctors/', include('apps.doctors.web_urls')),
    path('hospitals/', include('apps.hospitals.urls')),
    path('chat/', include('apps.chat.web_urls')),

    # WebSocket for chat
    # Note: WebSocket URLs are handled in routing.py for Django Channels
]

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add custom error handlers
handler404 = 'apps.api.views.custom_404'
handler500 = 'apps.api.views.custom_500'
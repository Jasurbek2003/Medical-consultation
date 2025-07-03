from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import UserViewSet, UserMedicalHistoryViewSet, UserPreferencesViewSet

app_name = 'users'

# API Router
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'medical-history', UserMedicalHistoryViewSet, basename='medical-history')
router.register(r'preferences', UserPreferencesViewSet, basename='preferences')

urlpatterns = [
    path('api/', include(router.urls)),
]
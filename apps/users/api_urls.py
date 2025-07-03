from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import UserViewSet, UserMedicalHistoryViewSet, UserPreferencesViewSet

app_name = 'users_api'

# DRF Router
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'medical-history', UserMedicalHistoryViewSet, basename='medical_history')
router.register(r'preferences', UserPreferencesViewSet, basename='preferences')

urlpatterns = [
    # DRF Router URL'lari
    path('', include(router.urls)),
]
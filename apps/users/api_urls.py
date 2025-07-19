from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views
from . import api_views
from . import web_views

app_name = 'users_api'

# API Router
router = DefaultRouter()
router.register(r'users', api_views.UserViewSet)
router.register(r'medical-history', api_views.UserMedicalHistoryViewSet, basename='medicalhistory')
router.register(r'preferences', api_views.UserPreferencesViewSet, basename='preferences')

app_name = 'users'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/auth/login/', api_views.CustomAuthToken.as_view(), name='api_login'),
    path('api/auth/token/', obtain_auth_token, name='api_token'),

    # Web views (future implementation)
    path('login/', web_views.login_view, name='login'),
    path('logout/', web_views.logout_view, name='logout'),
    path('register/', web_views.register_view, name='register'),
    path('profile/', web_views.profile_view, name='profile'),
    path('profile/edit/', web_views.edit_profile_view, name='edit_profile'),
]
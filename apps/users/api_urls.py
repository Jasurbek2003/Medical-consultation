from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import api_views

app_name = 'users_api'

# Router for ViewSets (if any)
router = DefaultRouter()

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Authentication endpoints
    path('auth/register/', api_views.UserRegistrationAPIView.as_view(), name='register'),
    path('auth/login/', api_views.quick_login, name='login'),
    path('auth/token/', obtain_auth_token, name='token'),  # Alternative token endpoint

    # Profile management
    path('profile/', api_views.UserProfileAPIView.as_view(), name='profile'),
    path('profile/change-password/', api_views.ChangePasswordAPIView.as_view(), name='change_password'),
    path('profile/upload-avatar/', api_views.UploadAvatarAPIView.as_view(), name='upload_avatar'),
    path('profile/delete-account/', api_views.DeleteAccountAPIView.as_view(), name='delete_account'),

    # Quick endpoints (simplified versions)
    path('quick/register/', api_views.quick_register, name='quick_register'),
    path('quick/login/', api_views.quick_login, name='quick_login'),
    path('quick/profile/', api_views.get_my_profile, name='quick_profile'),
    path('quick/update-profile/', api_views.update_my_profile, name='quick_update_profile'),

    # Service search endpoints
    path('services/search/', api_views.ServiceSearchAPIView.as_view(), name='service_search'),
    path('services/doctors/', api_views.DoctorServicesAPIView.as_view(), name='doctor_services'),
    path('services/hospitals/', api_views.HospitalServicesAPIView.as_view(), name='hospital_services'),

    # Hospital detail endpoints (authenticated users only)
    path('hospitals/<uuid:hospital_id>/', api_views.HospitalDetailAPIView.as_view(), name='hospital_detail'),
    path('hospitals/<uuid:hospital_id>/phone/', api_views.HospitalPhoneAPIView.as_view(), name='hospital_phone'),
]

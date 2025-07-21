from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api_views

app_name = 'doctors_api'

# Router for ViewSets
router = DefaultRouter()
# router.register(r'doctors', api_views.DoctorViewSet, basename='doctor')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Authentication endpoints (NEW)
    path('auth/register/', api_views.DoctorRegistrationView.as_view(), name='doctor_register'),
    path('auth/login/', api_views.DoctorLoginView.as_view(), name='doctor_login'),
    path('auth/profile/', api_views.DoctorProfileView.as_view(), name='doctor_profile'),
    path('auth/change-password/', api_views.DoctorChangePasswordView.as_view(), name='doctor_change_password'),
    path('auth/toggle-availability/', api_views.DoctorAvailabilityToggleView.as_view(),
         name='doctor_toggle_availability'),

    # Quick authentication endpoints
    path('auth/quick-register/', api_views.quick_doctor_register, name='quick_doctor_register'),
    path('auth/quick-login/', api_views.quick_doctor_login, name='quick_doctor_login'),

    # Existing endpoints
    path('search/', api_views.DoctorSearchView.as_view(), name='doctor_search'),
    # path('filter/', api_views.DoctorFilterView.as_view(), name='doctor_filter'),
    path('top-rated/', api_views.TopRatedDoctorsView.as_view(), name='top_rated'),
    # path('available/', api_views.AvailableDoctorsView.as_view(), name='available'),
    path('by-specialty/<str:specialty>/', api_views.DoctorsBySpecialtyView.as_view(), name='by_specialty'),
    # path('statistics/', api_views.DoctorStatisticsView.as_view(), name='statistics'),

    # Public endpoints (no authentication required)
    path('public/list/', api_views.PublicDoctorListView.as_view(), name='public_list'),
    path('public/detail/<uuid:doctor_id>/', api_views.PublicDoctorDetailView.as_view(), name='public_detail'),
    path('public/search/', api_views.PublicDoctorSearchView.as_view(), name='public_search'),
    path('public/specialties/', api_views.PublicSpecialtiesView.as_view(), name='public_specialties'),
    path('public/featured/', api_views.FeaturedDoctorsView.as_view(), name='featured_doctors'),
    path('public/top-rated/', api_views.TopRatedDoctorsView.as_view(), name='top_rated_public'),
]
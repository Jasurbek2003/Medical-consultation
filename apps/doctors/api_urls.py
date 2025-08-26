from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DoctorViewSet, RegionViewSet, DistrictViewSet, DoctorFilesViewSet,
    DoctorScheduleViewSet, DoctorSpecializationViewSet,
    DoctorListView, DoctorDetailView, DoctorRegistrationView,
    DoctorLocationUpdateView, DoctorFileUploadView, DoctorSearchView,
    DoctorStatsView, LocationAPIView, RegionDistrictsView, DoctorFileDeleteView, DoctorServiceCreateView,
    DoctorProfileView
)

# Router for ViewSets
router = DefaultRouter()
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'districts', DistrictViewSet, basename='district')
router.register(r'doctor-files', DoctorFilesViewSet, basename='doctor-files')
router.register(r'doctor-schedules', DoctorScheduleViewSet, basename='doctor-schedule')
router.register(r'doctor-specializations', DoctorSpecializationViewSet, basename='doctor-specialization')

app_name = 'doctors'

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Legacy API endpoints (for backward compatibility)
    path('list/', DoctorListView.as_view(), name='doctor-list'),
    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('profile/', DoctorProfileView.as_view(), name='doctor-detail'),
    path('toggle-availability/', DoctorProfileView.as_view(), name='doctor-detail'),
    path('register/', DoctorRegistrationView.as_view(), name='doctor-register'),
    path('search/', DoctorSearchView.as_view(), name='doctor-search'),

    # Doctor management endpoints
    path('<int:pk>/location/', DoctorLocationUpdateView.as_view(), name='doctor-location-update'),
    path('upload-file/', DoctorFileUploadView.as_view(), name='doctor-file-upload'),
    path('delete-file/', DoctorFileDeleteView.as_view(), name='doctor-file-delete'),
    path('service/', DoctorServiceCreateView.as_view(), name='doctor-file-delete'),
    path('<int:pk>/stats/', DoctorStatsView.as_view(), name='doctor-stats'),

    # Location endpoints
    path('locations/', LocationAPIView.as_view(), name='locations'),
    path('regions/<int:region_id>/districts/', RegionDistrictsView.as_view(), name='region-districts'),
]
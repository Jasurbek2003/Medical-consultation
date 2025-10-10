from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ..admin_panel.views import (
    doctor_complaint_detail,
    doctor_complaint_list,
    doctor_create_complaint,
)
from .api_views import DoctorServiceNameViewSet
from .views import (
    DistrictViewSet,
    DoctorAvailabilityToggleView,
    DoctorChargeLogsView,
    DoctorChargeSettingsView,
    DoctorComplaintFileViewSet,
    DoctorDetailView,
    DoctorFileDeleteView,
    DoctorFilesViewSet,
    DoctorFileUploadView,
    DoctorListView,
    DoctorLocationUpdateView,
    DoctorPhoneNumberView,
    DoctorProfileTranslationAPIView,
    DoctorProfileView,
    DoctorRegistrationView,
    DoctorScheduleViewSet,
    DoctorSearchLimitView,
    DoctorSearchStatsView,
    DoctorSearchView,
    DoctorServiceCreateView,
    DoctorServiceNameAPIView,
    DoctorSpecializationViewSet,
    DoctorSpecialtiesView,
    DoctorStatsView,
    DoctorViewSet,
    DoctorWalletView,
    LocationAPIView,
    RegionDistrictsView,
    RegionViewSet,
)
from .views_statistics import DoctorStatisticsOverviewView

# Router for ViewSets
router = DefaultRouter()
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'districts', DistrictViewSet, basename='district')
router.register(r'doctor-files', DoctorFilesViewSet, basename='doctor-files')
router.register(r'doctor-schedules', DoctorScheduleViewSet, basename='doctor-schedule')
router.register(r'doctor-specializations', DoctorSpecializationViewSet, basename='doctor-specialization')
router.register(r'service-names', DoctorServiceNameViewSet, basename='doctor-service-name')
router.register(r'complaint-files', DoctorComplaintFileViewSet, basename='complaint-file')

app_name = 'doctors'

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Legacy API endpoints (for backward compatibility)
    path('list/', DoctorListView.as_view(), name='doctor-list'),
    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('profile/', DoctorProfileView.as_view(), name='doctor-detail'),
    path('statistics-overview/', DoctorStatisticsOverviewView.as_view(), name='doctor-statistics-overview'),
    path('translate/', DoctorProfileTranslationAPIView.as_view(), name='doctor-detail'),
    path('toggle-availability/', DoctorAvailabilityToggleView.as_view(), name='doctor-detail'),
    path('register/', DoctorRegistrationView.as_view(), name='doctor-register'),
    path('search/', DoctorSearchView.as_view(), name='doctor-search'),
    path('specialties/', DoctorSpecialtiesView.as_view(), name='doctor-search'),
    # Doctor management endpoints
    path('<int:pk>/location/', DoctorLocationUpdateView.as_view(), name='doctor-location-update'),
    path('upload-file/', DoctorFileUploadView.as_view(), name='doctor-file-upload'),
    path('delete-file/', DoctorFileDeleteView.as_view(), name='doctor-file-delete'),
    path('service/', DoctorServiceCreateView.as_view(), name='doctor-file-delete'),
    path('service/list/', DoctorServiceNameAPIView.as_view(), name='doctor-file-delete'),
    path('<int:pk>/stats/', DoctorStatsView.as_view(), name='doctor-stats'),

    # Location endpoints
    path('locations/', LocationAPIView.as_view(), name='locations'),
    path('regions/<int:region_id>/districts/', RegionDistrictsView.as_view(), name='region-districts'),

    # Doctor complaint endpoints (for doctors to manage their own complaints)
    path('complaints/', doctor_complaint_list, name='doctor-complaint-list'),
    path('complaints/create/', doctor_create_complaint, name='doctor-create-complaint'),
    path('complaints/<int:complaint_id>/', doctor_complaint_detail, name='doctor-complaint-detail'),

    # Charge management endpoints
    path('<int:pk>/phone/', DoctorPhoneNumberView.as_view(), name='doctor-phone-view'),
    path('charges/', DoctorChargeSettingsView.as_view(), name='doctor-charge-settings'),
    path('charges/logs/', DoctorChargeLogsView.as_view(), name='doctor-charge-logs'),
    path('wallet/', DoctorWalletView.as_view(), name='doctor-wallet'),

    # Search limit management endpoints
    path('search-limit/', DoctorSearchLimitView.as_view(), name='doctor-search-limit'),
    path('search-stats/', DoctorSearchStatsView.as_view(), name='doctor-search-stats'),
]

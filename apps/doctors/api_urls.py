# apps/doctors/api_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import api_views

app_name = 'doctors_api'

# API Router
router = DefaultRouter()
router.register(r'', views.DoctorViewSet, basename='doctor')
router.register(r'schedules', views.DoctorScheduleViewSet, basename='schedule')

urlpatterns = [
    # DRF Router URLs - these handle the main CRUD operations
    path('', include(router.urls)),

    # Additional endpoints can be added here as needed
    # Example:
    # path('search/', views.DoctorSearchView.as_view(), name='search'),
    # path('specialties/', views.DoctorSpecialtiesView.as_view(), name='specialties'),
    # path('statistics/', views.DoctorStatisticsView.as_view(), name='statistics'),
path('filter/by-rating/', api_views.DoctorsByRatingView.as_view(), name='by_rating'),
path('filter/by-price/', api_views.DoctorsByPriceView.as_view(), name='by_price'),
# path('nearby/', api_views.NearbyDoctorsView.as_view(), name='nearby'),
#
# # Doctor reviews and ratings
# path('reviews/', api_views.DoctorReviewsView.as_view(), name='reviews'),
# path('reviews/summary/', api_views.DoctorReviewSummaryView.as_view(), name='review_summary'),
# path('rating/update/', api_views.UpdateDoctorRatingView.as_view(), name='update_rating'),
#
# # Doctor verification and approval (Admin only)
# path('verification/pending/', api_views.PendingDoctorsView.as_view(), name='pending_verification'),
# path('verification/approve/<uuid:doctor_id>/', api_views.ApproveDoctorView.as_view(), name='approve'),
# path('verification/reject/<uuid:doctor_id>/', api_views.RejectDoctorView.as_view(), name='reject'),
# path('verification/bulk-approve/', api_views.BulkApproveDoctorsView.as_view(), name='bulk_approve'),
#
# # Doctor consultations
# path('consultations/', api_views.DoctorConsultationsView.as_view(), name='consultations'),
# path('consultations/upcoming/', api_views.DoctorUpcomingConsultationsView.as_view(), name='upcoming_consultations'),
# path('consultations/history/', api_views.DoctorConsultationHistoryView.as_view(), name='consultation_history'),
# path('consultations/statistics/', api_views.DoctorConsultationStatsView.as_view(), name='consultation_stats'),
#
# # Doctor specialty management
# path('specialties/', api_views.DoctorSpecialtiesListView.as_view(), name='specialties_list'),
# path('specialties/add/', api_views.AddDoctorSpecialtyView.as_view(), name='add_specialty'),
# path('specialties/remove/<int:specialty_id>/', api_views.RemoveDoctorSpecialtyView.as_view(), name='remove_specialty'),
#
# # Doctor hospital management (for hospital admins)
# path('hospital/doctors/', api_views.HospitalDoctorsView.as_view(), name='hospital_doctors'),
# path('hospital/add-doctor/', api_views.AddDoctorToHospitalView.as_view(), name='add_to_hospital'),
# path('hospital/remove-doctor/<uuid:doctor_id>/', api_views.RemoveDoctorFromHospitalView.as_view(),
#      name='remove_from_hospital'),
#
# # Doctor notifications
# path('notifications/', api_views.DoctorNotificationsView.as_view(), name='notifications'),
# path('notifications/mark-read/', api_views.MarkNotificationsReadView.as_view(), name='mark_notifications_read'),
#
# # Doctor export and reports
# path('export/profile/', api_views.ExportDoctorProfileView.as_view(), name='export_profile'),
# path('export/statistics/', api_views.ExportDoctorStatisticsView.as_view(), name='export_statistics'),
# path('reports/monthly/', api_views.DoctorMonthlyReportView.as_view(), name='monthly_report'),
# path('reports/yearly/', api_views.DoctorYearlyReportView.as_view(), name='yearly_report'),

# Public endpoints (no authentication required)
path('public/list/', api_views.PublicDoctorListView.as_view(), name='public_list'),
path('public/detail/<uuid:doctor_id>/', api_views.PublicDoctorDetailView.as_view(), name='public_detail'),
path('public/search/', api_views.PublicDoctorSearchView.as_view(), name='public_search'),
path('public/specialties/', api_views.PublicSpecialtiesView.as_view(), name='public_specialties'),
path('public/featured/', api_views.FeaturedDoctorsView.as_view(), name='featured_doctors'),
path('public/top-rated/', api_views.TopRatedDoctorsView.as_view(), name='top_rated'),

# Utility endpoints
# path('validate-license/', api_views.ValidateLicenseView.as_view(), name='validate_license'),
# path('check-availability/', api_views.CheckDoctorAvailabilityView.as_view(), name='check_availability'),
# path('working-hours/', api_views.DoctorWorkingHoursView.as_view(), name='working_hours'),
#
# # Bulk operations (Admin only)
# path('bulk/update-status/', api_views.BulkUpdateDoctorStatusView.as_view(), name='bulk_update_status'),
# path('bulk/assign-hospital/', api_views.BulkAssignHospitalView.as_view(), name='bulk_assign_hospital'),
# path('bulk/export/', api_views.BulkExportDoctorsView.as_view(), name='bulk_export'),
#
# # Analytics for admins
# path('analytics/overview/', api_views.DoctorsAnalyticsOverviewView.as_view(), name='analytics_overview'),
# path('analytics/by-specialty/', api_views.DoctorsBySpecialtyAnalyticsView.as_view(), name='analytics_by_specialty'),
# path('analytics/by-region/', api_views.DoctorsByRegionAnalyticsView.as_view(), name='analytics_by_region'),
# path('analytics/performance-trends/', api_views.DoctorPerformanceTrendsView.as_view(), name='performance_trends'),
]
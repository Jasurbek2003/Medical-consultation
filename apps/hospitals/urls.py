from django.urls import path

from . import views

app_name = 'hospital_admin'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.HospitalDashboardAPIView.as_view(), name='api_dashboard'),
    path('profile/', views.HospitalProfileAPIView.as_view(), name='api_dashboard'),
    path('translate/', views.HospitalProfileTranslationAPIView.as_view(), name='api_dashboard'),
    path('service/', views.ServiceAPIView.as_view(), name='api_dashboard'),
    path('service/<int:service_id>', views.ServiceAPIView.as_view(), name='api_dashboard'),

    # Doctor management
    path('doctors/', views.HospitalDoctorsListAPIView.as_view(), name='api_doctors_list'),
    path('doctors/<int:doctor_id>/', views.DoctorDetailWithBillingAPIView.as_view(), name='api_doctor_detail'),
    path('doctors/<int:doctor_id>/translate/', views.DoctorTranslationAPIView.as_view(), name='api_doctor_detail'),
    path('doctors/<int:doctor_id>/access-check/', views.DoctorViewAccessCheckAPIView.as_view(),
         name='api_doctor_access_check'),

    # Revenue analytics
    path('analytics/revenue/', views.HospitalRevenueAnalyticsAPIView.as_view(), name='api_revenue_analytics'),

    # Payment integration
    path('payments/gateways/', views.PaymentIntegrationAPIView.as_view(), name='api_payment_gateways'),
    path('payments/create/', views.PaymentIntegrationAPIView.as_view(), name='api_create_payment'),

    # Location data
    path('locations/regions/', views.RegionsListAPIView.as_view(), name='api_regions'),
    path('locations/districts/', views.DistrictsListAPIView.as_view(), name='api_districts'),
    path('locations/districts/<int:region_id>', views.DistrictsListAPIView.as_view(), name='api_districts'),

    path('list/', views.HospitalListAPIView.as_view(), name='api_hospital_list'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'admin_panel'
router = DefaultRouter()
router.register(r'hospitals', views.AdminHospitalViewSet, basename='admin-hospital')
router.register(r'doctors', views.AdminDoctorViewSet, basename='admin-doctor')
router.register(r'complaints', views.DoctorComplaintViewSet, basename='doctor-complaint')
router.register(r'complaint-files', views.DoctorComplaintFileViewSet, basename='complaint-file')
urlpatterns = [
    path('dashboard/', views.AdminDashboardAPIView.as_view(), name='dashboard'),
    path('', include(router.urls)),

    # Doctor Management
    path('', views.doctor_management, name='doctor_management'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:doctor_id>/approve/', views.approve_doctor, name='approve_doctor'),
    path('doctors/<int:doctor_id>/reject/', views.reject_doctor, name='reject_doctor'),

    # User Management
    path('hospitals/', views.hospital_management, name='hospital_management'),
    path('hospitals/create-admin/', views.create_hospital_admin, name='create_hospital_admin'),

    # Statistics and Reports
    path('export/', views.export_data, name='export_data'),
    # Utility endpoints
    path('export/', views.export_data, name='export-data'),
    path('filter-options/', views.get_filter_options, name='filter-options'),
    path('bulk-actions/', views.bulk_actions, name='bulk-actions'),

    # Custom hospital endpoints (additional to ViewSet)
    # path('hospitals/<int:pk>/assign-admin/', api_views.assign_hospital_admin, name='assign-hospital-admin'),
    # path('hospitals/<int:pk>/remove-admin/', api_views.remove_hospital_admin, name='remove-hospital-admin'),

    # Custom doctor endpoints (additional to ViewSet)
    # path('doctors/<int:pk>/profile-complete/', api_views.check_doctor_profile_complete, name='doctor-profile-complete'),
    # path('doctors/<int:pk>/consultation-history/', api_views.doctor_consultation_history, name='doctor-consultation-history'),

    # Complaint Management
    path('complaints/dashboard/', views.complaint_dashboard, name='complaint-dashboard'),
    path('complaints/export/', views.complaint_export, name='complaint-export'),
]
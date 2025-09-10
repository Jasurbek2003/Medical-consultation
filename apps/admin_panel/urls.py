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

]
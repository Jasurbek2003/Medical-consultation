from django.urls import include, path
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
    path('hospitals/create-admin/', views.create_hospital_admin, name='create_hospital_admin'),
    path('', include(router.urls)),

    # Doctor Management
    path('', views.doctor_management, name='doctor_management'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:doctor_id>/approve/', views.approve_doctor, name='approve_doctor'),
    path('doctors/<int:doctor_id>/reject/', views.reject_doctor, name='reject_doctor'),

    # User Management
    path('hospitals/', views.hospital_management, name='hospital_management'),
    path('hospital-admins/', views.hospital_admin_list, name='hospital_admin_list'),
    path('hospital-admins/<int:admin_id>/', views.hospital_admin_detail, name='hospital_admin_detail'),
    path('hospital-admins/<int:admin_id>/activate-deactivate/', views.hospital_admin_activate_deactivate, name='hospital_admin_activate_deactivate'),
    path('hospital-admins/<int:admin_id>/verify/', views.hospital_admin_verify, name='hospital_admin_verify'),
    path('hospital-admins/<int:admin_id>/delete/', views.hospital_admin_delete, name='hospital_admin_delete'),

    # Statistics and Reports
    path('export/', views.export_data, name='export_data'),
    # Utility endpoints
    path('export/', views.export_data, name='export-data'),
    path('filter-options/', views.get_filter_options, name='filter-options'),
    path('bulk-actions/', views.bulk_actions, name='bulk-actions'),

    # Transaction Management
    path('transactions/wallet/', views.wallet_transactions_list, name='wallet_transactions_list'),
    path('transactions/doctor-charges/', views.doctor_charges_list, name='doctor_charges_list'),
    path('transactions/hospital/<int:hospital_id>/', views.hospital_transactions, name='hospital_transactions'),
    path('transactions/doctor/<int:doctor_id>/', views.doctor_transactions, name='doctor_transactions'),
    path('transactions/statistics/', views.transaction_statistics, name='transaction_statistics'),

    # Doctor Statistics
    path('doctors-statistics/', views.doctors_statistics_list, name='doctors_statistics_list'),
    path('doctors-statistics/<int:doctor_id>/', views.doctor_statistics_detail, name='doctor_statistics_detail'),
    path('doctors-statistics/summary/', views.doctors_statistics_summary, name='doctors_statistics_summary'),

    # Doctor Service Name Management
    path('doctor-service-names/', views.list_doctor_service_names, name='list_doctor_service_names'),
    path('doctor-service-names/create/', views.create_doctor_service_name, name='create_doctor_service_name'),
    path('doctor-service-names/<int:service_id>/', views.get_doctor_service_name_detail, name='get_doctor_service_name_detail'),
    path('doctor-service-names/<int:service_id>/delete/', views.delete_doctor_service_name, name='delete_doctor_service_name'),

    # User Complaint Management (Authenticated Users)
    path('user-complaints/create/', views.create_user_complaint, name='create_user_complaint'),
    path('user-complaints/my-complaints/', views.user_complaint_list, name='user_complaint_list'),
    path('user-complaints/my-complaints/<int:complaint_id>/', views.user_complaint_detail, name='user_complaint_detail'),

    # User Complaint Management (Admin Only)
    path('user-complaints/admin/', views.admin_user_complaint_list, name='admin_user_complaint_list'),
    path('user-complaints/admin/<int:complaint_id>/', views.admin_user_complaint_detail, name='admin_user_complaint_detail'),
    path('user-complaints/admin/<int:complaint_id>/update/', views.admin_update_user_complaint, name='admin_update_user_complaint'),
    path('user-complaints/admin/statistics/', views.admin_user_complaint_statistics, name='admin_user_complaint_statistics'),

]

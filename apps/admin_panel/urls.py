from django.urls import path

from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    # path('', views.admin_dashboard, name='dashboard'),

    # Doctor Management
    path('', views.doctor_management, name='doctor_management'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:doctor_id>/approve/', views.approve_doctor, name='approve_doctor'),
    path('doctors/<int:doctor_id>/reject/', views.reject_doctor, name='reject_doctor'),

    # User Management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),

    # Hospital Management
    path('hospitals/', views.hospital_management, name='hospital_management'),
    path('hospitals/create-admin/', views.create_hospital_admin, name='create_hospital_admin'),

    # Statistics and Reports
    path('statistics/', views.statistics_overview, name='statistics'),
    path('export/', views.export_data, name='export_data'),

    # Settings
    path('settings/', views.system_settings, name='system_settings'),
]
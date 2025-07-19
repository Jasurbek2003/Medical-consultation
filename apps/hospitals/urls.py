from django.urls import path

from . import views

app_name = 'hospital_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Doctor Management
    path('doctors/', views.doctors_list, name='doctors_list'),
    path('doctors/<uuid:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    # path('doctors/statistics/', views.s, name='doctor_statistics'),
    path('ajax/doctor-stats/<uuid:doctor_id>/', views.ajax_doctor_stats, name='ajax_doctor_stats'),
    path('ajax/doctor-availability/<uuid:doctor_id>/', views.doctor_availability_toggle,
         name='doctor_availability_toggle'),

    # Consultations
    path('consultations/', views.consultations_overview, name='consultations_overview'),

    # Hospital Management
    path('hospital/profile/', views.hospital_profile, name='hospital_profile'),
    path('profile/', views.my_profile, name='my_profile'),

    # Reports and Analytics
    # path('reports/', views.reports_and_analytics, name='reports_and_analytics'),
    # path('export/', views.export_hospital_data, name='export_hospital_data'),

    # Notifications
    path('notifications/', views.notification_center, name='notification_center'),
]

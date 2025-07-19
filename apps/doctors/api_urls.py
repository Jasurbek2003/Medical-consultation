from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# API Router
router = DefaultRouter()
router.register(r'doctors', views.DoctorViewSet)
router.register(r'schedules', views.DoctorScheduleViewSet, basename='schedule')

app_name = 'doctors'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),

    # Web views
    path('', views.DoctorListView.as_view(), name='list'),
    path('<uuid:pk>/', views.DoctorDetailView.as_view(), name='detail'),
    path('register/', views.doctor_register_view, name='register'),
    path('dashboard/', views.doctor_dashboard_view, name='dashboard'),
    path('profile/', views.doctor_profile_view, name='profile'),
    path('profile/edit/', views.edit_doctor_profile_view, name='edit_profile'),
    path('schedule/', views.doctor_schedule_view, name='schedule'),
    path('statistics/', views.doctor_statistics_view, name='statistics'),
]
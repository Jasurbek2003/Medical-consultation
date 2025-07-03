from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # API umumiy ko'rinish
    path('', views.api_overview, name='overview'),

    # Tez chat endpoint'lari
    path('chat/quick-message/', views.quick_send_message, name='quick_send_message'),
    path('chat/classify/', views.quick_classify_issue, name='quick_classify'),

    # Tez shifokor endpoint'lari
    path('doctors/', views.quick_get_doctors, name='quick_doctors'),
    path('doctors/search/', views.quick_search_doctors, name='quick_search'),
    path('doctors/specialties/', views.quick_get_specialties, name='quick_specialties'),
    path('doctors/by-specialty/', views.quick_doctors_by_specialty, name='quick_doctors_by_specialty'),

    # Tizim monitoring
    path('health/', views.quick_health_check, name='health_check'),
    path('stats/', views.quick_stats, name='quick_stats'),
    #
    # Qo'shimcha foydali endpoint'lar
    path('regions/', views.get_regions, name='regions'),
    path('emergency-info/', views.get_emergency_info, name='emergency_info'),
]
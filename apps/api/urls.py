from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # API overview
    path('', views.api_overview, name='overview'),

    # Quick endpoints
    path('quick/send-message/', views.quick_send_message, name='quick_send_message'),
    path('quick/doctors/', views.quick_get_doctors, name='quick_doctors'),
    path('quick/specialties/', views.quick_get_specialties, name='quick_specialties'),
    path('quick/search-doctors/', views.quick_search_doctors, name='quick_search'),
    path('quick/health/', views.quick_health_check, name='health_check'),
    path('quick/stats/', views.quick_stats, name='quick_stats'),
]
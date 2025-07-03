from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'doctors_api'

# DRF Router
router = DefaultRouter()
router.register(r'', views.DoctorViewSet, basename='doctor')

urlpatterns = [
    # DRF Router URL'lari
    path('', include(router.urls)),

    # AJAX endpoint'lar (JSON response)
    path('ajax/search/', views.doctor_search_ajax, name='ajax_search'),
    path('ajax/by-specialty/', views.get_doctors_by_specialty, name='by_specialty'),
    path('ajax/specialties/', views.get_specialties_list, name='specialties'),
]
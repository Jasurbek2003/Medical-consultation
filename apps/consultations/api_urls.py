from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    ConsultationViewSet, ReviewViewSet, ConsultationDiagnosisViewSet,
    ConsultationPrescriptionViewSet, ConsultationRecommendationViewSet
)

app_name = "consultations_api"

# DRF Router
router = DefaultRouter()
router.register(r'', ConsultationViewSet, basename='consultation')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'diagnoses', ConsultationDiagnosisViewSet, basename='diagnosis')
router.register(r'prescriptions', ConsultationPrescriptionViewSet, basename='prescription')
router.register(r'recommendations', ConsultationRecommendationViewSet, basename='recommendation')

urlpatterns = [
    # DRF Router URL'lari
    path('', include(router.urls)),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import (
    ConsultationViewSet, ReviewViewSet, ConsultationDiagnosisViewSet,
    ConsultationPrescriptionViewSet, ConsultationRecommendationViewSet
)

app_name = "consultations"

# API Router
router = DefaultRouter()
router.register(r'', ConsultationViewSet, basename='consultation')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'diagnoses', ConsultationDiagnosisViewSet, basename='diagnosis')
router.register(r'prescriptions', ConsultationPrescriptionViewSet, basename='prescription')
router.register(r'recommendations', ConsultationRecommendationViewSet, basename='recommendation')

urlpatterns = [
    # API endpoints
    path("api/", include(router.urls)),
]
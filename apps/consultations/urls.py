from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "consultations"

router = DefaultRouter()

urlpatterns = [
    path("api/", include(router.urls)),
]
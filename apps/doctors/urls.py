from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'doctors'

# API Router
router = DefaultRouter()
router.register(r"", views.DoctorViewSet, basename="doctor")

urlpatterns = [
    # Web views
    path("list/", views.DoctorListView.as_view(), name="list"),
    path("detail/<int:pk>/", views.DoctorDetailView.as_view(), name="detail"),
    path("search/", views.DoctorSearchView.as_view(), name="search"),

    # API endpoints
    path("api/", include(router.urls)),

    # AJAX endpoints
    path("ajax/search/", views.doctor_search_ajax, name="ajax_search"),
    path("ajax/by-specialty/", views.get_doctors_by_specialty, name="by_specialty"),
    path("ajax/specialties/", views.get_specialties_list, name="specialties"),
]
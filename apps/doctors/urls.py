from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'doctors'

router = DefaultRouter()
router.register(r"api", views.DoctorViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("list/", views.DoctorListView.as_view(), name="list"),
    path("<int:pk>/", views.DoctorDetailView.as_view(), name="detail"),
    path("search/", views.DoctorSearchView.as_view(), name="search"),
    path("ajax/search/", views.doctor_search_ajax, name="ajax_search"),
    path("ajax/by-specialty/", views.get_doctors_by_specialty, name="by_specialty"),
    path("ajax/specialties/", views.get_specialties_list, name="specialties"),
]

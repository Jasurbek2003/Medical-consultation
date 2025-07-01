from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'doctors'

router = DefaultRouter()
# router.register(r'', views.DoctorViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    # Web views
    # path('', views.DoctorListView.as_view(), name='list'),
    # path('<int:pk>/', views.DoctorDetailView.as_view(), name='detail'),
    # path('search/', views.DoctorSearchView.as_view(), name='search'),
]
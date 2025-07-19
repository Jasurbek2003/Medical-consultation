from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    # Web sahifalar
    # path('', views.DoctorListView.as_view(), name='list'),
    # path('<int:pk>/', views.DoctorDetailView.as_view(), name='detail'),
    # path('search/', views.DoctorSearchView.as_view(), name='search'),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'consultations'

router = DefaultRouter()
# router.register(r'', views.ConsultationViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    # Web views
    # path('', views.ConsultationListView.as_view(), name='list'),
    # path('<int:pk>/', views.ConsultationDetailView.as_view(), name='detail'),
    # path('history/', views.ConsultationHistoryView.as_view(), name='history'),
]
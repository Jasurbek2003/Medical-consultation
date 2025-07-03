from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    ChatSessionViewSet, ChatMessageViewSet,
    ChatFeedbackViewSet, DoctorRecommendationViewSet
)
from . import views

app_name = "chat_api"

# DRF Router
router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='session')
router.register(r'messages', ChatMessageViewSet, basename='message')
router.register(r'feedback', ChatFeedbackViewSet, basename='feedback')
router.register(r'recommendations', DoctorRecommendationViewSet, basename='recommendation')

urlpatterns = [
    # DRF Router URL'lari
    path('', include(router.urls)),

    # Qo'shimcha API endpoint'lar
    path('send-message/', views.ChatMessageView.as_view(), name='send_message'),
    path('classify/', views.classify_issue, name='classify'),
    path('history/<uuid:session_id>/', views.get_session_history, name='session_history'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
]
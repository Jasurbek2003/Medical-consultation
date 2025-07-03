from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import (
    ChatSessionViewSet, ChatMessageViewSet,
    ChatFeedbackViewSet, DoctorRecommendationViewSet
)

app_name = "chat"

# API Router
router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='session')
router.register(r'messages', ChatMessageViewSet, basename='message')
router.register(r'feedback', ChatFeedbackViewSet, basename='feedback')
router.register(r'recommendations', DoctorRecommendationViewSet, basename='recommendation')

urlpatterns = [
    # Web views
    path("", views.ChatRoomView.as_view(), name="room"),
    path("interface/", views.ChatInterfaceView.as_view(), name="interface"),

    # API endpoints
    path("api/", include(router.urls)),

    # Legacy endpoints (backward compatibility)
    path("message/", views.ChatMessageView.as_view(), name="api_message"),
    path("classify/", views.classify_issue, name="api_classify"),
    path("history/<uuid:session_id>/", views.get_session_history, name="session_history"),
    path("feedback/", views.submit_feedback, name="submit_feedback"),
]
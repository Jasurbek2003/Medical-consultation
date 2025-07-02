from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    # Web views
    path("", views.ChatRoomView.as_view(), name="room"),
    path("interface/", views.ChatInterfaceView.as_view(), name="interface"),

    # API endpoints (without 'api/' prefix since it's already in main urls.py)
    path("message/", views.ChatMessageView.as_view(), name="api_message"),
    path("classify/", views.classify_issue, name="api_classify"),
    path("history/<uuid:session_id>/", views.get_session_history, name="session_history"),
    path("feedback/", views.submit_feedback, name="submit_feedback"),
]
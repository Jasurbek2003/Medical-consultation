from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.ChatRoomView.as_view(), name="room"),
    path("interface/", views.ChatInterfaceView.as_view(), name="interface"),
    path("api/message/", views.ChatMessageView.as_view(), name="api_message"),
    path("api/classify/", views.classify_issue, name="api_classify"),
    path("api/history/<uuid:session_id>/", views.get_session_history, name="session_history"),
    path("api/feedback/", views.submit_feedback, name="submit_feedback"),
]
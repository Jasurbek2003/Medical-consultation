from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    # Chat sahifalar
    path('', views.ChatRoomView.as_view(), name='room'),
    path('interface/', views.ChatInterfaceView.as_view(), name='interface'),
    path('room/<uuid:session_id>/', views.ChatRoomView.as_view(), name='room_with_session'),
]
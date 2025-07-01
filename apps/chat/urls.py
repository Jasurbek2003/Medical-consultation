from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # API endpoints
    # path('api/messages/', views.ChatMessageView.as_view(), name='api_messages'),
    # path('api/classify/', views.ClassifyIssueView.as_view(), name='api_classify'),
    #
    # Web views
    # path('', views.ChatRoomView.as_view(), name='room'),
    # path('interface/', views.ChatInterfaceView.as_view(), name='interface'),
]
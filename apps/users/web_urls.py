from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Foydalanuvchi autentifikatsiya sahifalari (kelajakda)
    # path('login/', views.LoginView.as_view(), name='login'),
    # path('register/', views.RegisterView.as_view(), name='register'),
    # path('profile/', views.ProfileView.as_view(), name='profile'),

    # Hozircha bo'sh - kelajakda qo'shiladi
    # path('', views.UserListView.as_view(), name='list'),
]
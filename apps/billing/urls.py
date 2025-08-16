from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'billing'

urlpatterns = [
    # Wallet endpoints
    path('wallet/', views.UserWalletView.as_view(), name='user_wallet'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet_transactions'),
    path('wallet/stats/', views.BillingStatsView.as_view(), name='billing_stats'),

    # Billing rules
    path('rules/', views.BillingRulesView.as_view(), name='billing_rules'),

    # Balance and charging
    path('check-balance/', views.CheckBalanceView.as_view(), name='check_balance'),
    path('charge/', views.ChargeForServiceView.as_view(), name='charge_service'),

    # Doctor view billing
    path('doctor-views/', views.DoctorViewChargeHistoryView.as_view(), name='doctor_view_history'),
    path('doctor/<int:doctor_id>/check-access/', views.check_doctor_view_access, name='check_doctor_access'),
    path('doctor/<int:doctor_id>/view/', views.ProtectedDoctorDetailView.as_view(), name='protected_doctor_detail'),

    # Usage tracking
    path('daily-usage/', views.get_user_daily_usage, name='daily_usage'),
]
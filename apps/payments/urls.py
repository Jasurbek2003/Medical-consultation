from django.urls import path
from . import views as api_views

app_name = 'payments'

urlpatterns = [
    # Payment gateway management
    path('gateways/', api_views.PaymentGatewayListView.as_view(), name='gateway_list'),
    path('gateways/status/', api_views.gateway_status, name='gateway_status'),

    # Payment creation and management
    path('create/', api_views.CreatePaymentView.as_view(), name='create_payment'),
    path('<uuid:payment_id>/status/', api_views.PaymentStatusView.as_view(), name='payment_status'),
    path('<uuid:payment_id>/cancel/', api_views.cancel_payment, name='cancel_payment'),
    path('<uuid:payment_id>/verify/', api_views.verify_payment, name='verify_payment'),

    # Payment history and methods
    path('history/', api_views.PaymentHistoryView.as_view(), name='payment_history'),
    path('methods/', api_views.payment_methods, name='payment_methods'),

    # Payment estimation
    path('estimate/', api_views.estimate_payment, name='estimate_payment'),

    # Click payment webhooks
    path('click/webhook/', api_views.ClickWebhookView.as_view(), name='click_webhook'),
    path('click/prepare/', api_views.ClickPrepareView.as_view(), name='click_prepare'),
    path('click/complete/', api_views.ClickCompleteView.as_view(), name='click_complete'),

    # Payme payment webhooks
    path('payme/webhook/', api_views.PaymeWebhookView.as_view(), name='payme_webhook'),

    # Analytics (admin only)
    path('analytics/', api_views.PaymentAnalyticsView.as_view(), name='payment_analytics'),
]
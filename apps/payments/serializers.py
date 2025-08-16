from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import (
    PaymentGateway, Payment, PaymentWebhook,
    ClickTransaction, PaymeTransaction, PaymentMethod,
    PaymentRefund, PaymentDispute, PaymentProcessor
)

User = get_user_model()


class PaymentGatewaySerializer(serializers.ModelSerializer):
    """Payment gateway serializer with commission calculation"""

    commission_example = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    supported_currencies_display = serializers.SerializerMethodField()

    class Meta:
        model = PaymentGateway
        fields = [
            'name', 'display_name', 'description', 'is_active', 'is_test_mode',
            'min_amount', 'max_amount', 'commission_type', 'commission_percentage',
            'commission_fixed', 'processing_time_minutes', 'auto_capture',
            'supports_refunds', 'supports_recurring', 'default_currency',
            'supported_currencies', 'supported_currencies_display', 'logo',
            'sort_order', 'commission_example', 'is_available', 'last_used_at'
        ]
        read_only_fields = ['name', 'last_used_at']

    def get_commission_example(self, obj):
        """Calculate commission for example amounts"""
        examples = [10000, 50000, 100000, 500000]
        return {
            str(amount): {
                'amount': amount,
                'commission': float(obj.calculate_commission(Decimal(str(amount)))),
                'total': float(obj.get_total_amount(Decimal(str(amount))))
            }
            for amount in examples
        }

    def get_is_available(self, obj):
        """Check if gateway is currently available"""
        return obj.is_active and not obj.extra_config.get('maintenance_mode', False)

    def get_supported_currencies_display(self, obj):
        """Get human-readable currency names"""
        currency_map = {
            'UZS': 'Uzbek Som',
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'RUB': 'Russian Ruble'
        }
        return [
            {
                'code': currency,
                'name': currency_map.get(currency, currency)
            }
            for currency in obj.supported_currencies
        ]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer"""

    gateway_name = serializers.CharField(source='gateway.display_name', read_only=True)
    method_type_display = serializers.CharField(source='get_method_type_display', read_only=True)
    card_type_display = serializers.CharField(source='get_card_type_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    masked_details = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'gateway_name', 'method_type', 'method_type_display',
            'nickname', 'is_default', 'is_active', 'card_type', 'card_type_display',
            'card_number_masked', 'card_holder_name', 'expiry_month', 'expiry_year',
            'bank_name', 'account_number_masked', 'is_verified', 'verified_at',
            'usage_count', 'last_used_at', 'created_at', 'is_expired', 'masked_details'
        ]
        read_only_fields = [
            'id', 'gateway_token', 'gateway_customer_id', 'gateway_method_id',
            'usage_count', 'last_used_at', 'created_at', 'verified_at'
        ]

    def get_is_expired(self, obj):
        """Check if payment method is expired"""
        return obj.is_expired()

    def get_masked_details(self, obj):
        """Get masked payment details for display"""
        if obj.method_type == 'card' and obj.card_number_masked:
            return {
                'type': 'card',
                'display': f"{obj.get_card_type_display()} ****{obj.card_number_masked[-4:]}",
                'expiry': f"{obj.expiry_month}/{obj.expiry_year}" if obj.expiry_month and obj.expiry_year else None
            }
        elif obj.method_type == 'bank_account' and obj.account_number_masked:
            return {
                'type': 'bank_account',
                'display': f"{obj.bank_name} ****{obj.account_number_masked[-4:]}",
                'bank': obj.bank_name
            }
        else:
            return {
                'type': obj.method_type,
                'display': obj.nickname or obj.get_method_type_display(),
                'gateway': obj.gateway.display_name
            }


class PaymentSerializer(serializers.ModelSerializer):
    """Comprehensive payment serializer"""

    gateway_name = serializers.CharField(source='gateway.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    # Calculated fields
    is_expired = serializers.SerializerMethodField()
    can_be_refunded = serializers.SerializerMethodField()
    refunded_amount = serializers.SerializerMethodField()
    refundable_amount = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()

    # Related data
    refunds_summary = serializers.SerializerMethodField()
    disputes_summary = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'reference_number', 'user_name', 'gateway_name',
            'payment_type', 'payment_type_display', 'payment_method', 'payment_method_display',
            'currency', 'amount', 'commission', 'discount', 'total_amount',
            'status', 'status_display', 'description', 'metadata',
            'gateway_transaction_id', 'gateway_payment_id', 'gateway_reference',
            'gateway_error_code', 'gateway_error_message',
            'payment_url', 'success_url', 'cancel_url',
            'ip_address', 'attempt_count', 'max_attempts',
            'created_at', 'updated_at', 'processing_started_at',
            'completed_at', 'expires_at',
            # Calculated fields
            'is_expired', 'can_be_refunded', 'refunded_amount', 'refundable_amount',
            'can_retry', 'time_remaining', 'refunds_summary', 'disputes_summary'
        ]
        read_only_fields = [
            'id', 'reference_number', 'commission', 'total_amount',
            'gateway_transaction_id', 'gateway_payment_id', 'gateway_reference',
            'gateway_error_code', 'gateway_error_message', 'payment_url',
            'attempt_count', 'created_at', 'updated_at', 'processing_started_at',
            'completed_at'
        ]

    def get_is_expired(self, obj):
        """Check if payment is expired"""
        return obj.is_expired()

    def get_can_be_refunded(self, obj):
        """Check if payment can be refunded"""
        return obj.can_be_refunded()

    def get_refunded_amount(self, obj):
        """Get total refunded amount"""
        return float(obj.get_refunded_amount())

    def get_refundable_amount(self, obj):
        """Get amount that can still be refunded"""
        return float(obj.get_refundable_amount())

    def get_can_retry(self, obj):
        """Check if payment can be retried"""
        return obj.can_retry()

    def get_time_remaining(self, obj):
        """Get time remaining until expiration"""
        if obj.expires_at:
            from django.utils import timezone
            remaining = obj.expires_at - timezone.now()
            if remaining.total_seconds() > 0:
                return {
                    'seconds': int(remaining.total_seconds()),
                    'minutes': int(remaining.total_seconds() / 60),
                    'formatted': f"{int(remaining.total_seconds() / 60)}m {int(remaining.total_seconds() % 60)}s"
                }
        return None

    def get_refunds_summary(self, obj):
        """Get refunds summary"""
        refunds = obj.refunds.all()
        if not refunds:
            return None

        return {
            'count': refunds.count(),
            'total_amount': float(sum(r.amount for r in refunds if r.status == 'completed')),
            'pending_count': refunds.filter(status='pending').count(),
            'completed_count': refunds.filter(status='completed').count(),
            'latest_refund': {
                'id': str(refunds.first().id),
                'amount': float(refunds.first().amount),
                'status': refunds.first().status,
                'created_at': refunds.first().created_at.isoformat()
            } if refunds.exists() else None
        }

    def get_disputes_summary(self, obj):
        """Get disputes summary"""
        disputes = obj.disputes.all()
        if not disputes:
            return None

        return {
            'count': disputes.count(),
            'active_count': disputes.exclude(status__in=['won', 'lost', 'closed']).count(),
            'latest_dispute': {
                'id': str(disputes.first().id),
                'dispute_id': disputes.first().dispute_id,
                'status': disputes.first().status,
                'amount': float(disputes.first().amount),
                'created_at': disputes.first().created_at.isoformat()
            } if disputes.exists() else None
        }


class PaymentListSerializer(serializers.ModelSerializer):
    """Lightweight payment serializer for list views"""

    gateway_name = serializers.CharField(source='gateway.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'reference_number', 'gateway_name', 'payment_type_display',
            'amount', 'total_amount', 'currency', 'status', 'status_display',
            'is_expired', 'created_at', 'expires_at'
        ]

    def get_is_expired(self, obj):
        return obj.is_expired()


class CreatePaymentSerializer(serializers.Serializer):
    """Create payment request serializer with validation"""

    gateway = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    payment_type = serializers.ChoiceField(
        choices=Payment.PAYMENT_TYPES,
        default='wallet_topup'
    )
    payment_method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHODS,
        default='card'
    )
    currency = serializers.CharField(max_length=3, default='UZS')
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    # URL fields
    success_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    cancel_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    callback_url = serializers.URLField(required=False, allow_blank=True, max_length=500)

    # Optional fields
    metadata = serializers.JSONField(required=False, default=dict)
    saved_payment_method_id = serializers.UUIDField(required=False, allow_null=True)
    save_payment_method = serializers.BooleanField(default=False)

    def validate_gateway(self, value):
        """Validate gateway exists and is active"""
        try:
            gateway = PaymentGateway.objects.get(name=value, is_active=True)
            return value
        except PaymentGateway.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive payment gateway")

    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate amount against gateway limits
        try:
            gateway = PaymentGateway.objects.get(name=attrs['gateway'], is_active=True)
            if not gateway.is_amount_valid(attrs['amount']):
                raise serializers.ValidationError({
                    'amount': f"Amount must be between {gateway.min_amount} and {gateway.max_amount} {gateway.default_currency}"
                })

            # Validate currency is supported
            if attrs.get('currency') and attrs['currency'] not in gateway.supported_currencies:
                if gateway.supported_currencies:  # Only validate if gateway has currency restrictions
                    raise serializers.ValidationError({
                        'currency': f"Currency {attrs['currency']} not supported by {gateway.display_name}"
                    })
        except PaymentGateway.DoesNotExist:
            pass  # Will be caught by gateway validation

        return attrs


class PaymentEstimateSerializer(serializers.Serializer):
    """Payment cost estimation serializer"""

    gateway = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    currency = serializers.CharField(max_length=3, default='UZS')

    def validate_gateway(self, value):
        """Validate gateway exists and is active"""
        try:
            PaymentGateway.objects.get(name=value, is_active=True)
            return value
        except PaymentGateway.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive payment gateway")


class PaymentEstimateResponseSerializer(serializers.Serializer):
    """Payment estimate response serializer"""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    gateway = serializers.CharField()
    gateway_display_name = serializers.CharField()
    commission_type = serializers.CharField()
    commission_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    commission_fixed = serializers.DecimalField(max_digits=10, decimal_places=2)
    processing_time_minutes = serializers.IntegerField()


class ClickTransactionSerializer(serializers.ModelSerializer):
    """Click transaction serializer"""

    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=12, decimal_places=2, read_only=True)
    payment_status = serializers.CharField(source='payment.status', read_only=True)
    payment_reference = serializers.CharField(source='payment.reference_number', read_only=True)
    error_description = serializers.SerializerMethodField()

    class Meta:
        model = ClickTransaction
        fields = [
            'click_trans_id', 'click_paydoc_id', 'merchant_trans_id',
            'service_id', 'merchant_prepare_id', 'merchant_confirm_id',
            'sign_time', 'error_code', 'error_note', 'error_description',
            'card_type', 'card_number_masked', 'payment_amount',
            'payment_status', 'payment_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_error_description(self, obj):
        """Get human-readable error description"""
        error_codes = {
            0: 'Success',
            -1: 'Invalid signature',
            -2: 'Invalid amount',
            -3: 'Transaction not found',
            -4: 'Transaction already exists',
            -5: 'Invalid parameters',
            -6: 'Service unavailable',
            -7: 'Transaction cancelled',
            -8: 'Transaction timeout',
            -9: 'Internal error'
        }
        return error_codes.get(obj.error_code, f'Unknown error ({obj.error_code})')


class PaymeTransactionSerializer(serializers.ModelSerializer):
    """Payme transaction serializer"""

    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=12, decimal_places=2, read_only=True)
    payment_status = serializers.CharField(source='payment.status', read_only=True)
    payment_reference = serializers.CharField(source='payment.reference_number', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    # Datetime fields
    payme_time_datetime = serializers.SerializerMethodField()
    create_time_datetime = serializers.SerializerMethodField()
    perform_time_datetime = serializers.SerializerMethodField()
    cancel_time_datetime = serializers.SerializerMethodField()

    class Meta:
        model = PaymeTransaction
        fields = [
            'payme_id', 'payme_time', 'payme_time_datetime',
            'create_time', 'create_time_datetime', 'perform_time', 'perform_time_datetime',
            'cancel_time', 'cancel_time_datetime', 'state', 'state_display',
            'reason', 'account', 'receivers', 'extra_data',
            'payment_amount', 'payment_status', 'payment_reference',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_payme_time_datetime(self, obj):
        """Convert Payme time to ISO format"""
        if obj.payme_time:
            return obj.get_payme_time_as_datetime().isoformat() if obj.get_payme_time_as_datetime() else None
        return None

    def get_create_time_datetime(self, obj):
        """Convert create time to ISO format"""
        if obj.create_time:
            return obj.get_create_time_as_datetime().isoformat() if obj.get_create_time_as_datetime() else None
        return None

    def get_perform_time_datetime(self, obj):
        """Convert perform time to ISO format"""
        if obj.perform_time and obj.perform_time > 0:
            from django.utils import timezone
            return timezone.datetime.fromtimestamp(obj.perform_time / 1000).isoformat()
        return None

    def get_cancel_time_datetime(self, obj):
        """Convert cancel time to ISO format"""
        if obj.cancel_time and obj.cancel_time > 0:
            from django.utils import timezone
            return timezone.datetime.fromtimestamp(obj.cancel_time / 1000).isoformat()
        return None


class PaymentRefundSerializer(serializers.ModelSerializer):
    """Payment refund serializer"""

    payment_reference = serializers.CharField(source='payment.reference_number', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=12, decimal_places=2, read_only=True)
    user_name = serializers.CharField(source='payment.user.get_full_name', read_only=True)
    gateway_name = serializers.CharField(source='payment.gateway.display_name', read_only=True)

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    can_be_processed = serializers.SerializerMethodField()
    processing_time = serializers.SerializerMethodField()

    class Meta:
        model = PaymentRefund
        fields = [
            'id', 'payment_reference', 'payment_amount', 'user_name', 'gateway_name',
            'amount', 'currency', 'reason', 'reason_display', 'reason_description',
            'status', 'status_display', 'gateway_refund_id', 'gateway_reference',
            'gateway_error_code', 'gateway_error_message',
            'requested_by_name', 'processed_by_name', 'approved_by_name',
            'internal_notes', 'customer_notes', 'metadata',
            'can_be_processed', 'processing_time',
            'created_at', 'updated_at', 'processed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'gateway_refund_id', 'gateway_reference', 'gateway_error_code',
            'gateway_error_message', 'processed_by_name', 'approved_by_name',
            'created_at', 'updated_at', 'processed_at', 'completed_at'
        ]

    def get_can_be_processed(self, obj):
        """Check if refund can be processed"""
        return obj.can_be_processed()

    def get_processing_time(self, obj):
        """Calculate processing time if completed"""
        if obj.processed_at and obj.created_at:
            delta = obj.processed_at - obj.created_at
            return {
                'seconds': int(delta.total_seconds()),
                'human_readable': f"{delta.days}d {delta.seconds // 3600}h {(delta.seconds % 3600) // 60}m"
            }
        return None


class CreateRefundSerializer(serializers.Serializer):
    """Create refund request serializer"""

    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    reason = serializers.ChoiceField(choices=PaymentRefund.REFUND_REASONS)
    reason_description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    customer_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    internal_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_payment_id(self, value):
        """Validate payment exists and can be refunded"""
        try:
            payment = Payment.objects.get(id=value)
            if not payment.can_be_refunded():
                raise serializers.ValidationError("Payment cannot be refunded")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")

    def validate(self, attrs):
        """Validate refund amount"""
        try:
            payment = Payment.objects.get(id=attrs['payment_id'])
            refundable_amount = payment.get_refundable_amount()

            if attrs['amount'] > refundable_amount:
                raise serializers.ValidationError({
                    'amount': f"Maximum refundable amount is {refundable_amount} {payment.currency}"
                })
        except Payment.DoesNotExist:
            pass  # Will be caught by payment_id validation

        return attrs


class PaymentDisputeSerializer(serializers.ModelSerializer):
    """Payment dispute serializer"""

    payment_reference = serializers.CharField(source='payment.reference_number', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=12, decimal_places=2, read_only=True)
    user_name = serializers.CharField(source='payment.user.get_full_name', read_only=True)
    gateway_name = serializers.CharField(source='payment.gateway.display_name', read_only=True)

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.get_full_name', read_only=True)

    time_to_respond = serializers.SerializerMethodField()
    evidence_status = serializers.SerializerMethodField()

    class Meta:
        model = PaymentDispute
        fields = [
            'id', 'dispute_id', 'payment_reference', 'payment_amount',
            'user_name', 'gateway_name', 'amount', 'currency',
            'reason', 'reason_display', 'status', 'status_display',
            'description', 'customer_message', 'response_message',
            'evidence_details', 'evidence_due_by', 'evidence_status',
            'gateway_dispute_id', 'gateway_data', 'handled_by_name',
            'time_to_respond', 'created_at', 'updated_at',
            'responded_at', 'closed_at'
        ]
        read_only_fields = [
            'id', 'dispute_id', 'gateway_dispute_id', 'handled_by_name',
            'created_at', 'updated_at', 'responded_at', 'closed_at'
        ]

    def get_time_to_respond(self, obj):
        """Calculate time remaining to respond"""
        if obj.evidence_due_by and obj.status == 'evidence_required':
            from django.utils import timezone
            remaining = obj.evidence_due_by - timezone.now()
            if remaining.total_seconds() > 0:
                return {
                    'seconds': int(remaining.total_seconds()),
                    'days': remaining.days,
                    'hours': remaining.seconds // 3600,
                    'formatted': f"{remaining.days}d {remaining.seconds // 3600}h"
                }
            else:
                return {'overdue': True, 'days_overdue': abs(remaining.days)}
        return None

    def get_evidence_status(self, obj):
        """Get evidence submission status"""
        evidence_details = obj.evidence_details or {}
        required_evidence = evidence_details.get('required_evidence', [])
        submitted_evidence = evidence_details.get('submitted_evidence', [])

        return {
            'required_count': len(required_evidence),
            'submitted_count': len(submitted_evidence),
            'missing_evidence': list(set(required_evidence) - set(submitted_evidence)),
            'is_complete': set(required_evidence).issubset(set(submitted_evidence))
        }


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Payment webhook serializer for debugging"""

    payment_reference = serializers.CharField(source='payment.reference_number', read_only=True)
    gateway_name = serializers.CharField(source='gateway.display_name', read_only=True)
    webhook_type_display = serializers.CharField(source='get_webhook_type_display', read_only=True)
    processing_time_seconds = serializers.SerializerMethodField()

    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'payment_reference', 'gateway_name', 'webhook_type', 'webhook_type_display',
            'request_method', 'request_headers', 'request_body', 'raw_body',
            'response_status', 'response_data', 'ip_address', 'user_agent',
            'signature_valid', 'processed', 'processing_time_ms', 'processing_time_seconds',
            'processing_result', 'error_message', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']

    def get_processing_time_seconds(self, obj):
        """Convert processing time to seconds"""
        if obj.processing_time_ms:
            return round(obj.processing_time_ms / 1000, 3)
        return None


class PaymentAnalyticsSerializer(serializers.Serializer):
    """Payment analytics serializer"""

    period_days = serializers.IntegerField()
    total_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    cancelled_payments = serializers.IntegerField()

    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_commission = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_refunded = serializers.DecimalField(max_digits=12, decimal_places=2)

    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_processing_time_minutes = serializers.DecimalField(max_digits=8, decimal_places=2)

    top_gateways = serializers.ListField(child=serializers.DictField())
    payment_trends = serializers.ListField(child=serializers.DictField())
    currency_breakdown = serializers.ListField(child=serializers.DictField())


class GatewayStatusSerializer(serializers.Serializer):
    """Gateway status check serializer"""

    gateway = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    available = serializers.BooleanField()
    message = serializers.CharField()
    response_time = serializers.FloatField()
    last_check = serializers.DateTimeField()
    is_test_mode = serializers.BooleanField()


class BulkPaymentActionSerializer(serializers.Serializer):
    """Bulk payment action serializer"""

    payment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=[
        ('cancel', 'Cancel'),
        ('retry', 'Retry'),
        ('refund', 'Refund'),
        ('mark_failed', 'Mark as Failed'),
        ('export', 'Export')
    ])
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_payment_ids(self, value):
        """Validate all payment IDs exist"""
        existing_ids = Payment.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)

        if missing_ids:
            raise serializers.ValidationError(
                f"Payment IDs not found: {', '.join(str(id) for id in missing_ids)}"
            )

        return value


class PaymentSearchSerializer(serializers.Serializer):
    """Payment search and filter serializer"""

    # Text search
    search = serializers.CharField(max_length=255, required=False, allow_blank=True)

    # Filters
    status = serializers.MultipleChoiceField(
        choices=Payment.STATUS_CHOICES,
        required=False,
        allow_empty=True
    )
    payment_type = serializers.MultipleChoiceField(
        choices=Payment.PAYMENT_TYPES,
        required=False,
        allow_empty=True
    )
    gateway = serializers.MultipleChoiceField(
        choices=[],  # Will be populated dynamically
        required=False,
        allow_empty=True
    )
    currency = serializers.MultipleChoiceField(
        choices=[('UZS', 'UZS'), ('USD', 'USD'), ('EUR', 'EUR'), ('RUB', 'RUB')],
        required=False,
        allow_empty=True
    )

    # Amount range
    min_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    max_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True
    )

    # Date range
    date_from = serializers.DateTimeField(required=False, allow_null=True)
    date_to = serializers.DateTimeField(required=False, allow_null=True)

    # User filters
    user_id = serializers.UUIDField(required=False, allow_null=True)
    user_email = serializers.EmailField(required=False, allow_blank=True)

    # Advanced filters
    has_refunds = serializers.BooleanField(required=False, allow_null=True)
    has_disputes = serializers.BooleanField(required=False, allow_null=True)
    is_expired = serializers.BooleanField(required=False, allow_null=True)
    failed_attempts_gte = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    # Sorting
    sort_by = serializers.ChoiceField(
        choices=[
            ('created_at', 'Created Date'),
            ('-created_at', 'Created Date (Desc)'),
            ('amount', 'Amount'),
            ('-amount', 'Amount (Desc)'),
            ('status', 'Status'),
            ('gateway', 'Gateway'),
            ('updated_at', 'Last Updated'),
            ('-updated_at', 'Last Updated (Desc)')
        ],
        default='-created_at',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate gateway choices dynamically
        gateway_choices = [(g.name, g.display_name) for g in PaymentGateway.objects.all()]
        self.fields['gateway'].choices = gateway_choices

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate date range
        if attrs.get('date_from') and attrs.get('date_to'):
            if attrs['date_from'] > attrs['date_to']:
                raise serializers.ValidationError({
                    'date_from': 'Start date must be before end date'
                })

        # Validate amount range
        if attrs.get('min_amount') and attrs.get('max_amount'):
            if attrs['min_amount'] > attrs['max_amount']:
                raise serializers.ValidationError({
                    'min_amount': 'Minimum amount must be less than maximum amount'
                })

        return attrs


class PaymentExportSerializer(serializers.Serializer):
    """Payment export configuration serializer"""

    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
        ('json', 'JSON'),
        ('pdf', 'PDF Report')
    ]

    format = serializers.ChoiceField(choices=FORMAT_CHOICES, default='csv')
    include_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    filters = PaymentSearchSerializer(required=False)

    def validate(self, attrs):
        """Validate export parameters"""
        if attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({
                'date_from': 'Start date must be before end date'
            })

        # Validate date range is not too large
        date_diff = attrs['date_to'] - attrs['date_from']
        if date_diff.days > 365:
            raise serializers.ValidationError(
                'Export date range cannot exceed 365 days'
            )

        return attrs


class PaymentRetrySerializer(serializers.Serializer):
    """Payment retry configuration serializer"""

    payment_id = serializers.UUIDField()
    new_gateway = serializers.CharField(max_length=50, required=False, allow_blank=True)
    update_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal('0.01')
    )
    retry_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_payment_id(self, value):
        """Validate payment can be retried"""
        try:
            payment = Payment.objects.get(id=value)
            if not payment.can_retry():
                raise serializers.ValidationError("Payment cannot be retried")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")

    def validate_new_gateway(self, value):
        """Validate new gateway if provided"""
        if value:
            try:
                PaymentGateway.objects.get(name=value, is_active=True)
                return value
            except PaymentGateway.DoesNotExist:
                raise serializers.ValidationError("Invalid or inactive gateway")
        return value


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for saving payment methods"""

    gateway_name = serializers.CharField(source='gateway.name', write_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'gateway_name', 'method_type', 'nickname', 'is_default',
            'card_type', 'card_holder_name', 'expiry_month', 'expiry_year',
            'bank_name'
        ]

    def validate_gateway_name(self, value):
        """Validate gateway exists and is active"""
        try:
            gateway = PaymentGateway.objects.get(name=value, is_active=True)
            return value
        except PaymentGateway.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive gateway")

    def validate(self, attrs):
        """Validate payment method data"""
        if attrs['method_type'] == 'card':
            required_fields = ['card_holder_name', 'expiry_month', 'expiry_year']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError({
                        field: f'{field} is required for card payment methods'
                    })

            # Validate expiry date
            try:
                month = int(attrs['expiry_month'])
                year = int(attrs['expiry_year'])
                if month < 1 or month > 12:
                    raise serializers.ValidationError({
                        'expiry_month': 'Invalid month'
                    })
                if year < 2024 or year > 2050:
                    raise serializers.ValidationError({
                        'expiry_year': 'Invalid year'
                    })
            except (ValueError, TypeError):
                raise serializers.ValidationError('Invalid expiry date')

        elif attrs['method_type'] == 'bank_account':
            if not attrs.get('bank_name'):
                raise serializers.ValidationError({
                    'bank_name': 'Bank name is required for bank account payment methods'
                })

        return attrs

    def create(self, validated_data):
        """Create payment method with gateway lookup"""
        gateway_name = validated_data.pop('gateway_name')
        gateway = PaymentGateway.objects.get(name=gateway_name)

        return PaymentMethod.objects.create(
            gateway=gateway,
            user=self.context['request'].user,
            **validated_data
        )


class PaymentStatisticsSerializer(serializers.Serializer):
    """Payment statistics summary serializer"""

    # Period info
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()

    # Payment counts
    total_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()

    # Amounts
    total_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    successful_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_payment_size = serializers.DecimalField(max_digits=12, decimal_places=2)

    # Rates
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    failure_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Refunds
    total_refunds = serializers.IntegerField()
    refunded_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    refund_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Disputes
    total_disputes = serializers.IntegerField()
    dispute_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Gateway breakdown
    gateway_stats = serializers.ListField(child=serializers.DictField())

    # Trends
    daily_trends = serializers.ListField(child=serializers.DictField())
    hourly_distribution = serializers.ListField(child=serializers.DictField())


class PaymentValidationSerializer(serializers.Serializer):
    """Payment validation before processing"""

    user_id = serializers.UUIDField()
    gateway_name = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='UZS')
    payment_type = serializers.ChoiceField(choices=Payment.PAYMENT_TYPES)

    def validate(self, attrs):
        """Comprehensive payment validation"""
        errors = {}

        # Validate user
        try:
            user = User.objects.get(id=attrs['user_id'])
            if not user.is_active:
                errors['user_id'] = 'User account is not active'
        except User.DoesNotExist:
            errors['user_id'] = 'User not found'

        # Validate gateway
        try:
            gateway = PaymentGateway.objects.get(
                name=attrs['gateway_name'],
                is_active=True
            )

            # Check amount limits
            if not gateway.is_amount_valid(attrs['amount']):
                errors['amount'] = (
                    f'Amount must be between {gateway.min_amount} and '
                    f'{gateway.max_amount} {gateway.default_currency}'
                )

            # Check currency support
            if (gateway.supported_currencies and
                    attrs['currency'] not in gateway.supported_currencies):
                errors['currency'] = f'Currency {attrs["currency"]} not supported'

        except PaymentGateway.DoesNotExist:
            errors['gateway_name'] = 'Gateway not found or inactive'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


# Utility serializers for API responses
class SuccessResponseSerializer(serializers.Serializer):
    """Standard success response serializer"""
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = serializers.JSONField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    """Standard error response serializer"""
    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    error_code = serializers.CharField(required=False)
    details = serializers.JSONField(required=False)


class PaginatedResponseSerializer(serializers.Serializer):
    """Paginated response serializer"""
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField()


# Custom field serializers
class CurrencyField(serializers.DecimalField):
    """Custom currency field with proper formatting"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_digits', 12)
        kwargs.setdefault('decimal_places', 2)
        super().__init__(**kwargs)

    def to_representation(self, value):
        """Format currency for display"""
        if value is None:
            return None

        # Format with thousand separators
        formatted = f"{float(value):,.2f}"
        return formatted


class TimestampField(serializers.DateTimeField):
    """Custom timestamp field with multiple format support"""

    def to_representation(self, value):
        """Return timestamp in multiple formats"""
        if value is None:
            return None

        return {
            'iso': value.isoformat(),
            'timestamp': int(value.timestamp()),
            'formatted': value.strftime('%Y-%m-%d %H:%M:%S'),
            'relative': self.get_relative_time(value)
        }

    def get_relative_time(self, value):
        """Get relative time description"""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - value

        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            return f'{diff.seconds // 60} minutes ago'
        elif diff < timedelta(days=1):
            return f'{diff.seconds // 3600} hours ago'
        elif diff < timedelta(days=30):
            return f'{diff.days} days ago'
        else:
            return value.strftime('%B %d, %Y')


# Webhook-specific serializers for external integrations
class WebhookPaymentDataSerializer(serializers.Serializer):
    """Payment data for webhook notifications"""

    id = serializers.UUIDField()
    reference_number = serializers.CharField()
    amount = CurrencyField()
    currency = serializers.CharField()
    status = serializers.CharField()
    gateway = serializers.CharField()
    user_id = serializers.UUIDField()
    created_at = TimestampField()
    completed_at = TimestampField(allow_null=True)

    # Additional context
    payment_type = serializers.CharField()
    metadata = serializers.JSONField()


class WebhookNotificationSerializer(serializers.Serializer):
    """Webhook notification payload serializer"""

    event_type = serializers.ChoiceField(choices=[
        ('payment.created', 'Payment Created'),
        ('payment.completed', 'Payment Completed'),
        ('payment.failed', 'Payment Failed'),
        ('payment.cancelled', 'Payment Cancelled'),
        ('refund.created', 'Refund Created'),
        ('refund.completed', 'Refund Completed'),
        ('dispute.created', 'Dispute Created'),
    ])

    timestamp = serializers.DateTimeField()
    api_version = serializers.CharField(default='3.0')

    # Event data
    data = WebhookPaymentDataSerializer()

    # Security
    signature = serializers.CharField()
    webhook_id = serializers.CharField()


# Admin-specific serializers
class AdminPaymentOverviewSerializer(serializers.Serializer):
    """Admin payment overview with enhanced data"""

    payment = PaymentSerializer()

    # Enhanced admin data
    risk_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    fraud_indicators = serializers.ListField(child=serializers.CharField(), default=list)
    related_payments = serializers.IntegerField()
    user_payment_history = serializers.DictField()

    # Technical details
    processing_logs = serializers.ListField(child=serializers.DictField())
    api_calls = serializers.ListField(child=serializers.DictField())

    # Financial details
    net_amount = CurrencyField()  # Amount minus commission
    platform_fee = CurrencyField()
    gateway_fee = CurrencyField()


print("🚀 Payment serializers loaded with comprehensive functionality!")
print("📊 Features: Detailed validation, rich data, export support, admin tools")
print("🔒 Security: Input validation, error handling, sensitive data protection")
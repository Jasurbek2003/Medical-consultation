from rest_framework import serializers
from .models import (
    UserWallet, WalletTransaction, BillingRule,
    DoctorViewCharge, BillingSettings
)


class UserWalletSerializer(serializers.ModelSerializer):
    """User wallet serializer"""

    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = UserWallet
        fields = [
            'balance', 'total_spent', 'total_topped_up',
            'is_blocked', 'user_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_spent', 'total_topped_up', 'created_at', 'updated_at'
        ]


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Wallet transaction serializer"""

    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display',
            'amount', 'balance_before', 'balance_after',
            'description', 'status', 'status_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BillingRuleSerializer(serializers.ModelSerializer):
    """Billing rule serializer"""

    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)

    class Meta:
        model = BillingRule
        fields = [
            'service_type', 'service_type_display', 'price',
            'is_active', 'description', 'discount_percentage',
            'min_quantity_for_discount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        """Add effective price calculation"""
        data = super().to_representation(instance)
        data['effective_price'] = instance.get_effective_price()
        data['effective_price_bulk'] = instance.get_effective_price(
            instance.min_quantity_for_discount
        ) if instance.min_quantity_for_discount > 1 else None
        return data


class DoctorViewChargeSerializer(serializers.ModelSerializer):
    """Doctor view charge serializer"""

    doctor_name = serializers.CharField(source='doctor.get_short_name', read_only=True)
    doctor_specialty = serializers.CharField(source='doctor.specialty', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = DoctorViewCharge
        fields = [
            'id', 'doctor_name', 'doctor_specialty', 'user_name',
            'amount_charged', 'view_duration', 'ip_address',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BillingSettingsSerializer(serializers.ModelSerializer):
    """Billing settings serializer"""

    class Meta:
        model = BillingSettings
        fields = [
            'free_views_per_day', 'free_views_for_new_users',
            'min_wallet_topup', 'max_wallet_balance',
            'enable_billing', 'maintenance_mode',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BillingStatsSerializer(serializers.Serializer):
    """Billing statistics serializer"""

    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_topped_up = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_spending = serializers.DecimalField(max_digits=12, decimal_places=2)
    month_spending = serializers.DecimalField(max_digits=12, decimal_places=2)
    doctor_views_today = serializers.IntegerField()
    free_views_used_today = serializers.IntegerField()
    free_views_remaining = serializers.IntegerField()


class ChargeServiceSerializer(serializers.Serializer):
    """Charge service request serializer"""

    service_type = serializers.ChoiceField(choices=BillingRule.SERVICE_TYPES)
    object_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value


class CheckBalanceSerializer(serializers.Serializer):
    """Check balance request serializer"""

    service_type = serializers.ChoiceField(choices=BillingRule.SERVICE_TYPES)
    quantity = serializers.IntegerField(default=1, min_value=1)


class DailyUsageSerializer(serializers.Serializer):
    """Daily usage statistics serializer"""

    free_views_used = serializers.IntegerField()
    free_views_remaining = serializers.IntegerField()
    paid_views = serializers.IntegerField()
    total_views = serializers.IntegerField()
    spending_today = serializers.DecimalField(max_digits=10, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
"""
Payment and Billing Integration Services
Connects payment processing with wallet and billing systems
"""

from decimal import Decimal
from django.db import transaction, models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.billing.models import UserWallet, WalletTransaction, BillingRule, DoctorViewCharge, BillingSettings
from .models import Payment, PaymentGateway

User = get_user_model()


class WalletService:
    """Service for wallet operations"""

    @staticmethod
    def get_or_create_wallet(user):
        """Get or create wallet for user"""
        wallet, created = UserWallet.objects.get_or_create(user=user)
        return wallet

    @staticmethod
    def check_balance(user, amount):
        """Check if user has sufficient balance"""
        try:
            wallet = WalletService.get_or_create_wallet(user)
            return wallet.has_sufficient_balance(amount)
        except Exception:
            return False

    @staticmethod
    def deduct_balance(user, amount, description="", related_object=None):
        """Deduct amount from user wallet"""
        with transaction.atomic():
            wallet = WalletService.get_or_create_wallet(user)

            if not wallet.has_sufficient_balance(amount):
                raise ValidationError(f"Insufficient balance. Available: {wallet.balance}, Required: {amount}")

            # Store balance before deduction
            balance_before = wallet.balance

            # Deduct balance
            wallet.balance -= amount
            wallet.total_spent += amount
            wallet.save()

            # Create transaction record
            wallet_transaction = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='debit',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status='completed'
            )

            # Link to related object if provided
            if related_object:
                from django.contrib.contenttypes.models import ContentType
                content_type = ContentType.objects.get_for_model(related_object)
                wallet_transaction.content_type = content_type
                wallet_transaction.object_id = related_object.pk
                wallet_transaction.save()

            return wallet_transaction

    @staticmethod
    def add_balance(user, amount, description="", related_object=None):
        """Add amount to user wallet"""
        with transaction.atomic():
            wallet = WalletService.get_or_create_wallet(user)

            # Store balance before addition
            balance_before = wallet.balance

            # Add balance
            wallet.balance += amount
            wallet.total_topped_up += amount
            wallet.save()

            # Create transaction record
            wallet_transaction = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='credit',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status='completed'
            )

            # Link to related object if provided
            if related_object:
                from django.contrib.contenttypes.models import ContentType
                content_type = ContentType.objects.get_for_model(related_object)
                wallet_transaction.content_type = content_type
                wallet_transaction.object_id = related_object.pk
                wallet_transaction.save()

            return wallet_transaction

    @staticmethod
    def get_wallet_info(user):
        """Get comprehensive wallet information"""
        wallet = WalletService.get_or_create_wallet(user)

        # Get recent transactions
        recent_transactions = wallet.transactions.filter(
            status='completed'
        ).order_by('-created_at')[:10]

        # Get today's spending
        today = timezone.now().date()
        today_spending = wallet.transactions.filter(
            transaction_type='debit',
            status='completed',
            created_at__date=today
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        # Get billing settings
        billing_settings = BillingSettings.get_settings()

        return {
            'balance': wallet.balance,
            'total_spent': wallet.total_spent,
            'total_topped_up': wallet.total_topped_up,
            'is_blocked': wallet.is_blocked,
            'today_spending': today_spending,
            'recent_transactions': recent_transactions,
            'billing_settings': billing_settings
        }


class BillingService:
    """Service for billing operations"""

    @staticmethod
    def get_service_price(service_type, quantity=1):
        """Get price for a service"""
        try:
            billing_rule = BillingRule.objects.get(
                service_type=service_type,
                is_active=True
            )
            return billing_rule.get_effective_price(quantity)
        except BillingRule.DoesNotExist:
            return Decimal('0.00')

    @staticmethod
    def can_access_service(user, service_type, quantity=1):
        """Check if user can access a service"""
        billing_settings = BillingSettings.get_settings()

        if not billing_settings.enable_billing:
            return True, "Billing disabled"

        if billing_settings.maintenance_mode:
            return False, "System under maintenance"

        # Special handling for doctor view
        if service_type == 'doctor_view':
            return BillingService._can_view_doctor(user)

        # Check wallet balance for other services
        price = BillingService.get_service_price(service_type, quantity)
        if price > 0:
            has_balance = WalletService.check_balance(user, price)
            if not has_balance:
                return False, f"Insufficient balance. Required: {price}"

        return True, "Access granted"

    @staticmethod
    def _can_view_doctor(user):
        """Check if user can view doctor profile"""
        billing_settings = BillingSettings.get_settings()
        today = timezone.now().date()

        # Count today's doctor views
        today_views = DoctorViewCharge.objects.filter(
            user=user,
            created_at__date=today
        ).count()

        # Check if user has free views remaining
        if today_views < billing_settings.free_views_per_day:
            return True, f"Free view remaining ({billing_settings.free_views_per_day - today_views} left)"

        # Check if new user has free views
        user_age_days = (timezone.now().date() - user.created_at.date()).days
        if user_age_days <= 7:  # New user (7 days)
            total_views = DoctorViewCharge.objects.filter(user=user).count()
            if total_views < billing_settings.free_views_for_new_users:
                return True, f"New user free view ({billing_settings.free_views_for_new_users - total_views} left)"

        # Check wallet balance
        price = BillingService.get_service_price('doctor_view')
        if price > 0:
            has_balance = WalletService.check_balance(user, price)
            if not has_balance:
                return False, f"Insufficient balance. Required: {price}"

        return True, "Access granted with charge"

    @staticmethod
    def charge_for_service(user, service_type, quantity=1, related_object=None, **kwargs):
        """Charge user for a service"""
        billing_settings = BillingSettings.get_settings()

        if not billing_settings.enable_billing:
            return None  # No charging when billing is disabled

        price = BillingService.get_service_price(service_type, quantity)
        if price <= 0:
            return None  # Free service

        # Check access
        can_access, message = BillingService.can_access_service(user, service_type, quantity)
        if not can_access:
            raise ValidationError(message)

        # Special handling for doctor view
        if service_type == 'doctor_view':
            return BillingService._charge_doctor_view(user, related_object, price, **kwargs)

        # Regular service charging
        description = f"{service_type.replace('_', ' ').title()}"
        if quantity > 1:
            description += f" (x{quantity})"

        wallet_transaction = WalletService.deduct_balance(
            user=user,
            amount=price * quantity,
            description=description,
            related_object=related_object
        )

        return wallet_transaction

    @staticmethod
    def _charge_doctor_view(user, doctor, price, **kwargs):
        """Charge for doctor view with specific tracking"""
        with transaction.atomic():
            # Check if this is a free view
            can_access, message = BillingService._can_view_doctor(user)
            if not can_access:
                raise ValidationError(message)

            # If it's a free view, don't charge
            if "free" in message.lower():
                # Create a free view record
                charge = DoctorViewCharge.objects.create(
                    user=user,
                    doctor=doctor,
                    amount_charged=Decimal('0.00'),
                    ip_address=kwargs.get('ip_address'),
                    user_agent=kwargs.get('user_agent', '')
                )
                return None

            # Charge for the view
            wallet_transaction = WalletService.deduct_balance(
                user=user,
                amount=price,
                description=f"Shifokor profilini ko'rish - {doctor.get_short_name()}",
                related_object=doctor
            )

            # Create charge record
            charge = DoctorViewCharge.objects.create(
                user=user,
                doctor=doctor,
                transaction=wallet_transaction,
                amount_charged=price,
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent', '')
            )

            return wallet_transaction


class PaymentBillingIntegration:
    """Integration between payment and billing systems"""

    @staticmethod
    def process_wallet_topup_payment(payment):
        """Process completed wallet topup payment"""
        if payment.status != 'completed' or payment.payment_type != 'wallet_topup':
            return False

        try:
            wallet_transaction = WalletService.add_balance(
                user=payment.user,
                amount=payment.amount,
                description=f"Hamyon to'ldirish - {payment.gateway.display_name} - {payment.reference_number}",
                related_object=payment
            )
            return wallet_transaction
        except Exception as e:
            import logging
            logger = logging.getLogger('apps.payments.billing')
            logger.error(f"Failed to process wallet topup for payment {payment.reference_number}: {str(e)}")
            return False

    @staticmethod
    def create_wallet_topup_payment(user, amount, gateway_name, **kwargs):
        """Create a payment for wallet topup"""
        try:
            gateway = PaymentGateway.objects.get(name=gateway_name, is_active=True)

            # Validate amount
            billing_settings = BillingSettings.get_settings()
            if amount < billing_settings.min_wallet_topup:
                raise ValidationError(f"Minimum topup amount is {billing_settings.min_wallet_topup}")

            # Check wallet balance limit
            wallet = WalletService.get_or_create_wallet(user)
            if wallet.balance + amount > billing_settings.max_wallet_balance:
                raise ValidationError(f"Wallet balance would exceed maximum limit of {billing_settings.max_wallet_balance}")

            # Create payment
            from .models import PaymentProcessor
            payment = PaymentProcessor.create_payment(
                user=user,
                gateway=gateway,
                amount=amount,
                payment_type='wallet_topup',
                description=f"Hamyon to'ldirish - {amount} so'm",
                **kwargs
            )

            return payment

        except Exception as e:
            raise ValidationError(f"Failed to create topup payment: {str(e)}")

    @staticmethod
    def get_user_billing_summary(user, days=30):
        """Get user billing summary"""
        from django.utils import timezone
        from django.db.models import Sum, Count
        from datetime import timedelta

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        wallet = WalletService.get_or_create_wallet(user)

        # Get transaction summaries
        transactions = wallet.transactions.filter(
            created_at__gte=start_date,
            status='completed'
        )

        credit_summary = transactions.filter(transaction_type='credit').aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        debit_summary = transactions.filter(transaction_type='debit').aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        # Get payment summaries
        payments = Payment.objects.filter(
            user=user,
            created_at__gte=start_date
        )

        payment_summary = {
            'total_payments': payments.count(),
            'completed_payments': payments.filter(status='completed').count(),
            'total_amount': payments.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'pending_payments': payments.filter(status='pending').count(),
            'failed_payments': payments.filter(status='failed').count(),
        }

        # Get service usage
        doctor_views = DoctorViewCharge.objects.filter(
            user=user,
            created_at__gte=start_date
        )

        service_summary = {
            'doctor_views': doctor_views.count(),
            'doctor_view_charges': doctor_views.exclude(
                amount_charged=Decimal('0.00')
            ).aggregate(total=Sum('amount_charged'))['total'] or Decimal('0.00'),
            'free_doctor_views': doctor_views.filter(
                amount_charged=Decimal('0.00')
            ).count(),
        }

        return {
            'period_days': days,
            'wallet_info': {
                'current_balance': wallet.balance,
                'total_credited': credit_summary['total'] or Decimal('0.00'),
                'total_debited': debit_summary['total'] or Decimal('0.00'),
                'credit_transactions': credit_summary['count'] or 0,
                'debit_transactions': debit_summary['count'] or 0,
            },
            'payment_summary': payment_summary,
            'service_summary': service_summary,
            'net_change': (credit_summary['total'] or Decimal('0.00')) - (debit_summary['total'] or Decimal('0.00'))
        }


# Utility functions for quick access
def check_user_balance(user, amount):
    """Quick check if user has sufficient balance"""
    return WalletService.check_balance(user, amount)


def charge_user(user, service_type, **kwargs):
    """Quick charge user for a service"""
    return BillingService.charge_for_service(user, service_type, **kwargs)


def topup_wallet(user, amount):
    """Quick wallet topup"""
    return WalletService.add_balance(user, amount, "Manual topup")


def get_service_price(service_type):
    """Quick get service price"""
    return BillingService.get_service_price(service_type)


print("🚀 Payment-Billing integration loaded successfully!")
print("💰 Features: Wallet management, service charging, payment processing")
print("🔄 Integration: Payment completion, billing rules, transaction tracking")
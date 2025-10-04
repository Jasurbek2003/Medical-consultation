from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import timedelta

from .models import (
    UserWallet, BillingRule, DoctorViewCharge,
    BillingSettings, WalletTransaction
)
from apps.doctors.models import ChargeLog

User = get_user_model()


class BillingService:
    """Core billing service for handling billing logic"""

    @staticmethod
    def get_daily_free_views_used(user):
        """Get number of free views used today by user"""
        today = timezone.now().date()

        # Count free views (stored as special transactions)
        free_views = WalletTransaction.objects.filter(
            wallet__user=user,
            created_at__date=today,
            description__icontains='free view'
        ).count()

        return free_views

    @staticmethod
    def record_free_view(user, doctor_id):
        """Record a free view usage"""
        wallet, created = UserWallet.objects.get_or_create(user=user)

        # Create a zero-amount transaction to track free usage
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='debit',
            amount=Decimal('0.00'),
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            description=f'Free view - Doctor ID: {doctor_id}',
            status='completed'
        )

    @staticmethod
    def can_user_access_service(user, service_type, object_id=None):
        """Check if user can access a service (free or paid)"""
        settings = BillingSettings.get_settings()

        # Check if billing is disabled
        if not settings.enable_billing:
            return {
                'can_access': True,
                'reason': 'billing_disabled',
                'charge_required': False
            }

        # Check maintenance mode
        if settings.maintenance_mode:
            return {
                'can_access': False,
                'reason': 'maintenance_mode',
                'charge_required': False
            }

        # Special handling for doctor views
        if service_type == 'doctor_view' and object_id:
            return BillingService._check_doctor_view_access(user, object_id, settings)

        # Check for other services
        try:
            billing_rule = BillingRule.objects.get(
                service_type=service_type,
                is_active=True
            )

            wallet, created = UserWallet.objects.get_or_create(user=user)
            required_amount = billing_rule.get_effective_price()

            if wallet.has_sufficient_balance(required_amount):
                return {
                    'can_access': True,
                    'reason': 'sufficient_balance',
                    'charge_required': True,
                    'required_amount': required_amount
                }
            else:
                return {
                    'can_access': False,
                    'reason': 'insufficient_balance',
                    'charge_required': True,
                    'required_amount': required_amount,
                    'current_balance': wallet.balance
                }

        except BillingRule.DoesNotExist:
            return {
                'can_access': False,
                'reason': 'billing_rule_not_found',
                'charge_required': False
            }

    @staticmethod
    def _check_doctor_view_access(user, doctor_id, settings):
        """Check doctor view access specifically"""
        today = timezone.now().date()

        # Check if already viewed today
        already_viewed = DoctorViewCharge.objects.filter(
            user=user,
            doctor_id=doctor_id,
            created_at__date=today
        ).exists()

        if already_viewed:
            return {
                'can_access': True,
                'reason': 'already_viewed_today',
                'charge_required': False
            }

        # Check free views
        free_views_used = BillingService.get_daily_free_views_used(user)
        if free_views_used < settings.free_views_per_day:
            return {
                'can_access': True,
                'reason': 'free_view_available',
                'charge_required': False,
                'free_views_used': free_views_used,
                'free_views_total': settings.free_views_per_day
            }

        # Check paid access
        try:
            billing_rule = BillingRule.objects.get(
                service_type='doctor_view',
                is_active=True
            )

            wallet, created = UserWallet.objects.get_or_create(user=user)
            required_amount = billing_rule.get_effective_price()

            return {
                'can_access': wallet.has_sufficient_balance(required_amount),
                'reason': 'payment_required',
                'charge_required': True,
                'required_amount': required_amount,
                'current_balance': wallet.balance
            }

        except BillingRule.DoesNotExist:
            return {
                'can_access': False,
                'reason': 'billing_rule_not_found',
                'charge_required': False
            }

    @staticmethod
    def charge_for_service(user, service_type, object_id=None, quantity=1):
        """Charge user for a service"""
        try:
            billing_rule = BillingRule.objects.get(
                service_type=service_type,
                is_active=True
            )

            wallet, created = UserWallet.objects.get_or_create(user=user)

            # Calculate total amount
            price_per_unit = billing_rule.get_effective_price(quantity)
            total_amount = price_per_unit * quantity

            # Check balance
            if not wallet.has_sufficient_balance(total_amount):
                raise ValueError("Insufficient balance")

            # Deduct amount
            description = f"{billing_rule.get_service_type_display()}"
            if object_id:
                description += f" (ID: {object_id})"
            if quantity > 1:
                description += f" x{quantity}"

            wallet.deduct_balance(total_amount, description)

            return {
                'success': True,
                'amount_charged': total_amount,
                'new_balance': wallet.balance,
                'transaction_id': wallet.transactions.first().id
            }

        except BillingRule.DoesNotExist:
            raise ValueError("Billing rule not found")

    @staticmethod
    def get_user_billing_summary(user, days=30):
        """Get user's billing summary for specified period"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        wallet, created = UserWallet.objects.get_or_create(user=user)

        # Get transactions in period
        transactions = wallet.transactions.filter(
            created_at__date__range=[start_date, end_date]
        )

        # Calculate totals
        total_spent = transactions.filter(
            transaction_type='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_topped_up = transactions.filter(
            transaction_type='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Service breakdown
        service_breakdown = {}
        for service_type, display_name in BillingRule.SERVICE_TYPES:
            service_transactions = transactions.filter(
                transaction_type='debit',
                description__icontains=display_name
            )

            service_breakdown[service_type] = {
                'count': service_transactions.count(),
                'total_amount': service_transactions.aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0.00'),
                'display_name': display_name
            }

        # Daily usage stats
        today = timezone.now().date()
        today_spending = transactions.filter(
            created_at__date=today,
            transaction_type='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Free views
        settings = BillingSettings.get_settings()
        free_views_used = BillingService.get_daily_free_views_used(user)

        return {
            'period_days': days,
            'current_balance': wallet.balance,
            'total_spent': total_spent,
            'total_topped_up': total_topped_up,
            'today_spending': today_spending,
            'service_breakdown': service_breakdown,
            'free_views_used_today': free_views_used,
            'free_views_remaining': max(0, settings.free_views_per_day - free_views_used),
            'wallet_created': wallet.created_at,
            'is_blocked': wallet.is_blocked
        }

    @staticmethod
    def get_billing_analytics(days=30):
        """Get billing analytics for admin dashboard"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Total revenue
        total_revenue = WalletTransaction.objects.filter(
            created_at__gte=start_date,
            transaction_type='debit',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Active users with transactions
        active_users = WalletTransaction.objects.filter(
            created_at__gte=start_date
        ).values('wallet__user').distinct().count()

        # Service usage statistics
        service_stats = {}
        for service_type, display_name in BillingRule.SERVICE_TYPES:
            transactions = WalletTransaction.objects.filter(
                created_at__gte=start_date,
                transaction_type='debit',
                description__icontains=display_name
            )

            service_stats[service_type] = {
                'transaction_count': transactions.count(),
                'total_revenue': transactions.aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0.00'),
                'unique_users': transactions.values(
                    'wallet__user'
                ).distinct().count(),
                'display_name': display_name
            }

        # Top spending users
        top_users = WalletTransaction.objects.filter(
            created_at__gte=start_date,
            transaction_type='debit'
        ).values(
            'wallet__user__id',
            'wallet__user__first_name',
            'wallet__user__last_name'
        ).annotate(
            total_spent=Sum('amount')
        ).order_by('-total_spent')[:10]

        return {
            'period_days': days,
            'total_revenue': total_revenue,
            'active_users': active_users,
            'service_stats': service_stats,
            'top_users': list(top_users),
            'generated_at': timezone.now()
        }

    @staticmethod
    def process_refund(payment_id, amount, reason, processed_by=None):
        """Process a refund for a payment"""
        from apps.payments.models import Payment, PaymentRefund

        try:
            payment = Payment.objects.get(
                id=payment_id,
                status='completed'
            )

            # Create refund record
            refund = PaymentRefund.objects.create(
                payment=payment,
                amount=amount,
                reason=reason,
                processed_by=processed_by
            )

            # Process the refund
            refund.process_refund(processed_by)

            return {
                'success': True,
                'refund_id': refund.id,
                'amount': amount,
                'message': 'Refund processed successfully'
            }

        except Payment.DoesNotExist:
            raise ValueError("Payment not found or not eligible for refund")

    @staticmethod
    def validate_wallet_topup(user, amount):
        """Validate wallet top-up amount"""
        settings = BillingSettings.get_settings()

        if amount < settings.min_wallet_topup:
            raise ValueError(
                f"Minimum top-up amount is {settings.min_wallet_topup} som"
            )

        wallet, created = UserWallet.objects.get_or_create(user=user)

        if wallet.balance + amount > settings.max_wallet_balance:
            raise ValueError(
                f"Maximum wallet balance is {settings.max_wallet_balance} som"
            )

        if wallet.is_blocked:
            raise ValueError("Wallet is blocked")

        return True


def charge_user_for_service(user, doctor, charge_type, amount, metadata=None):
    """
    Charge user for doctor-related services (search, view card, view phone)

    Args:
        user: User object to charge
        doctor: Doctor object providing the service
        charge_type: Type of charge ('search', 'view_card', 'view_phone')
        amount: Amount to charge (Decimal)
        metadata: Optional dict with additional information

    Returns:
        bool: True if charge successful, False otherwise
    """
    try:
        # Get or create user wallet
        wallet, created = UserWallet.objects.get_or_create(user=user)

        # Check if wallet is blocked
        if wallet.is_blocked:
            return False

        # Check sufficient balance
        if not wallet.has_sufficient_balance(amount):
            return False

        # Deduct balance
        description = f"{dict(ChargeLog.CHARGE_TYPES).get(charge_type, 'Service')} - Dr. {doctor.full_name}"
        wallet.deduct_balance(amount, description)

        # Create charge log
        from apps.core.utils import get_client_ip
        ChargeLog.objects.create(
            doctor=doctor,
            charge_type=charge_type,
            amount=amount,
            user=user,
            ip_address=metadata.get('ip_address', '0.0.0.0') if metadata else '0.0.0.0',
            user_agent=metadata.get('user_agent', '') if metadata else '',
            metadata=metadata or {}
        )

        return True

    except Exception:
        return False
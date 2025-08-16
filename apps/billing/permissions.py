from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal

from .models import (
    UserWallet, BillingRule, BillingSettings,
    DoctorViewCharge, WalletTransaction
)
from .services import BillingService

User = get_user_model()


class BillingPermissionMixin:
    """Mixin for billing-related permission checks"""

    def check_billing_enabled(self):
        """Check if billing system is enabled"""
        settings = BillingSettings.get_settings()
        if not settings.enable_billing:
            return False

        if settings.maintenance_mode:
            return False

        return True

    def check_user_wallet_active(self, user):
        """Check if user's wallet is active and not blocked"""
        try:
            wallet = user.wallet
            return not wallet.is_blocked
        except UserWallet.DoesNotExist:
            return True  # Will be created automatically

    def get_user_daily_usage(self, user):
        """Get user's daily usage statistics"""
        return BillingService.get_daily_free_views_used(user)


class HasSufficientBalance(permissions.BasePermission):
    """Permission to check if user has sufficient balance for a service"""

    message = "Insufficient balance to access this service"

    def has_permission(self, request, view):
        """Check if user has sufficient balance"""
        if not request.user.is_authenticated:
            return False

        # Check if billing is enabled
        settings = BillingSettings.get_settings()
        if not settings.enable_billing:
            return True  # Allow access when billing is disabled

        # Get service type from view or request
        service_type = getattr(view, 'billing_service_type', None)
        if not service_type:
            service_type = request.data.get('service_type')

        if not service_type:
            return True  # No service type specified, let view handle

        try:
            # Get billing rule
            billing_rule = BillingRule.objects.get(
                service_type=service_type,
                is_active=True
            )

            # Get user wallet
            wallet, created = UserWallet.objects.get_or_create(user=request.user)

            # Check if wallet is blocked
            if wallet.is_blocked:
                self.message = "Your wallet is blocked. Please contact support."
                return False

            # Calculate required amount
            quantity = getattr(view, 'billing_quantity', 1)
            required_amount = billing_rule.get_effective_price(quantity) * quantity

            # Check balance
            if not wallet.has_sufficient_balance(required_amount):
                self.message = f"Insufficient balance. Required: {required_amount} so'm, Available: {wallet.balance} so'm"
                return False

            return True

        except BillingRule.DoesNotExist:
            # No billing rule found, allow access
            return True
        except Exception:
            # On any error, deny access for security
            return False


class CanAccessDoctorProfile(permissions.BasePermission):
    """Permission to check if user can access doctor profile"""

    message = "Cannot access doctor profile"

    def has_permission(self, request, view):
        """Check if user can access doctor profile"""
        if not request.user.is_authenticated:
            return False

        # Get doctor ID from URL or request
        doctor_id = view.kwargs.get('doctor_id') or view.kwargs.get('pk')
        if not doctor_id:
            return True  # Let view handle missing ID

        # Check access using billing service
        access_check = BillingService.can_user_access_service(
            request.user,
            'doctor_view',
            doctor_id
        )

        if not access_check['can_access']:
            self.message = access_check.get('reason', 'Access denied')
            return False

        return True


class HasValidWallet(permissions.BasePermission):
    """Permission to check if user has a valid wallet"""

    message = "Invalid or blocked wallet"

    def has_permission(self, request, view):
        """Check if user has a valid wallet"""
        if not request.user.is_authenticated:
            return False

        try:
            wallet = request.user.wallet
            if wallet.is_blocked:
                self.message = "Your wallet is blocked. Please contact support."
                return False
            return True
        except UserWallet.DoesNotExist:
            # Wallet will be created automatically
            return True


class CanPerformWalletAction(permissions.BasePermission):
    """Permission for wallet-related actions"""

    message = "Cannot perform wallet action"

    def has_permission(self, request, view):
        """Check if user can perform wallet actions"""
        if not request.user.is_authenticated:
            return False

        # Check billing settings
        settings = BillingSettings.get_settings()
        if settings.maintenance_mode:
            self.message = "Billing system is under maintenance"
            return False

        # Check wallet status
        try:
            wallet = request.user.wallet
            if wallet.is_blocked:
                self.message = "Your wallet is blocked"
                return False
        except UserWallet.DoesNotExist:
            pass  # Will be created

        return True


class BillingAdminPermission(permissions.BasePermission):
    """Permission for billing administration"""

    message = "Billing admin access required"

    def has_permission(self, request, view):
        """Check if user has billing admin permissions"""
        if not request.user.is_authenticated:
            return False

        # Check if user is staff or has billing admin role
        if request.user.is_superuser:
            return True

        if request.user.is_staff:
            # Check for specific billing permissions
            return request.user.has_perm('billing.change_billingsettings')

        # Check for custom billing admin role
        return hasattr(request.user, 'is_billing_admin') and request.user.is_billing_admin


class CanManageBillingRules(permissions.BasePermission):
    """Permission to manage billing rules"""

    message = "Cannot manage billing rules"

    def has_permission(self, request, view):
        """Check if user can manage billing rules"""
        if not request.user.is_authenticated:
            return False

        # Only superusers and billing admins can manage rules
        if request.user.is_superuser:
            return True

        return (
                request.user.is_staff and
                request.user.has_perm('billing.change_billingrule')
        )


class RateLimitedBillingAccess(permissions.BasePermission):
    """Rate limiting for billing-sensitive operations"""

    message = "Rate limit exceeded"

    def __init__(self, max_requests=10, time_window_minutes=60):
        self.max_requests = max_requests
        self.time_window_minutes = time_window_minutes

    def has_permission(self, request, view):
        """Check rate limiting for billing operations"""
        if not request.user.is_authenticated:
            return False

        # Get time window
        time_threshold = timezone.now() - timezone.timedelta(
            minutes=self.time_window_minutes
        )

        # Count recent billing transactions
        recent_transactions = WalletTransaction.objects.filter(
            wallet__user=request.user,
            created_at__gte=time_threshold,
            transaction_type='debit'
        ).count()

        if recent_transactions >= self.max_requests:
            self.message = f"Too many billing operations. Limit: {self.max_requests} per {self.time_window_minutes} minutes"
            return False

        return True


class DoctorSelfAccessPermission(permissions.BasePermission):
    """Permission for doctors to access their own billing data"""

    message = "Can only access own billing data"

    def has_permission(self, request, view):
        """Check if doctor can access their own billing data"""
        if not request.user.is_authenticated:
            return False

        # Check if user is a doctor
        if not hasattr(request.user, 'doctor_profile'):
            return False

        return request.user.doctor_profile.verification_status == 'approved'

    def has_object_permission(self, request, view, obj):
        """Check if doctor can access specific billing object"""
        # For doctor view charges
        if hasattr(obj, 'doctor'):
            return obj.doctor.user == request.user

        # For general billing records related to doctor
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class HospitalBillingPermission(permissions.BasePermission):
    """Permission for hospital billing management"""

    message = "Hospital billing access required"

    def has_permission(self, request, view):
        """Check if user can access hospital billing"""
        if not request.user.is_authenticated:
            return False

        # Check if user manages a hospital
        if not hasattr(request.user, 'managed_hospital'):
            return False

        return request.user.managed_hospital is not None

    def has_object_permission(self, request, view, obj):
        """Check if user can access specific hospital billing object"""
        hospital = request.user.managed_hospital

        # For doctor-related billing in the hospital
        if hasattr(obj, 'doctor') and hasattr(obj.doctor, 'hospital'):
            return obj.doctor.hospital == hospital

        # For consultations in the hospital
        if hasattr(obj, 'doctor') and hasattr(obj.doctor, 'hospital'):
            return obj.doctor.hospital == hospital

        return False


class FreeViewQuotaPermission(permissions.BasePermission):
    """Permission to check free view quota"""

    message = "Free view quota exceeded"

    def has_permission(self, request, view):
        """Check if user still has free views available"""
        if not request.user.is_authenticated:
            return False

        # Check billing settings
        settings = BillingSettings.get_settings()
        if not settings.enable_billing:
            return True  # Always allow when billing disabled

        # Check free views used today
        free_views_used = BillingService.get_daily_free_views_used(request.user)

        if free_views_used >= settings.free_views_per_day:
            # Check if user has sufficient balance for paid access
            try:
                billing_rule = BillingRule.objects.get(
                    service_type='doctor_view',
                    is_active=True
                )

                wallet, created = UserWallet.objects.get_or_create(user=request.user)
                required_amount = billing_rule.get_effective_price()

                if not wallet.has_sufficient_balance(required_amount):
                    self.message = f"Free quota exceeded and insufficient balance. Required: {required_amount} so'm"
                    return False

            except BillingRule.DoesNotExist:
                self.message = "Free quota exceeded and no billing rule configured"
                return False

        return True


class ServiceTypePermission(permissions.BasePermission):
    """Dynamic permission based on service type"""

    def __init__(self, service_type):
        self.service_type = service_type
        self.message = f"Cannot access {service_type} service"

    def has_permission(self, request, view):
        """Check permission for specific service type"""
        if not request.user.is_authenticated:
            return False

        # Check if service is available
        try:
            billing_rule = BillingRule.objects.get(
                service_type=self.service_type,
                is_active=True
            )
        except BillingRule.DoesNotExist:
            self.message = f"Service {self.service_type} is not available"
            return False

        # Check user access
        access_check = BillingService.can_user_access_service(
            request.user,
            self.service_type
        )

        if not access_check['can_access']:
            self.message = access_check.get('reason', 'Access denied')
            return False

        return True


class BillingOwnershipPermission(permissions.BasePermission):
    """Permission to check ownership of billing objects"""

    message = "Can only access own billing records"

    def has_permission(self, request, view):
        """Basic authentication check"""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user owns the billing object"""
        # For wallet-related objects
        if hasattr(obj, 'wallet'):
            return obj.wallet.user == request.user

        # For user-related objects
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # For transactions
        if hasattr(obj, 'wallet') and hasattr(obj.wallet, 'user'):
            return obj.wallet.user == request.user

        return False


class MinimumBalancePermission(permissions.BasePermission):
    """Permission to check minimum balance requirement"""

    def __init__(self, minimum_balance=Decimal('1000.00')):
        self.minimum_balance = minimum_balance
        self.message = f"Minimum balance of {minimum_balance} so'm required"

    def has_permission(self, request, view):
        """Check if user has minimum balance"""
        if not request.user.is_authenticated:
            return False

        try:
            wallet = request.user.wallet
            if wallet.balance < self.minimum_balance:
                return False
        except UserWallet.DoesNotExist:
            return False  # No wallet, no balance

        return True


class BillingMaintenancePermission(permissions.BasePermission):
    """Permission that checks billing maintenance mode"""

    message = "Billing system is under maintenance"

    def has_permission(self, request, view):
        """Check if billing system is not in maintenance mode"""
        settings = BillingSettings.get_settings()

        # Allow superusers even in maintenance mode
        if request.user.is_superuser:
            return True

        # Check maintenance mode
        if settings.maintenance_mode:
            return False

        return True


class DailyLimitPermission(permissions.BasePermission):
    """Permission to check daily spending limits"""

    def __init__(self, daily_limit=Decimal('100000.00')):
        self.daily_limit = daily_limit
        self.message = f"Daily spending limit of {daily_limit} so'm exceeded"

    def has_permission(self, request, view):
        """Check if user hasn't exceeded daily spending limit"""
        if not request.user.is_authenticated:
            return False

        # Calculate today's spending
        today = timezone.now().date()

        try:
            wallet = request.user.wallet
            today_spending = wallet.transactions.filter(
                created_at__date=today,
                transaction_type='debit',
                status='completed'
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')

            if today_spending >= self.daily_limit:
                return False

        except UserWallet.DoesNotExist:
            pass  # No wallet, no spending

        return True


# Permission classes for different user types
class PatientBillingPermission(permissions.BasePermission):
    """Permission for patient billing operations"""

    def has_permission(self, request, view):
        return (
                request.user.is_authenticated and
                request.user.user_type == 'patient'
        )


class DoctorBillingPermission(permissions.BasePermission):
    """Permission for doctor billing operations"""

    def has_permission(self, request, view):
        return (
                request.user.is_authenticated and
                request.user.user_type == 'doctor' and
                hasattr(request.user, 'doctor_profile') and
                request.user.doctor_profile.verification_status == 'approved'
        )


# Composite permissions for complex scenarios
class ComprehensiveBillingPermission(permissions.BasePermission):
    """Comprehensive billing permission with multiple checks"""

    def has_permission(self, request, view):
        """Perform comprehensive billing permission check"""
        if not request.user.is_authenticated:
            return False

        # Check billing system status
        settings = BillingSettings.get_settings()
        if settings.maintenance_mode and not request.user.is_superuser:
            return False

        # Check wallet status
        try:
            wallet = request.user.wallet
            if wallet.is_blocked:
                return False
        except UserWallet.DoesNotExist:
            pass  # Will be created automatically

        # Check user account status
        if not request.user.is_active:
            return False

        return True


# Decorator for method-level permission checking
def require_billing_permission(permission_class, *args, **kwargs):
    """Decorator to require specific billing permission"""

    def decorator(view_func):
        def wrapper(request, *view_args, **view_kwargs):
            permission = permission_class(*args, **kwargs)

            if not permission.has_permission(request, None):
                raise PermissionDenied(permission.message)

            return view_func(request, *view_args, **view_kwargs)

        return wrapper

    return decorator


# Usage examples in docstring
"""
Usage Examples:

# In views.py
class DoctorDetailView(APIView):
    permission_classes = [HasSufficientBalance, CanAccessDoctorProfile]
    billing_service_type = 'doctor_view'

# In viewsets
class BillingRuleViewSet(ModelViewSet):
    permission_classes = [CanManageBillingRules]

# With decorators
@require_billing_permission(MinimumBalancePermission, Decimal('5000.00'))
def premium_service_view(request):
    pass

# Composite permissions
class WalletTopupView(APIView):
    permission_classes = [
        ComprehensiveBillingPermission,
        CanPerformWalletAction,
        RateLimitedBillingAccess
    ]
"""

print("🔒 Billing permissions system loaded!")
print("✅ Features: Balance checking, rate limiting, admin controls")
print("🛡️ Security: Multi-layer validation, ownership checks, maintenance mode")
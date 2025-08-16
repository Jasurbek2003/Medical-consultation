from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import UserWallet, BillingRule,DoctorViewCharge, BillingSettings
from .serializers import (
    UserWalletSerializer, WalletTransactionSerializer, BillingRuleSerializer, DoctorViewChargeSerializer
)
from apps.doctors.models import Doctor
from .services import BillingService

User = get_user_model()


class UserWalletView(APIView):
    """User wallet information"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user wallet info"""
        wallet, created = UserWallet.objects.get_or_create(user=request.user)
        serializer = UserWalletSerializer(wallet)
        return Response({
            'success': True,
            'wallet': serializer.data
        })


class WalletTransactionListView(generics.ListAPIView):
    """User wallet transaction history"""
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        wallet = get_object_or_404(UserWallet, user=self.request.user)
        return wallet.transactions.all()


class BillingRulesView(APIView):
    """Get current billing rules"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Get all active billing rules"""
        rules = BillingRule.objects.filter(is_active=True)
        serializer = BillingRuleSerializer(rules, many=True)
        return Response({
            'success': True,
            'billing_rules': serializer.data
        })


class CheckBalanceView(APIView):
    """Check if user has sufficient balance for service"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Check balance for specific service"""
        service_type = request.data.get('service_type')
        quantity = request.data.get('quantity', 1)

        if not service_type:
            return Response({
                'success': False,
                'error': 'service_type is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            billing_rule = BillingRule.objects.get(
                service_type=service_type,
                is_active=True
            )

            wallet = get_object_or_404(UserWallet, user=request.user)
            required_amount = billing_rule.get_effective_price(quantity) * quantity

            has_balance = wallet.has_sufficient_balance(required_amount)

            return Response({
                'success': True,
                'has_sufficient_balance': has_balance,
                'current_balance': wallet.balance,
                'required_amount': required_amount,
                'service_price': billing_rule.get_effective_price(quantity)
            })

        except BillingRule.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Billing rule not found for this service'
            }, status=status.HTTP_404_NOT_FOUND)


class ChargeForServiceView(APIView):
    """Charge user for a service"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Charge user for specific service"""
        service_type = request.data.get('service_type')
        object_id = request.data.get('object_id')  # e.g., doctor_id
        quantity = request.data.get('quantity', 1)

        if not service_type:
            return Response({
                'success': False,
                'error': 'service_type is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Get billing rule
                billing_rule = BillingRule.objects.get(
                    service_type=service_type,
                    is_active=True
                )

                # Check billing settings
                settings = BillingSettings.get_settings()
                if not settings.enable_billing:
                    return Response({
                        'success': True,
                        'message': 'Billing is disabled, service granted for free'
                    })

                # Get user wallet
                wallet = get_object_or_404(UserWallet, user=request.user)

                # Calculate amount
                price_per_unit = billing_rule.get_effective_price(quantity)
                total_amount = price_per_unit * quantity

                # Check for free usage
                if service_type == 'doctor_view':
                    free_views_used = BillingService.get_daily_free_views_used(request.user)
                    if free_views_used < settings.free_views_per_day:
                        # Grant free view
                        BillingService.record_free_view(request.user, object_id)
                        return Response({
                            'success': True,
                            'charged': False,
                            'message': f'Free view granted ({free_views_used + 1}/{settings.free_views_per_day})'
                        })

                # Check balance
                if not wallet.has_sufficient_balance(total_amount):
                    return Response({
                        'success': False,
                        'error': 'Insufficient balance',
                        'current_balance': wallet.balance,
                        'required_amount': total_amount
                    }, status=status.HTTP_402_PAYMENT_REQUIRED)

                # Deduct balance
                description = f"{billing_rule.get_service_type_display()}"
                if object_id:
                    description += f" (ID: {object_id})"

                wallet.deduct_balance(total_amount, description)

                # Record specific service charge
                if service_type == 'doctor_view' and object_id:
                    doctor = get_object_or_404(Doctor, id=object_id)
                    transaction_obj = wallet.transactions.first()  # Latest transaction

                    DoctorViewCharge.objects.create(
                        user=request.user,
                        doctor=doctor,
                        transaction=transaction_obj,
                        amount_charged=total_amount,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )

                return Response({
                    'success': True,
                    'charged': True,
                    'amount_charged': total_amount,
                    'new_balance': wallet.balance,
                    'message': f'Successfully charged for {billing_rule.get_service_type_display()}'
                })

        except BillingRule.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Billing rule not found for this service'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoctorViewChargeHistoryView(generics.ListAPIView):
    """User's doctor view charge history"""
    serializer_class = DoctorViewChargeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DoctorViewCharge.objects.filter(user=self.request.user)


class BillingStatsView(APIView):
    """User billing statistics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user billing statistics"""
        wallet = get_object_or_404(UserWallet, user=request.user)

        # Calculate stats
        today = timezone.now().date()
        current_month = timezone.now().replace(day=1)

        # Today's spending
        today_spending = wallet.transactions.filter(
            created_at__date=today,
            transaction_type='debit'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # This month's spending
        month_spending = wallet.transactions.filter(
            created_at__gte=current_month,
            transaction_type='debit'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Doctor views today
        doctor_views_today = DoctorViewCharge.objects.filter(
            user=request.user,
            created_at__date=today
        ).count()

        # Free views used today
        settings = BillingSettings.get_settings()
        free_views_used = BillingService.get_daily_free_views_used(request.user)

        return Response({
            'success': True,
            'stats': {
                'current_balance': wallet.balance,
                'total_spent': wallet.total_spent,
                'total_topped_up': wallet.total_topped_up,
                'today_spending': today_spending,
                'month_spending': month_spending,
                'doctor_views_today': doctor_views_today,
                'free_views_used_today': free_views_used,
                'free_views_remaining': max(0, settings.free_views_per_day - free_views_used)
            }
        })


# Protected doctor endpoints
class ProtectedDoctorDetailView(APIView):
    """Protected doctor detail view with billing"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, doctor_id):
        """Get doctor details with billing check"""
        doctor = get_object_or_404(Doctor, id=doctor_id, verification_status='approved')

        # Check if billing is enabled
        settings = BillingSettings.get_settings()
        if not settings.enable_billing:
            # Return doctor data without charging
            from apps.doctors.serializers import DoctorSerializer
            serializer = DoctorSerializer(doctor)
            return Response({
                'success': True,
                'doctor': serializer.data,
                'charged': False,
                'message': 'Billing disabled - free access'
            })

        # Check if user has already viewed this doctor today
        today = timezone.now().date()
        already_viewed = DoctorViewCharge.objects.filter(
            user=request.user,
            doctor=doctor,
            created_at__date=today
        ).exists()

        if already_viewed:
            # Return doctor data without charging again
            from apps.doctors.serializers import DoctorSerializer
            serializer = DoctorSerializer(doctor)
            return Response({
                'success': True,
                'doctor': serializer.data,
                'charged': False,
                'message': 'Already viewed today - free access'
            })

        # Try to charge for view
        charge_response = ChargeForServiceView().post(request, {
            'service_type': 'doctor_view',
            'object_id': doctor_id
        })

        if not charge_response.data.get('success'):
            return charge_response

        # Return doctor data
        from apps.doctors.serializers import DoctorSerializer
        serializer = DoctorSerializer(doctor)

        return Response({
            'success': True,
            'doctor': serializer.data,
            'charged': charge_response.data.get('charged', False),
            'amount_charged': charge_response.data.get('amount_charged', 0),
            'new_balance': charge_response.data.get('new_balance'),
            'message': charge_response.data.get('message', 'Success')
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_doctor_view_access(request, doctor_id):
    """Check if user can access doctor without charging"""
    doctor = get_object_or_404(Doctor, id=doctor_id, verification_status='approved')

    # Check billing settings
    settings = BillingSettings.get_settings()
    if not settings.enable_billing:
        return Response({
            'has_access': True,
            'reason': 'billing_disabled',
            'charge_required': False
        })

    # Check if already viewed today
    today = timezone.now().date()
    already_viewed = DoctorViewCharge.objects.filter(
        user=request.user,
        doctor=doctor,
        created_at__date=today
    ).exists()

    if already_viewed:
        return Response({
            'has_access': True,
            'reason': 'already_viewed_today',
            'charge_required': False
        })

    # Check free views
    free_views_used = BillingService.get_daily_free_views_used(request.user)
    if free_views_used < settings.free_views_per_day:
        return Response({
            'has_access': True,
            'reason': 'free_view_available',
            'charge_required': False,
            'free_views_used': free_views_used,
            'free_views_total': settings.free_views_per_day
        })

    # Check balance for paid access
    try:
        billing_rule = BillingRule.objects.get(
            service_type='doctor_view',
            is_active=True
        )

        wallet = get_object_or_404(UserWallet, user=request.user)
        required_amount = billing_rule.get_effective_price()
        has_balance = wallet.has_sufficient_balance(required_amount)

        return Response({
            'has_access': has_balance,
            'reason': 'payment_required',
            'charge_required': True,
            'required_amount': required_amount,
            'current_balance': wallet.balance,
            'has_sufficient_balance': has_balance
        })

    except BillingRule.DoesNotExist:
        return Response({
            'has_access': False,
            'reason': 'billing_rule_not_found',
            'error': 'Billing configuration error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_daily_usage(request):
    """Get user's daily usage statistics"""
    today = timezone.now().date()
    settings = BillingSettings.get_settings()

    # Free views used
    free_views_used = BillingService.get_daily_free_views_used(request.user)

    # Paid views today
    paid_views = DoctorViewCharge.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()

    # Total spending today
    wallet = get_object_or_404(UserWallet, user=request.user)
    today_spending = wallet.transactions.filter(
        created_at__date=today,
        transaction_type='debit'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    return Response({
        'success': True,
        'daily_usage': {
            'free_views_used': free_views_used,
            'free_views_remaining': max(0, settings.free_views_per_day - free_views_used),
            'paid_views': paid_views,
            'total_views': free_views_used + paid_views,
            'spending_today': today_spending,
            'current_balance': wallet.balance
        }
    })
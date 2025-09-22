"""
Wallet Management API Views
Provides endpoints for wallet operations and billing integration
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from apps.billing.models import UserWallet, WalletTransaction, BillingRule, BillingSettings
from .billing_integration import WalletService, BillingService, PaymentBillingIntegration
from .serializers import PaymentSerializer
from .models import Payment


class WalletInfoView(APIView):
    """Get user wallet information"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get comprehensive wallet information"""
        try:
            wallet_info = WalletService.get_wallet_info(request.user)

            # Format recent transactions
            transactions_data = []
            for transaction in wallet_info['recent_transactions']:
                transactions_data.append({
                    'id': str(transaction.id),
                    'type': transaction.transaction_type,
                    'amount': float(transaction.amount),
                    'balance_after': float(transaction.balance_after),
                    'description': transaction.description,
                    'status': transaction.status,
                    'created_at': transaction.created_at.isoformat()
                })

            response_data = {
                'balance': float(wallet_info['balance']),
                'total_spent': float(wallet_info['total_spent']),
                'total_topped_up': float(wallet_info['total_topped_up']),
                'is_blocked': wallet_info['is_blocked'],
                'today_spending': float(wallet_info['today_spending']),
                'recent_transactions': transactions_data,
                'billing_settings': {
                    'min_topup': float(wallet_info['billing_settings'].min_wallet_topup),
                    'max_balance': float(wallet_info['billing_settings'].max_wallet_balance),
                    'free_views_per_day': wallet_info['billing_settings'].free_views_per_day,
                    'enable_billing': wallet_info['billing_settings'].enable_billing,
                    'maintenance_mode': wallet_info['billing_settings'].maintenance_mode,
                }
            }

            return Response({
                'success': True,
                'wallet': response_data
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletTransactionsView(generics.ListAPIView):
    """List user wallet transactions"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get paginated wallet transactions"""
        try:
            wallet = WalletService.get_or_create_wallet(request.user)

            # Filter parameters
            transaction_type = request.GET.get('type')  # credit, debit
            status_filter = request.GET.get('status', 'completed')
            days = int(request.GET.get('days', 30))
            page = int(request.GET.get('page', 1))
            per_page = min(int(request.GET.get('per_page', 20)), 100)

            # Build queryset
            queryset = wallet.transactions.filter(status=status_filter)

            if transaction_type in ['credit', 'debit']:
                queryset = queryset.filter(transaction_type=transaction_type)

            if days > 0:
                from datetime import timedelta
                start_date = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(created_at__gte=start_date)

            # Pagination
            total_count = queryset.count()
            offset = (page - 1) * per_page
            transactions = queryset.order_by('-created_at')[offset:offset + per_page]

            # Format data
            transactions_data = []
            for transaction in transactions:
                transactions_data.append({
                    'id': str(transaction.id),
                    'type': transaction.transaction_type,
                    'type_display': transaction.get_transaction_type_display(),
                    'amount': float(transaction.amount),
                    'balance_before': float(transaction.balance_before),
                    'balance_after': float(transaction.balance_after),
                    'description': transaction.description,
                    'status': transaction.status,
                    'status_display': transaction.get_status_display(),
                    'created_at': transaction.created_at.isoformat()
                })

            return Response({
                'success': True,
                'transactions': transactions_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page,
                    'has_next': offset + per_page < total_count,
                    'has_previous': page > 1
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateWalletTopupView(APIView):
    """Create wallet topup payment"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create wallet topup payment"""
        try:
            amount = request.data.get('amount')
            gateway_name = request.data.get('gateway')
            return_url = request.data.get('return_url', '')

            if not amount or not gateway_name:
                return Response({
                    'success': False,
                    'error': 'Amount and gateway are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate amount
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'Invalid amount'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create topup payment
            payment = PaymentBillingIntegration.create_wallet_topup_payment(
                user=request.user,
                amount=amount,
                gateway_name=gateway_name,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                callback_url=return_url
            )

            # Generate payment URL
            if payment.gateway.name == 'click':
                from .services import ClickService
                payment_data = ClickService.create_payment(payment)
            elif payment.gateway.name == 'payme':
                from .services import PaymeService
                payment_data = PaymeService.create_payment(payment)
            else:
                return Response({
                    'success': False,
                    'error': 'Gateway not implemented'
                }, status=status.HTTP_501_NOT_IMPLEMENTED)

            return Response({
                'success': True,
                'payment': {
                    'id': str(payment.id),
                    'reference_number': payment.reference_number,
                    'amount': float(payment.amount),
                    'total_amount': float(payment.total_amount),
                    'commission': float(payment.commission),
                    'status': payment.status,
                    'gateway': payment.gateway.display_name,
                    'payment_url': payment_data.get('payment_url'),
                    'expires_at': payment.expires_at.isoformat() if payment.expires_at else None
                }
            })

        except ValidationError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Payment creation failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckServiceAccessView(APIView):
    """Check if user can access a service"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Check service access"""
        try:
            service_type = request.data.get('service_type')
            quantity = int(request.data.get('quantity', 1))

            if not service_type:
                return Response({
                    'success': False,
                    'error': 'Service type is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            can_access, message = BillingService.can_access_service(
                user=request.user,
                service_type=service_type,
                quantity=quantity
            )

            price = BillingService.get_service_price(service_type, quantity)

            return Response({
                'success': True,
                'can_access': can_access,
                'message': message,
                'price': float(price * quantity),
                'unit_price': float(price),
                'quantity': quantity,
                'service_type': service_type,
                'user_balance': float(WalletService.get_or_create_wallet(request.user).balance)
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChargeForServiceView(APIView):
    """Charge user for a service"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Charge user for service"""
        try:
            service_type = request.data.get('service_type')
            quantity = int(request.data.get('quantity', 1))
            related_object_id = request.data.get('related_object_id')

            if not service_type:
                return Response({
                    'success': False,
                    'error': 'Service type is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get related object if provided
            related_object = None
            if related_object_id and service_type == 'doctor_view':
                from apps.doctors.models import Doctor
                try:
                    related_object = Doctor.objects.get(id=related_object_id)
                except Doctor.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': 'Doctor not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # Charge for service
            wallet_transaction = BillingService.charge_for_service(
                user=request.user,
                service_type=service_type,
                quantity=quantity,
                related_object=related_object,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            response_data = {
                'success': True,
                'charged': wallet_transaction is not None,
                'service_type': service_type,
                'quantity': quantity
            }

            if wallet_transaction:
                response_data.update({
                    'transaction_id': str(wallet_transaction.id),
                    'amount_charged': float(wallet_transaction.amount),
                    'balance_after': float(wallet_transaction.balance_after),
                    'description': wallet_transaction.description
                })
            else:
                response_data['message'] = 'Service accessed without charge (free)'

            return Response(response_data)

        except ValidationError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillingRulesView(APIView):
    """Get billing rules and prices"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Get all active billing rules"""
        try:
            rules = BillingRule.objects.filter(is_active=True).order_by('service_type')

            rules_data = []
            for rule in rules:
                rules_data.append({
                    'service_type': rule.service_type,
                    'service_name': rule.get_service_type_display(),
                    'price': float(rule.price),
                    'description': rule.description,
                    'discount_percentage': float(rule.discount_percentage),
                    'min_quantity_for_discount': rule.min_quantity_for_discount,
                    'effective_prices': {
                        '1': float(rule.get_effective_price(1)),
                        str(rule.min_quantity_for_discount): float(rule.get_effective_price(rule.min_quantity_for_discount)),
                        '10': float(rule.get_effective_price(10))
                    }
                })

            billing_settings = BillingSettings.get_settings()

            return Response({
                'success': True,
                'billing_rules': rules_data,
                'settings': {
                    'enable_billing': billing_settings.enable_billing,
                    'maintenance_mode': billing_settings.maintenance_mode,
                    'free_views_per_day': billing_settings.free_views_per_day,
                    'free_views_for_new_users': billing_settings.free_views_for_new_users,
                    'min_wallet_topup': float(billing_settings.min_wallet_topup),
                    'max_wallet_balance': float(billing_settings.max_wallet_balance)
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserBillingSummaryView(APIView):
    """Get user billing summary"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user billing summary for specified period"""
        try:
            days = int(request.GET.get('days', 30))
            summary = PaymentBillingIntegration.get_user_billing_summary(request.user, days)

            return Response({
                'success': True,
                'summary': {
                    'period_days': summary['period_days'],
                    'wallet_info': {
                        'current_balance': float(summary['wallet_info']['current_balance']),
                        'total_credited': float(summary['wallet_info']['total_credited']),
                        'total_debited': float(summary['wallet_info']['total_debited']),
                        'credit_transactions': summary['wallet_info']['credit_transactions'],
                        'debit_transactions': summary['wallet_info']['debit_transactions'],
                        'net_change': float(summary['net_change'])
                    },
                    'payment_summary': {
                        'total_payments': summary['payment_summary']['total_payments'],
                        'completed_payments': summary['payment_summary']['completed_payments'],
                        'total_amount': float(summary['payment_summary']['total_amount']),
                        'pending_payments': summary['payment_summary']['pending_payments'],
                        'failed_payments': summary['payment_summary']['failed_payments']
                    },
                    'service_summary': {
                        'doctor_views': summary['service_summary']['doctor_views'],
                        'doctor_view_charges': float(summary['service_summary']['doctor_view_charges']),
                        'free_doctor_views': summary['service_summary']['free_doctor_views']
                    }
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletTopupHistoryView(APIView):
    """Get wallet topup history"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's wallet topup payments"""
        try:
            # Get topup payments
            payments = Payment.objects.filter(
                user=request.user,
                payment_type='wallet_topup'
            ).order_by('-created_at')

            # Pagination
            page = int(request.GET.get('page', 1))
            per_page = min(int(request.GET.get('per_page', 20)), 100)
            total_count = payments.count()
            offset = (page - 1) * per_page
            payments_page = payments[offset:offset + per_page]

            # Format payments
            payments_data = []
            for payment in payments_page:
                serializer = PaymentSerializer(payment)
                payments_data.append(serializer.data)

            return Response({
                'success': True,
                'payments': payments_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page,
                    'has_next': offset + per_page < total_count,
                    'has_previous': page > 1
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Quick utility endpoints
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def quick_balance_check(request):
    """Quick balance check"""
    try:
        wallet = WalletService.get_or_create_wallet(request.user)
        return Response({
            'balance': float(wallet.balance),
            'is_blocked': wallet.is_blocked
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def estimate_topup(request):
    """Estimate topup cost including commission"""
    try:
        amount = request.data.get('amount')
        gateway_name = request.data.get('gateway')

        if not amount or not gateway_name:
            return Response({
                'error': 'Amount and gateway are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        amount = Decimal(str(amount))
        from .models import PaymentGateway
        gateway = PaymentGateway.objects.get(name=gateway_name, is_active=True)

        commission = gateway.calculate_commission(amount)
        total_amount = amount + commission

        return Response({
            'amount': float(amount),
            'commission': float(commission),
            'total_amount': float(total_amount),
            'gateway': gateway.display_name,
            'commission_type': gateway.commission_type,
            'commission_percentage': float(gateway.commission_percentage),
            'commission_fixed': float(gateway.commission_fixed)
        })

    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


print("🚀 Wallet management views loaded successfully!")
print("💳 Features: Balance check, transactions, topup, service charging")
print("📊 Endpoints: Wallet info, billing summary, transaction history")
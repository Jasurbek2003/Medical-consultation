from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from decimal import Decimal
import json

from .models import (
    PaymentGateway, Payment, PaymentWebhook,
    PaymentProcessor
)
from .serializers import (
    PaymentSerializer, PaymentGatewaySerializer,
    PaymentMethodSerializer
)
from .services import ClickService, PaymeService


class PaymentGatewayListView(APIView):
    """List available payment gateways"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Get all active payment gateways"""
        gateways = PaymentGateway.objects.filter(is_active=True)
        serializer = PaymentGatewaySerializer(gateways, many=True)
        return Response({
            'success': True,
            'gateways': serializer.data
        })


class CreatePaymentView(APIView):
    """Create a new payment"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Create payment for wallet topup"""
        gateway_name = request.data.get('gateway')
        amount = request.data.get('amount')
        return_url = request.data.get('callback_url', '')

        if not gateway_name or not amount:
            return Response({
                'success': False,
                'error': 'gateway and amount are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            gateway = PaymentGateway.objects.get(name=gateway_name, is_active=True)

            # Validate amount
            PaymentProcessor.validate_payment_amount(gateway, amount)

            # Create payment
            payment = PaymentProcessor.create_payment(
                user=request.user,
                gateway=gateway,
                amount=amount,
                payment_type='wallet_topup',
                description=f'Hamyon to\'ldirish - {amount} so\'m'
            )

            # Set additional info
            payment.ip_address = request.META.get('REMOTE_ADDR')
            payment.user_agent = request.META.get('HTTP_USER_AGENT', '')
            payment.callback_url = return_url
            payment.save()

            # Generate payment URL based on gateway
            if gateway.name == 'click':
                payment_data = ClickService.create_payment(payment)
            elif gateway.name == 'payme':
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
                    'amount': payment.amount,
                    'total_amount': payment.total_amount,
                    'commission': payment.commission,
                    'status': payment.status,
                    'gateway': gateway.display_name,
                    'payment_url': payment_data.get('payment_url'),
                    'expires_at': payment.expires_at.isoformat() if payment.expires_at else None
                }
            })

        except PaymentGateway.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment gateway not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({
                'success': False,
                'error': 'Payment creation failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusView(APIView):
    """Check payment status"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, payment_id):
        """Get payment status"""
        try:
            payment = Payment.objects.get(
                id=payment_id,
                user=request.user
            )

            serializer = PaymentSerializer(payment)
            return Response({
                'success': True,
                'payment': serializer.data
            })

        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)


class PaymentHistoryView(generics.ListAPIView):
    """User payment history"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


# Click Payment Gateway Views
@method_decorator(csrf_exempt, name='dispatch')
class ClickWebhookView(APIView):
    """Click payment webhook handler"""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        """Handle Click webhook"""
        try:
            data = request.data

            # Log webhook
            webhook = PaymentWebhook.objects.create(
                payment_id=data.get('merchant_trans_id'),
                gateway=PaymentGateway.objects.get(name='click'),
                webhook_data=data,
                headers=dict(request.META),
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Process webhook
            result = ClickService.process_webhook(data)
            webhook.processed = True
            webhook.processing_result = str(result)
            webhook.save()

            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({
                'error': -1,
                'error_note': str(e)
            })


class ClickPrepareView(APIView):
    """Click prepare endpoint"""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        """Handle Click prepare request"""
        try:
            data = request.data
            result = ClickService.prepare(data)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                'error': -1,
                'error_note': str(e)
            })


class ClickCompleteView(APIView):
    """Click complete endpoint"""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        """Handle Click complete request"""
        try:
            data = request.data
            result = ClickService.complete(data)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                'error': -1,
                'error_note': str(e)
            })


# Payme Payment Gateway Views
@method_decorator(csrf_exempt, name='dispatch')
class PaymeWebhookView(APIView):
    """Payme payment webhook handler"""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        """Handle Payme JSON-RPC webhook"""
        try:
            data = json.loads(request.body)

            # Log webhook
            webhook = PaymentWebhook.objects.create(
                payment_id=data.get('params', {}).get('account', {}).get('payment_id'),
                gateway=PaymentGateway.objects.get(name='payme'),
                webhook_data=data,
                headers=dict(request.META),
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Process webhook
            result = PaymeService.process_webhook(data)
            webhook.processed = True
            webhook.processing_result = str(result)
            webhook.save()

            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': data.get('id', 0),
                'error': {
                    'code': -32400,
                    'message': str(e)
                }
            })


# Payment utility endpoints
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_payment(request, payment_id):
    """Cancel a payment"""
    try:
        payment = Payment.objects.get(
            id=payment_id,
            user=request.user,
            status='pending'
        )

        payment.status = 'cancelled'
        payment.save()

        return Response({
            'success': True,
            'message': 'Payment cancelled successfully'
        })

    except Payment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment not found or cannot be cancelled'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_methods(request):
    """Get user's saved payment methods"""
    methods = request.user.payment_methods.filter(is_active=True)
    serializer = PaymentMethodSerializer(methods, many=True)
    return Response({
        'success': True,
        'payment_methods': serializer.data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def estimate_payment(request):
    """Estimate payment amount including commission"""
    gateway_name = request.data.get('gateway')
    amount = request.data.get('amount')

    if not gateway_name or not amount:
        return Response({
            'success': False,
            'error': 'gateway and amount are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = Decimal(str(amount))
        gateway = PaymentGateway.objects.get(name=gateway_name, is_active=True)

        commission = gateway.calculate_commission(amount)
        total_amount = amount + commission

        return Response({
            'success': True,
            'estimate': {
                'amount': amount,
                'commission': commission,
                'total_amount': total_amount,
                'gateway': gateway.display_name,
                'commission_percentage': gateway.commission_percentage,
                'commission_fixed': gateway.commission_fixed
            }
        })

    except (ValueError, TypeError):
        return Response({
            'success': False,
            'error': 'Invalid amount'
        }, status=status.HTTP_400_BAD_REQUEST)
    except PaymentGateway.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment gateway not found'
        }, status=status.HTTP_404_NOT_FOUND)


# Administrative endpoints
class PaymentAnalyticsView(APIView):
    """Payment analytics for admins"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """Get payment analytics"""
        from django.db.models import Sum, Count, Avg
        from datetime import datetime, timedelta

        # Date range
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Base queryset
        payments = Payment.objects.filter(created_at__gte=start_date)

        # Analytics
        analytics = {
            'total_payments': payments.count(),
            'successful_payments': payments.filter(status='completed').count(),
            'failed_payments': payments.filter(status='failed').count(),
            'pending_payments': payments.filter(status='pending').count(),
            'total_amount': payments.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'average_amount': payments.filter(status='completed').aggregate(
                avg=Avg('amount')
            )['avg'] or Decimal('0.00'),
            'total_commission': payments.filter(status='completed').aggregate(
                total=Sum('commission')
            )['total'] or Decimal('0.00'),
        }

        # Gateway breakdown
        gateway_stats = []
        for gateway in PaymentGateway.objects.filter(is_active=True):
            gateway_payments = payments.filter(gateway=gateway)
            gateway_stats.append({
                'gateway': gateway.display_name,
                'total_payments': gateway_payments.count(),
                'successful_payments': gateway_payments.filter(status='completed').count(),
                'total_amount': gateway_payments.filter(status='completed').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0.00'),
            })

        return Response({
            'success': True,
            'analytics': analytics,
            'gateway_stats': gateway_stats,
            'period_days': days
        })


# Payment verification endpoints
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_payment(request, payment_id):
    """Manually verify payment status with gateway"""
    try:
        payment = Payment.objects.get(
            id=payment_id,
            user=request.user
        )

        if payment.gateway.name == 'click':
            result = ClickService.verify_payment(payment)
        elif payment.gateway.name == 'payme':
            result = PaymeService.verify_payment(payment)
        else:
            return Response({
                'success': False,
                'error': 'Gateway verification not supported'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

        return Response({
            'success': True,
            'verification_result': result,
            'payment_status': payment.status
        })

    except Payment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def gateway_status(request):
    """Check gateway availability status"""
    gateways_status = []

    for gateway in PaymentGateway.objects.filter(is_active=True):
        try:
            if gateway.name == 'click':
                status_check = ClickService.check_status()
            elif gateway.name == 'payme':
                status_check = PaymeService.check_status()
            else:
                status_check = {'available': True, 'message': 'Unknown'}

            gateways_status.append({
                'gateway': gateway.display_name,
                'name': gateway.name,
                'available': status_check.get('available', False),
                'message': status_check.get('message', ''),
                'response_time': status_check.get('response_time', 0)
            })

        except Exception as e:
            gateways_status.append({
                'gateway': gateway.display_name,
                'name': gateway.name,
                'available': False,
                'message': f'Error: {str(e)}',
                'response_time': 0
            })

    return Response({
        'success': True,
        'gateways': gateways_status,
        'timestamp': timezone.now().isoformat()
    })
import hashlib
import json
import time
import requests
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from datetime import datetime

from .models import (
    Payment, ClickTransaction, PaymeTransaction,
    PaymentGateway
)


class ClickService:
    """Click payment gateway service"""

    @staticmethod
    def create_payment(payment):
        """Create Click payment"""
        gateway = payment.gateway

        # Create Click transaction
        click_transaction = ClickTransaction.objects.create(
            payment=payment,
            click_trans_id=str(payment.id),
            merchant_trans_id=str(payment.id),
            service_id=gateway.service_id
        )

        # Generate payment URL
        payment_url = ClickService._generate_payment_url(payment, gateway)
        payment.payment_url = payment_url
        payment.save()

        return {
            'payment_url': payment_url,
            'transaction_id': click_transaction.click_trans_id
        }

    @staticmethod
    def _generate_payment_url(payment, gateway):
        """Generate Click payment URL"""
        params = {
            'service_id': gateway.service_id,
            'merchant_id': gateway.merchant_id,
            'amount': str(payment.total_amount),
            'transaction_param': str(payment.id),
            'return_url': payment.callback_url or settings.FRONTEND_URL,
            'card_type': '1'  # All cards
        }

        # Create signature
        sign_string = (
            f"{params['service_id']}"
            f"{params['merchant_id']}"
            f"{params['amount']}"
            f"{params['transaction_param']}"
        )

        signature = hashlib.md5(
            (sign_string + gateway.secret_key).encode('utf-8')
        ).hexdigest()

        params['sign'] = signature

        # Build URL
        base_url = gateway.api_url or "https://my.click.uz/services/pay"
        url_params = "&".join([f"{k}={v}" for k, v in params.items()])

        return f"{base_url}?{url_params}"

    @staticmethod
    def prepare(data):
        """Handle Click prepare request"""
        click_trans_id = data.get('click_trans_id')
        service_id = data.get('service_id')
        amount = data.get('amount')
        action = data.get('action')
        merchant_trans_id = data.get('merchant_trans_id')
        sign_time = data.get('sign_time')
        sign_string = data.get('sign_string')

        try:
            # Verify signature
            gateway = PaymentGateway.objects.get(
                name='click',
                service_id=service_id
            )

            expected_sign = hashlib.md5(
                (str(click_trans_id) +
                 str(service_id) +
                 gateway.secret_key +
                 str(merchant_trans_id) +
                 str(amount) +
                 str(action) +
                 str(sign_time)).encode('utf-8')
            ).hexdigest()

            if expected_sign != sign_string:
                return {
                    'error': -1,
                    'error_note': 'Invalid signature'
                }

            # Find payment
            payment = Payment.objects.get(
                id=merchant_trans_id,
                gateway=gateway,
                status='pending'
            )

            # Check amount
            if Decimal(str(amount)) != payment.total_amount:
                return {
                    'error': -2,
                    'error_note': 'Invalid amount'
                }

            # Update Click transaction
            click_transaction = payment.click_transaction
            click_transaction.click_trans_id = click_trans_id
            click_transaction.merchant_prepare_id = str(int(time.time()))
            click_transaction.sign_time = datetime.fromtimestamp(int(sign_time))
            click_transaction.save()

            return {
                'error': 0,
                'error_note': 'Success',
                'merchant_prepare_id': click_transaction.merchant_prepare_id
            }

        except (Payment.DoesNotExist, PaymentGateway.DoesNotExist):
            return {
                'error': -5,
                'error_note': 'Payment not found'
            }
        except Exception as e:
            return {
                'error': -9,
                'error_note': f'Internal error: {str(e)}'
            }

    @staticmethod
    def complete(data):
        """Handle Click complete request"""
        click_trans_id = data.get('click_trans_id')
        service_id = data.get('service_id')
        amount = data.get('amount')
        action = data.get('action')
        merchant_trans_id = data.get('merchant_trans_id')
        merchant_prepare_id = data.get('merchant_prepare_id')
        sign_time = data.get('sign_time')
        sign_string = data.get('sign_string')
        error = data.get('error', 0)

        try:
            # Verify signature
            gateway = PaymentGateway.objects.get(
                name='click',
                service_id=service_id
            )

            expected_sign = hashlib.md5(
                (str(click_trans_id) +
                 str(service_id) +
                 gateway.secret_key +
                 str(merchant_trans_id) +
                 str(merchant_prepare_id) +
                 str(amount) +
                 str(action) +
                 str(sign_time)).encode('utf-8')
            ).hexdigest()

            if expected_sign != sign_string:
                return {
                    'error': -1,
                    'error_note': 'Invalid signature'
                }

            # Find payment
            payment = Payment.objects.get(
                id=merchant_trans_id,
                gateway=gateway
            )

            click_transaction = payment.click_transaction

            if error == 0:
                # Payment successful
                with transaction.atomic():
                    payment.mark_as_completed()
                    click_transaction.error_code = 0
                    click_transaction.save()

                return {
                    'error': 0,
                    'error_note': 'Success',
                    'merchant_confirm_id': str(int(time.time()))
                }
            else:
                # Payment failed
                payment.mark_as_failed(f"Click error: {error}")
                click_transaction.error_code = error
                click_transaction.error_note = data.get('error_note', '')
                click_transaction.save()

                return {
                    'error': 0,
                    'error_note': 'Transaction cancelled'
                }

        except (Payment.DoesNotExist, PaymentGateway.DoesNotExist):
            return {
                'error': -5,
                'error_note': 'Payment not found'
            }
        except Exception as e:
            return {
                'error': -9,
                'error_note': f'Internal error: {str(e)}'
            }

    @staticmethod
    def verify_payment(payment):
        """Verify payment status with Click"""
        # Click doesn't have a separate verify endpoint
        # Status is managed through prepare/complete flow
        return {
            'verified': True,
            'status': payment.status,
            'message': 'Click payments are verified through webhook flow'
        }

    @staticmethod
    def check_status():
        """Check Click service status"""
        try:
            # Simple health check
            response = requests.get('https://my.click.uz', timeout=10)
            return {
                'available': response.status_code == 200,
                'message': 'Service available',
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                'available': False,
                'message': f'Service unavailable: {str(e)}',
                'response_time': 0
            }

    @staticmethod
    def process_webhook(data):
        """Process Click webhook (alias for complete)"""
        return ClickService.complete(data)


class PaymeService:
    """Payme payment gateway service"""

    @staticmethod
    def create_payment(payment):
        """Create Payme payment"""
        gateway = payment.gateway

        # Create payment URL
        payment_url = PaymeService._generate_payment_url(payment, gateway)
        payment.payment_url = payment_url
        payment.save()

        return {
            'payment_url': payment_url,
            'payment_id': str(payment.id)
        }

    @staticmethod
    def _generate_payment_url(payment, gateway):
        """Generate Payme payment URL"""
        # Encode account data
        account = {
            'payment_id': str(payment.id)
        }

        import base64
        account_encoded = base64.b64encode(
            json.dumps(account).encode('utf-8')
        ).decode('utf-8')

        # Generate URL
        amount_tiyin = int(payment.total_amount * 100)  # Convert to tiyin

        base_url = "https://checkout.paycom.uz"
        url = f"{base_url}/{gateway.merchant_id}?amount={amount_tiyin}&account={account_encoded}"

        if payment.callback_url:
            url += f"&callback={payment.callback_url}"

        return url

    @staticmethod
    def check_perform_transaction(params):
        """Check if transaction can be performed"""
        account = params.get('account', {})
        amount = params.get('amount', 0)

        try:
            payment_id = account.get('payment_id')
            payment = Payment.objects.get(
                id=payment_id,
                status='pending'
            )

            # Check amount (Payme sends amount in tiyin)
            expected_amount_tiyin = int(payment.total_amount * 100)
            if amount != expected_amount_tiyin:
                return {
                    'error': {
                        'code': -31001,
                        'message': 'Invalid amount'
                    }
                }

            return {'result': {'allow': True}}

        except Payment.DoesNotExist:
            return {
                'error': {
                    'code': -31050,
                    'message': 'Payment not found'
                }
            }

    @staticmethod
    def create_transaction(params):
        """Create Payme transaction"""
        payme_id = params.get('id')
        payme_time = params.get('time')
        amount = params.get('amount')
        account = params.get('account', {})

        try:
            payment_id = account.get('payment_id')
            payment = Payment.objects.get(
                id=payment_id,
                status='pending'
            )

            # Check if transaction already exists
            try:
                payme_transaction = PaymeTransaction.objects.get(payme_id=payme_id)
                if payme_transaction.state == 1:
                    return {
                        'result': {
                            'create_time': payme_transaction.create_time,
                            'transaction': payme_transaction.payme_id,
                            'state': payme_transaction.state
                        }
                    }
            except PaymeTransaction.DoesNotExist:
                pass

            # Create new transaction
            create_time = int(time.time() * 1000)
            PaymeTransaction.objects.create(
                payment=payment,
                payme_id=payme_id,
                payme_time=payme_time,
                create_time=create_time,
                state=1  # Created
            )

            return {
                'result': {
                    'create_time': create_time,
                    'transaction': payme_id,
                    'state': 1
                }
            }

        except Payment.DoesNotExist:
            return {
                'error': {
                    'code': -31050,
                    'message': 'Payment not found'
                }
            }

    @staticmethod
    def perform_transaction(params):
        """Perform Payme transaction"""
        payme_id = params.get('id')

        try:
            payme_transaction = PaymeTransaction.objects.get(payme_id=payme_id)

            if payme_transaction.state == 1:
                # Complete the transaction
                perform_time = int(time.time() * 1000)

                with transaction.atomic():
                    payme_transaction.state = 2  # Completed
                    payme_transaction.perform_time = perform_time
                    payme_transaction.save()

                    # Mark payment as completed
                    payme_transaction.payment.mark_as_completed()

                return {
                    'result': {
                        'transaction': payme_id,
                        'perform_time': perform_time,
                        'state': 2
                    }
                }
            elif payme_transaction.state == 2:
                return {
                    'result': {
                        'transaction': payme_id,
                        'perform_time': payme_transaction.perform_time,
                        'state': 2
                    }
                }
            else:
                return {
                    'error': {
                        'code': -31008,
                        'message': 'Transaction cannot be performed'
                    }
                }

        except PaymeTransaction.DoesNotExist:
            return {
                'error': {
                    'code': -31003,
                    'message': 'Transaction not found'
                }
            }

    @staticmethod
    def cancel_transaction(params):
        """Cancel Payme transaction"""
        payme_id = params.get('id')
        reason = params.get('reason', 0)

        try:
            payme_transaction = PaymeTransaction.objects.get(payme_id=payme_id)

            if payme_transaction.state in [1, 2]:
                cancel_time = int(time.time() * 1000)

                with transaction.atomic():
                    payme_transaction.state = -1 if payme_transaction.state == 1 else -2
                    payme_transaction.cancel_time = cancel_time
                    payme_transaction.reason = reason
                    payme_transaction.save()

                    # Mark payment as failed
                    payme_transaction.payment.mark_as_failed(f"Payme cancelled, reason: {reason}")

                return {
                    'result': {
                        'transaction': payme_id,
                        'cancel_time': cancel_time,
                        'state': payme_transaction.state
                    }
                }
            else:
                return {
                    'result': {
                        'transaction': payme_id,
                        'cancel_time': payme_transaction.cancel_time,
                        'state': payme_transaction.state
                    }
                }

        except PaymeTransaction.DoesNotExist:
            return {
                'error': {
                    'code': -31003,
                    'message': 'Transaction not found'
                }
            }

    @staticmethod
    def check_transaction(params):
        """Check Payme transaction status"""
        payme_id = params.get('id')

        try:
            payme_transaction = PaymeTransaction.objects.get(payme_id=payme_id)

            result = {
                'create_time': payme_transaction.create_time,
                'perform_time': payme_transaction.perform_time,
                'cancel_time': payme_transaction.cancel_time,
                'transaction': payme_id,
                'state': payme_transaction.state,
                'reason': payme_transaction.reason
            }

            return {'result': result}

        except PaymeTransaction.DoesNotExist:
            return {
                'error': {
                    'code': -31003,
                    'message': 'Transaction not found'
                }
            }

    @staticmethod
    def process_webhook(data):
        """Process Payme webhook"""
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id', 0)

        try:
            if method == 'CheckPerformTransaction':
                result = PaymeService.check_perform_transaction(params)
            elif method == 'CreateTransaction':
                result = PaymeService.create_transaction(params)
            elif method == 'PerformTransaction':
                result = PaymeService.perform_transaction(params)
            elif method == 'CancelTransaction':
                result = PaymeService.cancel_transaction(params)
            elif method == 'CheckTransaction':
                result = PaymeService.check_transaction(params)
            else:
                result = {
                    'error': {
                        'code': -32601,
                        'message': 'Method not found'
                    }
                }

            response = {
                'jsonrpc': '2.0',
                'id': request_id
            }
            response.update(result)

            return response

        except Exception as e:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32400,
                    'message': str(e)
                }
            }

    @staticmethod
    def verify_payment(payment):
        """Verify payment status with Payme"""
        try:
            payme_transaction = payment.payme_transaction
            return {
                'verified': True,
                'status': payment.status,
                'payme_state': payme_transaction.state,
                'message': 'Payment verified'
            }
        except:
            return {
                'verified': False,
                'status': payment.status,
                'message': 'No Payme transaction found'
            }

    @staticmethod
    def check_status():
        """Check Payme service status"""
        try:
            response = requests.get('https://checkout.paycom.uz', timeout=10)
            return {
                'available': response.status_code == 200,
                'message': 'Service available',
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                'available': False,
                'message': f'Service unavailable: {str(e)}',
                'response_time': 0
            }
"""
Payment, Billing, and Wallet Integration Usage Examples
This file demonstrates how to use the integrated payment and billing system
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.billing.models import UserWallet, BillingRule, BillingSettings
from apps.payments.billing_integration import (
    WalletService, BillingService, PaymentBillingIntegration,
    check_user_balance, charge_user, topup_wallet, get_service_price
)
from apps.payments.models import PaymentGateway, Payment

User = get_user_model()


def example_wallet_operations():
    """Example wallet operations"""

    # Get a user
    user = User.objects.first()
    if not user:
        print("No users found. Create a user first.")
        return

    print(f"🧪 Testing wallet operations for user: {user.get_full_name()}")

    # 1. Get or create wallet
    wallet = WalletService.get_or_create_wallet(user)
    print(f"💰 Current balance: {wallet.balance} so'm")

    # 2. Check wallet info
    wallet_info = WalletService.get_wallet_info(user)
    print(f"📊 Wallet info: Balance={wallet_info['balance']}, Total spent={wallet_info['total_spent']}")

    # 3. Check if user can afford a service
    doctor_view_price = get_service_price('doctor_view')
    can_afford = check_user_balance(user, doctor_view_price)
    print(f"💳 Can afford doctor view ({doctor_view_price} so'm): {can_afford}")

    # 4. Add balance to wallet (manual topup)
    if wallet.balance < 10000:
        print("💵 Adding 50000 so'm to wallet...")
        WalletService.add_balance(user, Decimal('50000'), "Manual test topup")
        print(f"✅ New balance: {WalletService.get_or_create_wallet(user).balance} so'm")


def example_service_charging():
    """Example service charging operations"""

    user = User.objects.first()
    if not user:
        print("No users found. Create a user first.")
        return

    print(f"💸 Testing service charging for user: {user.get_full_name()}")

    # 1. Check if user can access doctor view service
    can_access, message = BillingService.can_access_service(user, 'doctor_view')
    print(f"🔍 Can access doctor view: {can_access} - {message}")

    # 2. Check service prices
    services = ['doctor_view', 'consultation', 'ai_diagnosis']
    for service in services:
        price = get_service_price(service)
        print(f"💰 {service}: {price} so'm")

    # 3. Charge for doctor view (if doctor exists)
    try:
        from apps.doctors.models import Doctor
        doctor = Doctor.objects.first()
        if doctor and can_access:
            print(f"💳 Charging for viewing doctor: {doctor.get_short_name()}")
            transaction = charge_user(
                user,
                'doctor_view',
                related_object=doctor,
                ip_address='127.0.0.1'
            )
            if transaction:
                print(f"✅ Charged {transaction.amount} so'm. New balance: {transaction.balance_after} so'm")
            else:
                print("✅ Free view used - no charge")
    except ImportError:
        print("⚠️ Doctor model not available for testing")


def example_payment_topup():
    """Example payment and wallet topup"""

    user = User.objects.first()
    if not user:
        print("No users found. Create a user first.")
        return

    print(f"🏦 Testing payment topup for user: {user.get_full_name()}")

    # 1. Check available payment gateways
    gateways = PaymentGateway.objects.filter(is_active=True)
    print(f"💳 Available gateways: {[g.display_name for g in gateways]}")

    if not gateways.exists():
        print("⚠️ No active payment gateways found. Create one first.")
        return

    gateway = gateways.first()

    # 2. Create a wallet topup payment
    try:
        amount = Decimal('25000')
        print(f"💰 Creating topup payment: {amount} so'm via {gateway.display_name}")

        payment = PaymentBillingIntegration.create_wallet_topup_payment(
            user=user,
            amount=amount,
            gateway_name=gateway.name,
            ip_address='127.0.0.1'
        )

        print(f"✅ Payment created: {payment.reference_number}")
        print(f"📄 Details: {payment.amount} so'm + {payment.commission} commission = {payment.total_amount} total")

        # 3. Simulate payment completion (normally done by webhook)
        print("🔄 Simulating payment completion...")
        payment.mark_as_completed()

        # 4. Check wallet balance after topup
        updated_wallet = WalletService.get_or_create_wallet(user)
        print(f"✅ Payment completed! New wallet balance: {updated_wallet.balance} so'm")

    except Exception as e:
        print(f"❌ Error creating payment: {str(e)}")


def example_billing_summary():
    """Example billing summary"""

    user = User.objects.first()
    if not user:
        print("No users found. Create a user first.")
        return

    print(f"📊 Billing summary for user: {user.get_full_name()}")

    # Get 30-day billing summary
    summary = PaymentBillingIntegration.get_user_billing_summary(user, days=30)

    print(f"📈 Summary for last {summary['period_days']} days:")
    print(f"💰 Wallet - Current: {summary['wallet_info']['current_balance']} so'm")
    print(f"💳 Credited: {summary['wallet_info']['total_credited']} so'm")
    print(f"💸 Debited: {summary['wallet_info']['total_debited']} so'm")
    print(f"📊 Net change: {summary['net_change']} so'm")

    print(f"🏦 Payments - Total: {summary['payment_summary']['total_payments']}")
    print(f"✅ Completed: {summary['payment_summary']['completed_payments']}")
    print(f"💰 Total amount: {summary['payment_summary']['total_amount']} so'm")

    print(f"👨‍⚕️ Doctor views: {summary['service_summary']['doctor_views']}")
    print(f"💸 View charges: {summary['service_summary']['doctor_view_charges']} so'm")
    print(f"🆓 Free views: {summary['service_summary']['free_doctor_views']}")


def example_billing_settings():
    """Example billing settings management"""

    print("⚙️ Billing settings management")

    # Get current settings
    settings = BillingSettings.get_settings()
    print(f"🔧 Current settings:")
    print(f"   Billing enabled: {settings.enable_billing}")
    print(f"   Maintenance mode: {settings.maintenance_mode}")
    print(f"   Free views per day: {settings.free_views_per_day}")
    print(f"   Min wallet topup: {settings.min_wallet_topup} so'm")
    print(f"   Max wallet balance: {settings.max_wallet_balance} so'm")

    # Get billing rules
    rules = BillingRule.objects.filter(is_active=True)
    print(f"\n💰 Active billing rules:")
    for rule in rules:
        print(f"   {rule.get_service_type_display()}: {rule.price} so'm")
        if rule.discount_percentage > 0:
            print(f"     Discount: {rule.discount_percentage}% (min {rule.min_quantity_for_discount} qty)")


def run_all_examples():
    """Run all examples"""

    print("🚀 Running Payment-Billing Integration Examples")
    print("=" * 60)

    try:
        print("\n1. Wallet Operations")
        print("-" * 30)
        example_wallet_operations()

        print("\n2. Service Charging")
        print("-" * 30)
        example_service_charging()

        print("\n3. Payment Topup")
        print("-" * 30)
        example_payment_topup()

        print("\n4. Billing Summary")
        print("-" * 30)
        example_billing_summary()

        print("\n5. Billing Settings")
        print("-" * 30)
        example_billing_settings()

        print("\n✅ All examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()


# Quick utility functions for common operations
def quick_wallet_status(user_id):
    """Quick check of user wallet status"""
    try:
        user = User.objects.get(id=user_id)
        wallet = WalletService.get_or_create_wallet(user)
        print(f"👤 User: {user.get_full_name()}")
        print(f"💰 Balance: {wallet.balance} so'm")
        print(f"🚫 Blocked: {wallet.is_blocked}")
        return wallet
    except User.DoesNotExist:
        print(f"❌ User with ID {user_id} not found")
        return None


def quick_topup(user_id, amount):
    """Quick wallet topup"""
    try:
        user = User.objects.get(id=user_id)
        transaction = topup_wallet(user, Decimal(str(amount)))
        print(f"✅ Added {amount} so'm to {user.get_full_name()}'s wallet")
        print(f"💰 New balance: {transaction.balance_after} so'm")
        return transaction
    except User.DoesNotExist:
        print(f"❌ User with ID {user_id} not found")
        return None


def quick_service_price_check():
    """Quick check of all service prices"""
    services = ['doctor_view', 'consultation', 'chat_message', 'ai_diagnosis', 'prescription']
    print("💰 Current service prices:")
    for service in services:
        price = get_service_price(service)
        print(f"   {service}: {price} so'm")


if __name__ == "__main__":
    print("Payment-Billing Integration Usage Examples")
    print("Run individual functions or use run_all_examples()")
    print("\nAvailable functions:")
    print("- example_wallet_operations()")
    print("- example_service_charging()")
    print("- example_payment_topup()")
    print("- example_billing_summary()")
    print("- example_billing_settings()")
    print("- run_all_examples()")
    print("- quick_wallet_status(user_id)")
    print("- quick_topup(user_id, amount)")
    print("- quick_service_price_check()")
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from decimal import Decimal
import uuid
import json

User = get_user_model()


class PaymentGateway(models.Model):
    """Payment gateway configuration"""

    GATEWAY_TYPES = [
        ('click', 'Click'),
        ('payme', 'Payme'),
        ('uzcard', 'UzCard'),
        ('humo', 'Humo'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
    ]

    CURRENCY_CHOICES = [
        ('UZS', 'Uzbek Som'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('RUB', 'Russian Ruble'),
    ]

    name = models.CharField(
        max_length=50,
        choices=GATEWAY_TYPES,
        unique=True,
        verbose_name="To'lov tizimi nomi"
    )

    display_name = models.CharField(
        max_length=100,
        verbose_name="Ko'rsatiladigan nom"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Tavsif"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    is_test_mode = models.BooleanField(
        default=True,
        verbose_name="Test rejimi"
    )

    # Gateway configuration
    merchant_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Merchant ID"
    )

    service_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Service ID"
    )

    secret_key = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Secret Key"
    )

    public_key = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Public Key"
    )

    api_url = models.URLField(
        blank=True,
        verbose_name="API URL"
    )

    webhook_url = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Webhook URL"
    )

    # Gateway settings
    supported_currencies = models.JSONField(
        default=list,
        verbose_name="Qo'llab-quvvatlanadigan valyutalar"
    )

    default_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='UZS',
        verbose_name="Asosiy valyuta"
    )

    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1000.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Minimal to'lov miqdori"
    )

    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('10000000.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Maksimal to'lov miqdori"
    )

    # Commission settings
    commission_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Foiz'),
            ('fixed', 'Qat\'iy summa'),
            ('combined', 'Aralash'),
        ],
        default='percentage',
        verbose_name="Komissiya turi"
    )

    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="Komissiya foizi"
    )

    commission_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Qo'shimcha komissiya"
    )

    # Processing settings
    processing_time_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name="Qayta ishlash vaqti (daqiqa)"
    )

    auto_capture = models.BooleanField(
        default=True,
        verbose_name="Avtomatik yechish"
    )

    supports_refunds = models.BooleanField(
        default=True,
        verbose_name="Qaytarishni qo'llab-quvvatlaydi"
    )

    supports_recurring = models.BooleanField(
        default=False,
        verbose_name="Takroriy to'lovlarni qo'llab-quvvatlaydi"
    )

    # Display settings
    logo = models.ImageField(
        upload_to='payment_gateways/logos/',
        blank=True,
        null=True,
        verbose_name="Logo"
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Tartiblash"
    )

    # Additional configuration
    extra_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo'shimcha sozlamalar"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Oxirgi ishlatilgan vaqt"
    )

    class Meta:
        verbose_name = "To'lov tizimi"
        verbose_name_plural = "To'lov tizimlari"
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['is_active', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.display_name} ({'Test' if self.is_test_mode else 'Live'})"

    def clean(self):
        """Validate gateway configuration"""
        from django.core.exceptions import ValidationError

        if self.is_active:
            if not self.merchant_id and self.name in ['click', 'payme']:
                raise ValidationError("Merchant ID talab qilinadi")

            if not self.secret_key and self.name in ['click', 'payme']:
                raise ValidationError("Secret Key talab qilinadi")

    def calculate_commission(self, amount):
        """Calculate commission for given amount"""
        if self.commission_type == 'percentage':
            return (amount * self.commission_percentage) / 100
        elif self.commission_type == 'fixed':
            return self.commission_fixed
        elif self.commission_type == 'combined':
            percentage_commission = (amount * self.commission_percentage) / 100
            return percentage_commission + self.commission_fixed
        return Decimal('0.00')

    def get_total_amount(self, amount):
        """Get total amount including commission"""
        return amount + self.calculate_commission(amount)

    def is_amount_valid(self, amount):
        """Check if amount is within gateway limits"""
        return self.min_amount <= amount <= self.max_amount

    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class Payment(models.Model):
    """Payment transaction model"""

    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('processing', 'Qayta ishlanmoqda'),
        ('requires_action', 'Harakat talab qilinadi'),
        ('completed', 'Tugallangan'),
        ('failed', 'Muvaffaqiyatsiz'),
        ('cancelled', 'Bekor qilingan'),
        ('expired', 'Muddati tugagan'),
        ('refunded', 'Qaytarilgan'),
        ('partially_refunded', 'Qisman qaytarilgan'),
    ]

    PAYMENT_TYPES = [
        ('wallet_topup', 'Hamyon to\'ldirish'),
        ('consultation', 'Konsultatsiya to\'lovi'),
        ('doctor_view', 'Shifokor ko\'rish'),
        ('subscription', 'Obuna to\'lovi'),
        ('service', 'Xizmat to\'lovi'),
        ('refund', 'Qaytarish'),
    ]

    PAYMENT_METHODS = [
        ('card', 'Bank kartasi'),
        ('wallet', 'Elektron hamyon'),
        ('bank_transfer', 'Bank o\'tkazmasi'),
        ('cash', 'Naqd pul'),
        ('crypto', 'Kriptovalyuta'),
    ]

    # Primary fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Foydalanuvchi"
    )

    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="To'lov tizimi"
    )

    # Payment details
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='wallet_topup',
        verbose_name="To'lov turi"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='card',
        verbose_name="To'lov usuli"
    )

    # Amount fields
    currency = models.CharField(
        max_length=3,
        default='UZS',
        verbose_name="Valyuta"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Asosiy summa"
    )

    commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Komissiya"
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Chegirma"
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Jami summa"
    )

    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Holat",
        db_index=True
    )

    reference_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name="Havola raqami"
    )

    # Gateway specific fields
    gateway_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="Gateway tranzaksiya ID"
    )

    gateway_payment_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway to'lov ID"
    )

    gateway_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway havolasi"
    )

    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Gateway javobi"
    )

    gateway_error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Gateway xato kodi"
    )

    gateway_error_message = models.TextField(
        blank=True,
        verbose_name="Gateway xato xabari"
    )

    # URLs and callbacks
    payment_url = models.URLField(
        blank=True,
        max_length=500,
        verbose_name="To'lov URL"
    )

    success_url = models.URLField(
        blank=True,
        max_length=500,
        verbose_name="Muvaffaqiyat URL"
    )

    cancel_url = models.URLField(
        blank=True,
        max_length=500,
        verbose_name="Bekor qilish URL"
    )

    callback_url = models.URLField(
        blank=True,
        max_length=500,
        verbose_name="Callback URL"
    )

    # Metadata
    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Tavsif"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )

    # Client information
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP manzil"
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )

    client_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Mijoz ma'lumotlari"
    )

    # Related object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Bog'liq obyekt turi"
    )
    object_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Bog'liq obyekt ID"
    )
    related_object = GenericForeignKey('content_type', 'object_id')

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt",
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqt"
    )

    processing_started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Qayta ishlash boshlangan vaqt"
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Tugallangan vaqt"
    )

    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Muddati tugash vaqti",
        db_index=True
    )

    # Attempts tracking
    attempt_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Urinishlar soni"
    )

    max_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name="Maksimal urinishlar"
    )

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['gateway', 'status']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['payment_type', 'status']),
        ]

    def __str__(self):
        return f"Payment {self.reference_number} - {self.user.get_full_name()} - {self.total_amount} {self.currency}"

    def save(self, *args, **kwargs):
        # Generate reference number
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()

        # Calculate total amount
        if not self.total_amount:
            self.commission = self.gateway.calculate_commission(self.amount)
            self.total_amount = self.amount + self.commission - self.discount

        # Set expiration time
        if not self.expires_at and self.status == 'pending':
            self.expires_at = timezone.now() + timezone.timedelta(
                minutes=self.gateway.processing_time_minutes
            )

        super().save(*args, **kwargs)

    def generate_reference_number(self):
        """Generate unique reference number"""
        import time
        timestamp = str(int(time.time()))
        return f"PAY-{timestamp}-{str(self.id)[:8].upper()}"

    def mark_as_processing(self):
        """Mark payment as processing"""
        self.status = 'processing'
        self.processing_started_at = timezone.now()
        self.attempt_count += 1
        self.save(update_fields=['status', 'processing_started_at', 'attempt_count', 'updated_at'])

    def mark_as_completed(self, gateway_transaction_id=None):
        """Mark payment as completed"""
        with models.transaction.atomic():
            self.status = 'completed'
            self.completed_at = timezone.now()
            if gateway_transaction_id:
                self.gateway_transaction_id = gateway_transaction_id
            self.save(update_fields=['status', 'completed_at', 'gateway_transaction_id', 'updated_at'])

            # Update user wallet if it's a topup
            if self.payment_type == 'wallet_topup':
                self.user.wallet.add_balance(
                    self.amount,
                    f"Hamyon to'ldirish - {self.gateway.display_name} - {self.reference_number}"
                )

            # Update gateway last used
            self.gateway.update_last_used()

    def mark_as_failed(self, error_code=None, error_message=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if error_code:
            self.gateway_error_code = error_code
        if error_message:
            self.gateway_error_message = error_message
        self.save(update_fields=[
            'status', 'gateway_error_code', 'gateway_error_message', 'updated_at'
        ])

    def mark_as_cancelled(self, reason=None):
        """Mark payment as cancelled"""
        self.status = 'cancelled'
        if reason:
            self.metadata['cancellation_reason'] = reason
        self.save(update_fields=['status', 'metadata', 'updated_at'])

    def is_expired(self):
        """Check if payment is expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def can_be_refunded(self):
        """Check if payment can be refunded"""
        return (
                self.status == 'completed' and
                self.gateway.supports_refunds and
                not self.is_fully_refunded()
        )

    def is_fully_refunded(self):
        """Check if payment is fully refunded"""
        total_refunded = self.refunds.filter(
            status='completed'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        return total_refunded >= self.amount

    def get_refunded_amount(self):
        """Get total refunded amount"""
        return self.refunds.filter(
            status='completed'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

    def get_refundable_amount(self):
        """Get amount that can still be refunded"""
        return self.amount - self.get_refunded_amount()

    def can_retry(self):
        """Check if payment can be retried"""
        return (
                self.status in ['failed', 'expired'] and
                self.attempt_count < self.max_attempts
        )


class PaymentWebhook(models.Model):
    """Payment webhook logs for debugging and audit"""

    WEBHOOK_TYPES = [
        ('payment_created', 'To\'lov yaratildi'),
        ('payment_completed', 'To\'lov tugallandi'),
        ('payment_failed', 'To\'lov muvaffaqiyatsiz'),
        ('payment_cancelled', 'To\'lov bekor qilindi'),
        ('refund_created', 'Qaytarish yaratildi'),
        ('refund_completed', 'Qaytarish tugallandi'),
        ('other', 'Boshqa'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='webhooks',
        blank=True,
        null=True,
        verbose_name="To'lov"
    )

    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.CASCADE,
        related_name='webhooks',
        verbose_name="To'lov tizimi"
    )

    webhook_type = models.CharField(
        max_length=20,
        choices=WEBHOOK_TYPES,
        default='other',
        verbose_name="Webhook turi"
    )

    # Request data
    request_method = models.CharField(
        max_length=10,
        default='POST',
        verbose_name="So'rov usuli"
    )

    request_headers = models.JSONField(
        default=dict,
        verbose_name="So'rov sarlavhalari"
    )

    request_body = models.JSONField(
        default=dict,
        verbose_name="So'rov ma'lumotlari"
    )

    raw_body = models.TextField(
        blank=True,
        verbose_name="Xom ma'lumotlar"
    )

    # Response data
    response_status = models.PositiveIntegerField(
        default=200,
        verbose_name="Javob holati"
    )

    response_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Javob ma'lumotlari"
    )

    # Processing info
    ip_address = models.GenericIPAddressField(
        verbose_name="IP manzil"
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )

    signature_valid = models.BooleanField(
        default=False,
        verbose_name="Imzo to'g'ri"
    )

    processed = models.BooleanField(
        default=False,
        verbose_name="Qayta ishlangan"
    )

    processing_time_ms = models.PositiveIntegerField(
        default=0,
        verbose_name="Qayta ishlash vaqti (ms)"
    )

    processing_result = models.TextField(
        blank=True,
        verbose_name="Qayta ishlash natijasi"
    )

    error_message = models.TextField(
        blank=True,
        verbose_name="Xato xabari"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qabul qilingan vaqt"
    )

    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Qayta ishlangan vaqt"
    )

    class Meta:
        verbose_name = "Payment Webhook"
        verbose_name_plural = "Payment Webhooks"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gateway', 'created_at']),
            models.Index(fields=['processed', 'created_at']),
            models.Index(fields=['webhook_type', 'created_at']),
        ]

    def __str__(self):
        return f"Webhook {self.webhook_type} - {self.gateway.display_name} - {self.created_at}"

    def mark_as_processed(self, result=None, processing_time=None):
        """Mark webhook as processed"""
        self.processed = True
        self.processed_at = timezone.now()
        if result:
            self.processing_result = str(result)
        if processing_time:
            self.processing_time_ms = processing_time
        self.save(update_fields=[
            'processed', 'processed_at', 'processing_result', 'processing_time_ms'
        ])


class ClickTransaction(models.Model):
    """Click specific transaction data"""

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='click_transaction',
        verbose_name="To'lov"
    )

    # Click specific fields
    click_trans_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Click Transaction ID"
    )

    click_paydoc_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Click Paydoc ID"
    )

    merchant_trans_id = models.CharField(
        max_length=100,
        verbose_name="Merchant Transaction ID"
    )

    service_id = models.CharField(
        max_length=50,
        verbose_name="Service ID"
    )

    merchant_prepare_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Merchant Prepare ID"
    )

    merchant_confirm_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Merchant Confirm ID"
    )

    # Timestamps from Click
    sign_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Sign Time"
    )

    # Error handling
    error_code = models.IntegerField(
        default=0,
        verbose_name="Error Code"
    )

    error_note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Error Note"
    )

    # Additional data
    card_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Karta turi"
    )

    card_number_masked = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Karta raqami (yashirilgan)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Click Transaction"
        verbose_name_plural = "Click Transactions"
        indexes = [
            models.Index(fields=['click_trans_id']),
            models.Index(fields=['merchant_trans_id']),
        ]

    def __str__(self):
        return f"Click {self.click_trans_id} - {self.payment.amount} {self.payment.currency}"


class PaymeTransaction(models.Model):
    """Payme specific transaction data"""

    PAYME_STATES = [
        (1, 'Yaratilgan'),
        (2, 'Tugallangan'),
        (-1, 'Bekor qilingan (yaratish)'),
        (-2, 'Bekor qilingan (tugallash)'),
    ]

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='payme_transaction',
        verbose_name="To'lov"
    )

    # Payme specific fields
    payme_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Payme Transaction ID"
    )

    # Payme timestamps (in milliseconds)
    payme_time = models.BigIntegerField(
        verbose_name="Payme Time"
    )

    create_time = models.BigIntegerField(
        verbose_name="Create Time"
    )

    perform_time = models.BigIntegerField(
        default=0,
        verbose_name="Perform Time"
    )

    cancel_time = models.BigIntegerField(
        default=0,
        verbose_name="Cancel Time"
    )

    # Transaction state
    state = models.IntegerField(
        choices=PAYME_STATES,
        default=1,
        verbose_name="Holat"
    )

    reason = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Sabab kodi"
    )

    # Account information
    account = models.JSONField(
        default=dict,
        verbose_name="Hisob ma'lumotlari"
    )

    # Receivers information
    receivers = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Qabul qiluvchilar"
    )

    # Additional Payme data
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payme Transaction"
        verbose_name_plural = "Payme Transactions"
        indexes = [
            models.Index(fields=['payme_id']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return f"Payme {self.payme_id} - {self.get_state_display()} - {self.payment.amount} {self.payment.currency}"

    def get_payme_time_as_datetime(self):
        """Convert Payme time to datetime"""
        if self.payme_time:
            return timezone.datetime.fromtimestamp(self.payme_time / 1000)
        return None

    def get_create_time_as_datetime(self):
        """Convert create time to datetime"""
        if self.create_time:
            return timezone.datetime.fromtimestamp(self.create_time / 1000)
        return None


class PaymentMethod(models.Model):
    """User saved payment methods"""

    METHOD_TYPES = [
        ('card', 'Bank kartasi'),
        ('wallet', 'Elektron hamyon'),
        ('bank_account', 'Bank hisobi'),
        ('mobile_money', 'Mobil pul'),
    ]

    CARD_TYPES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('uzcard', 'UzCard'),
        ('humo', 'Humo'),
        ('unionpay', 'UnionPay'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name="Foydalanuvchi"
    )

    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.CASCADE,
        related_name='saved_methods',
        verbose_name="To'lov tizimi"
    )

    # Method details
    method_type = models.CharField(
        max_length=20,
        choices=METHOD_TYPES,
        default='card',
        verbose_name="Usul turi"
    )

    nickname = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Taxallus"
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="Asosiy usul"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    # Card specific fields
    card_type = models.CharField(
        max_length=20,
        choices=CARD_TYPES,
        blank=True,
        verbose_name="Karta turi"
    )

    card_number_masked = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Karta raqami (yashirilgan)"
    )

    card_holder_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Karta egasi"
    )

    expiry_month = models.CharField(
        max_length=2,
        blank=True,
        verbose_name="Tugash oyi"
    )

    expiry_year = models.CharField(
        max_length=4,
        blank=True,
        verbose_name="Tugash yili"
    )

    # Bank account fields
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bank nomi"
    )

    account_number_masked = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Hisob raqami (yashirilgan)"
    )

    # Gateway specific data
    gateway_token = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Gateway token"
    )

    gateway_customer_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway mijoz ID"
    )

    gateway_method_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway usul ID"
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )

    # Usage tracking
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Ishlatilgan soni"
    )

    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Oxirgi ishlatilgan"
    )

    # Verification
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Tasdiqlangan"
    )

    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Tasdiqlangan vaqt"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Muddati tugash vaqti"
    )

    class Meta:
        verbose_name = "To'lov usuli"
        verbose_name_plural = "To'lov usullari"
        ordering = ['-is_default', '-last_used_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['gateway', 'is_active']),
            models.Index(fields=['gateway_token']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_payment_method_per_user'
            )
        ]

    def __str__(self):
        if self.nickname:
            return f"{self.nickname} ({self.gateway.display_name})"
        elif self.card_number_masked:
            return f"{self.gateway.display_name} - {self.card_number_masked}"
        else:
            return f"{self.gateway.display_name} - {self.get_method_type_display()}"

    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

        # Generate nickname if not provided
        if not self.nickname and self.card_number_masked:
            self.nickname = f"{self.get_card_type_display()} {self.card_number_masked}"

        super().save(*args, **kwargs)

    def update_usage(self):
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])

    def is_expired(self):
        """Check if payment method is expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True

        # Check card expiry
        if self.method_type == 'card' and self.expiry_month and self.expiry_year:
            try:
                expiry_date = timezone.datetime(
                    int(self.expiry_year),
                    int(self.expiry_month),
                    1
                )
                return timezone.now() > expiry_date
            except (ValueError, TypeError):
                pass

        return False


class PaymentRefund(models.Model):
    """Payment refund management"""

    REFUND_STATUS = [
        ('pending', 'Kutilmoqda'),
        ('processing', 'Qayta ishlanmoqda'),
        ('completed', 'Tugallangan'),
        ('failed', 'Muvaffaqiyatsiz'),
        ('cancelled', 'Bekor qilingan'),
        ('rejected', 'Rad etilgan'),
    ]

    REFUND_REASONS = [
        ('user_request', 'Foydalanuvchi so\'rovi'),
        ('duplicate_payment', 'Takroriy to\'lov'),
        ('fraudulent', 'Firibgarlik'),
        ('system_error', 'Tizim xatoligi'),
        ('service_unavailable', 'Xizmat mavjud emas'),
        ('quality_issue', 'Sifat muammosi'),
        ('admin_action', 'Administrator amali'),
        ('chargeback', 'Chargeback'),
        ('other', 'Boshqa'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds',
        verbose_name="To'lov"
    )

    # Refund details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Qaytariladigan summa"
    )

    currency = models.CharField(
        max_length=3,
        verbose_name="Valyuta"
    )

    reason = models.CharField(
        max_length=20,
        choices=REFUND_REASONS,
        verbose_name="Sabab"
    )

    reason_description = models.TextField(
        blank=True,
        verbose_name="Sabab tavsifi"
    )

    status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS,
        default='pending',
        verbose_name="Holat"
    )

    # Gateway integration
    gateway_refund_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway refund ID"
    )

    gateway_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway havolasi"
    )

    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Gateway javobi"
    )

    gateway_error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Gateway xato kodi"
    )

    gateway_error_message = models.TextField(
        blank=True,
        verbose_name="Gateway xato xabari"
    )

    # Processing information
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='requested_refunds',
        verbose_name="So'ragan foydalanuvchi"
    )

    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='processed_refunds',
        verbose_name="Qayta ishlagan foydalanuvchi"
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_refunds',
        verbose_name="Tasdiqlagan foydalanuvchi"
    )

    # Notes and communication
    internal_notes = models.TextField(
        blank=True,
        verbose_name="Ichki izohlar"
    )

    customer_notes = models.TextField(
        blank=True,
        verbose_name="Mijoz izohlari"
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Qayta ishlangan vaqt"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Tugallangan vaqt"
    )

    class Meta:
        verbose_name = "To'lov qaytarish"
        verbose_name_plural = "To'lov qaytarishlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['gateway_refund_id']),
        ]

    def __str__(self):
        return f"Refund {str(self.id)[:8]} - {self.amount} {self.currency} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Set currency from payment
        if not self.currency and self.payment:
            self.currency = self.payment.currency

        super().save(*args, **kwargs)

    def can_be_processed(self):
        """Check if refund can be processed"""
        return self.status == 'pending' and self.payment.can_be_refunded()

    def process_refund(self, processed_by=None):
        """Process the refund"""
        if not self.can_be_processed():
            raise ValueError("Refund cannot be processed")

        with models.transaction.atomic():
            self.status = 'completed'
            self.processed_by = processed_by
            self.processed_at = timezone.now()
            self.completed_at = timezone.now()
            self.save()

            # Add amount back to user wallet
            self.payment.user.wallet.add_balance(
                self.amount,
                f"To'lov qaytarish - {self.payment.gateway.display_name} - {self.payment.reference_number}"
            )

            # Update payment status if fully refunded
            if self.payment.is_fully_refunded():
                self.payment.status = 'refunded'
                self.payment.save(update_fields=['status', 'updated_at'])
            elif self.payment.get_refunded_amount() > 0:
                self.payment.status = 'partially_refunded'
                self.payment.save(update_fields=['status', 'updated_at'])

    def approve(self, approved_by=None):
        """Approve the refund"""
        self.approved_by = approved_by
        self.status = 'processing'
        self.save(update_fields=['approved_by', 'status', 'updated_at'])

    def reject(self, reason=None, rejected_by=None):
        """Reject the refund"""
        self.status = 'rejected'
        if reason:
            self.internal_notes = f"Rejected: {reason}"
        if rejected_by:
            self.processed_by = rejected_by
            self.processed_at = timezone.now()
        self.save()


class PaymentDispute(models.Model):
    """Payment dispute management"""

    DISPUTE_STATUS = [
        ('opened', 'Ochilgan'),
        ('under_review', 'Ko\'rib chiqilmoqda'),
        ('evidence_required', 'Dalil talab qilinadi'),
        ('responded', 'Javob berilgan'),
        ('won', 'Yutilgan'),
        ('lost', 'Yutqazilgan'),
        ('accepted', 'Qabul qilingan'),
        ('closed', 'Yopilgan'),
    ]

    DISPUTE_REASONS = [
        ('fraud', 'Firibgarlik'),
        ('authorization', 'Ruxsat berish'),
        ('duplicate', 'Takrorlash'),
        ('credit_not_processed', 'Kredit qayta ishlanmagan'),
        ('cancelled_recurring', 'Takroriy bekor qilingan'),
        ('product_not_received', 'Mahsulot olinmagan'),
        ('product_unacceptable', 'Mahsulot qabul qilinmaydi'),
        ('other', 'Boshqa'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='disputes',
        verbose_name="To'lov"
    )

    # Dispute details
    dispute_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nizo ID"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Nizoli summa"
    )

    currency = models.CharField(
        max_length=3,
        verbose_name="Valyuta"
    )

    reason = models.CharField(
        max_length=30,
        choices=DISPUTE_REASONS,
        verbose_name="Sabab"
    )

    status = models.CharField(
        max_length=20,
        choices=DISPUTE_STATUS,
        default='opened',
        verbose_name="Holat"
    )

    # Evidence and documentation
    evidence_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Dalil ma'lumotlari"
    )

    evidence_due_by = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Dalil muddati"
    )

    # Gateway information
    gateway_dispute_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Gateway nizo ID"
    )

    gateway_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Gateway ma'lumotlari"
    )

    # Communication
    description = models.TextField(
        blank=True,
        verbose_name="Tavsif"
    )

    customer_message = models.TextField(
        blank=True,
        verbose_name="Mijoz xabari"
    )

    response_message = models.TextField(
        blank=True,
        verbose_name="Javob xabari"
    )

    # Processing
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='handled_disputes',
        verbose_name="Yurituvchi"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Javob berilgan vaqt"
    )
    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Yopilgan vaqt"
    )

    class Meta:
        verbose_name = "To'lov nizosi"
        verbose_name_plural = "To'lov nizolari"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['dispute_id']),
            models.Index(fields=['gateway_dispute_id']),
        ]

    def __str__(self):
        return f"Dispute {self.dispute_id} - {self.amount} {self.currency} - {self.get_status_display()}"


# Utility functions and managers
class PaymentProcessor:
    """Utility class for payment processing"""

    @staticmethod
    def create_payment(user, gateway, amount, payment_type='wallet_topup', **kwargs):
        """Create a new payment with validation"""
        # Validate amount
        if not gateway.is_amount_valid(amount):
            raise ValueError(
                f"Amount must be between {gateway.min_amount} and {gateway.max_amount} {gateway.default_currency}"
            )

        # Create payment
        payment = Payment.objects.create(
            user=user,
            gateway=gateway,
            amount=amount,
            payment_type=payment_type,
            currency=gateway.default_currency,
            **kwargs
        )

        return payment

    @staticmethod
    def get_available_gateways(user=None, amount=None):
        """Get available payment gateways for user"""
        queryset = PaymentGateway.objects.filter(is_active=True)

        if amount:
            queryset = queryset.filter(
                min_amount__lte=amount,
                max_amount__gte=amount
            )

        return queryset.order_by('sort_order')

    @staticmethod
    def validate_payment_amount(gateway, amount):
        """Validate payment amount against gateway limits"""
        if not gateway.is_amount_valid(amount):
            raise ValueError(
                f"Amount must be between {gateway.min_amount} and {gateway.max_amount} {gateway.default_currency}"
            )
        return True

    @staticmethod
    def calculate_total_with_commission(gateway, amount):
        """Calculate total amount including commission"""
        commission = gateway.calculate_commission(amount)
        return {
            'amount': amount,
            'commission': commission,
            'total': amount + commission
        }


# Signal handlers
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """Handle payment post save actions"""
    if created:
        # Log payment creation
        import logging
        logger = logging.getLogger('apps.payments')
        logger.info(
            f"Payment created: {instance.reference_number} - {instance.user.get_full_name()} - {instance.total_amount} {instance.currency}")


@receiver(pre_save, sender=Payment)
def payment_pre_save(sender, instance, **kwargs):
    """Handle payment pre save actions"""
    # Check if status changed to expired
    if instance.pk:
        try:
            old_instance = Payment.objects.get(pk=instance.pk)
            if old_instance.status != 'expired' and instance.status == 'expired':
                # Log expiration
                import logging
                logger = logging.getLogger('apps.payments')
                logger.warning(f"Payment expired: {instance.reference_number}")
        except Payment.DoesNotExist:
            pass
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

User = get_user_model()


class UserWallet(models.Model):
    """User wallet for storing balance and managing payments"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name="Foydalanuvchi"
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Balans"
    )

    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Jami sarflangan"
    )

    total_topped_up = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Jami to'ldirilgan"
    )

    is_blocked = models.BooleanField(
        default=False,
        verbose_name="Bloklangan"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Foydalanuvchi hamyoni"
        verbose_name_plural = "Foydalanuvchi hamyonlari"

    def __str__(self):
        return f"{self.user.get_full_name} - {self.balance} so'm"

    def has_sufficient_balance(self, amount):
        """Check if user has sufficient balance"""
        return self.balance >= amount and not self.is_blocked

    def deduct_balance(self, amount, description=""):
        """Deduct amount from wallet"""
        if not self.has_sufficient_balance(amount):
            raise ValueError("Insufficient balance")

        balance_before = self.balance
        self.balance -= amount
        self.total_spent += amount
        self.save()

        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='debit',
            amount=amount,
            description=description,
            balance_before=balance_before,
            balance_after=self.balance
        )

    def add_balance(self, amount, description=""):
        """Add amount to wallet"""
        balance_before = self.balance
        self.balance += amount
        self.total_topped_up += amount
        self.save()

        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='credit',
            amount=amount,
            description=description,
            balance_before=balance_before,
            balance_after=self.balance
        )

        # Unblock doctor if balance topped up to more than 5000
        if self.balance > 5000 and self.user.user_type == 'doctor':
            try:
                doctor = self.user.doctor_profile
                if doctor.is_blocked:
                    doctor.is_blocked = False
                    doctor.save(update_fields=['is_blocked'])
            except Exception:
                pass  # User might not have doctor profile yet


class BillingRule(models.Model):
    """Configurable billing rules for different services"""

    SERVICE_TYPES = [
        ('doctor_view', 'Shifokor profilini ko\'rish'),
        ('consultation', 'Konsultatsiya'),
        ('chat_message', 'Chat xabar'),
        ('ai_diagnosis', 'AI diagnostika'),
        ('prescription', 'Retsept'),
    ]

    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPES,
        unique=True,
        verbose_name="Xizmat turi"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Narx (so'm)"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Tavsif"
    )

    # Discount rules
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="Chegirma foizi"
    )

    min_quantity_for_discount = models.PositiveIntegerField(
        default=1,
        verbose_name="Chegirma uchun minimal miqdor"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing qoidasi"
        verbose_name_plural = "Billing qoidalari"

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.price} so'm"

    def get_effective_price(self, quantity=1):
        """Get effective price considering discounts"""
        if quantity >= self.min_quantity_for_discount and self.discount_percentage > 0:
            discount_amount = (self.price * self.discount_percentage) / 100
            return self.price - discount_amount
        return self.price


class WalletTransaction(models.Model):
    """Wallet transaction history"""

    TRANSACTION_TYPES = [
        ('credit', 'Kredit (Qo\'shish)'),
        ('debit', 'Debit (Yechish)'),
    ]

    TRANSACTION_STATUS = [
        ('pending', 'Kutilmoqda'),
        ('completed', 'Tugallangan'),
        ('failed', 'Muvaffaqiyatsiz'),
        ('cancelled', 'Bekor qilingan'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wallet = models.ForeignKey(
        UserWallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Hamyon"
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        verbose_name="Tranzaksiya turi"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Summa"
    )

    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Oldingi balans"
    )

    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Keyingi balans"
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Tavsif"
    )

    status = models.CharField(
        max_length=10,
        choices=TRANSACTION_STATUS,
        default='completed',
        verbose_name="Holat"
    )

    # # Reference to related objects
    # content_type = models.ForeignKey(
    #     'contenttypes.ContentType',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True
    # )
    object_id = models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hamyon tranzaksiyasi"
        verbose_name_plural = "Hamyon tranzaksiyalari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.get_full_name()} - {self.transaction_type} - {self.amount} so'm"


class DoctorViewCharge(models.Model):
    """Track charges for viewing doctor profiles"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_view_charges',
        verbose_name="Foydalanuvchi"
    )

    doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.CASCADE,
        related_name='view_charges',
        verbose_name="Shifokor"
    )

    transaction = models.ForeignKey(
        WalletTransaction,
        on_delete=models.CASCADE,
        related_name='doctor_views',
        verbose_name="Tranzaksiya"
    )

    amount_charged = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="To'langan summa"
    )

    view_duration = models.DurationField(
        blank=True,
        null=True,
        verbose_name="Ko'rish davomiyligi"
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP manzil"
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Shifokor ko'rish to'lovi"
        verbose_name_plural = "Shifokor ko'rish to'lovlari"
        unique_together = ['user', 'doctor', 'created_at']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.doctor.full_name()} - {self.amount_charged} so'm"


class BillingSettings(models.Model):
    """Global billing settings"""

    free_views_per_day = models.PositiveIntegerField(
        default=3,
        verbose_name="Kunlik bepul ko'rishlar soni"
    )

    free_views_for_new_users = models.PositiveIntegerField(
        default=5,
        verbose_name="Yangi foydalanuvchilar uchun bepul ko'rishlar"
    )

    min_wallet_topup = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('10000.00'),
        verbose_name="Minimal hamyon to'ldirish"
    )

    max_wallet_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1000000.00'),
        verbose_name="Maksimal hamyon balansi"
    )

    enable_billing = models.BooleanField(
        default=True,
        verbose_name="Billing'ni yoqish"
    )

    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Texnik ishlar rejimi"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing sozlamalari"
        verbose_name_plural = "Billing sozlamalari"

    def __str__(self):
        return f"Billing Settings - {self.updated_at.strftime('%Y-%m-%d')}"

    @classmethod
    def get_settings(cls):
        """Get or create billing settings"""
        settings, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'free_views_per_day': 3,
                'free_views_for_new_users': 5,
                'min_wallet_topup': Decimal('10000.00'),
                'max_wallet_balance': Decimal('1000000.00'),
                'enable_billing': True,
                'maintenance_mode': False,
            }
        )
        return settings


# Signal handlers for automatic wallet creation
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create wallet for new users"""
    if created:
        UserWallet.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_wallet(sender, instance, **kwargs):
    """Ensure wallet exists for all users"""
    if not hasattr(instance, 'wallet'):
        UserWallet.objects.create(user=instance)
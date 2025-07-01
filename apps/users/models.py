from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from datetime import date


class User(AbstractUser):
    """Kengaytirilgan foydalanuvchi modeli"""

    GENDER_CHOICES = [
        ('M', 'Erkak'),
        ('F', 'Ayol'),
        ('O', 'Boshqa'),
    ]

    BLOOD_TYPES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]

    # Shaxsiy ma'lumotlar
    phone_regex = RegexValidator(
        regex=r'^\+998[0-9]{9}$',
        message="Telefon raqami +998xxxxxxxxx formatida bo'lishi kerak"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=13,
        unique=True,
        verbose_name="Telefon raqami"
    )

    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Tug'ilgan sana"
    )

    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name="Jins"
    )

    # Tibbiy ma'lumotlar
    blood_type = models.CharField(
        max_length=3,
        choices=BLOOD_TYPES,
        blank=True,
        null=True,
        verbose_name="Qon guruhi"
    )

    height = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(50), MaxValueValidator(250)],
        verbose_name="Bo'y (sm)"
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(10), MaxValueValidator(500)],
        verbose_name="Vazn (kg)"
    )

    allergies = models.TextField(
        blank=True,
        null=True,
        verbose_name="Allergiyalar"
    )

    chronic_diseases = models.TextField(
        blank=True,
        null=True,
        verbose_name="Surunkali kasalliklar"
    )

    current_medications = models.TextField(
        blank=True,
        null=True,
        verbose_name="Qabul qilinayotgan dorilar"
    )

    # Kontakt ma'lumotlar
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Favqulodda holat uchun aloqa - ism"
    )

    emergency_contact_phone = models.CharField(
        validators=[phone_regex],
        max_length=13,
        blank=True,
        null=True,
        verbose_name="Favqulodda holat uchun telefon"
    )

    emergency_contact_relation = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Qarindoshlik turi"
    )

    # Manzil
    region = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Viloyat/Shahar"
    )

    district = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tuman"
    )

    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="To'liq manzil"
    )

    # Profil rasmi
    avatar = models.ImageField(
        upload_to='users/avatars/',
        blank=True,
        null=True,
        verbose_name="Profil rasmi"
    )

    # Sozlamalar
    language = models.CharField(
        max_length=5,
        choices=[('uz', 'O\'zbek'), ('ru', 'Rus'), ('en', 'English')],
        default='uz',
        verbose_name="Til"
    )

    notifications_enabled = models.BooleanField(
        default=True,
        verbose_name="Bildirishnomalar yoqilgan"
    )

    email_notifications = models.BooleanField(
        default=True,
        verbose_name="Email bildirishnomalar"
    )

    sms_notifications = models.BooleanField(
        default=True,
        verbose_name="SMS bildirishnomalar"
    )

    # Meta ma'lumotlar
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ro'yxatdan o'tgan vaqt"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Oxirgi yangilanish"
    )

    last_login_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="Oxirgi kirish IP manzili"
    )

    is_profile_complete = models.BooleanField(
        default=False,
        verbose_name="Profil to'ldirilgan"
    )

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        if self.get_full_name():
            return f"{self.get_full_name()} ({self.phone})"
        return self.phone

    def get_age(self):
        """Yoshni hisoblash"""
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                    (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    def get_bmi(self):
        """BMI hisoblaash"""
        if self.height and self.weight:
            height_m = self.height / 100  # sm dan m ga
            bmi = float(self.weight) / (height_m ** 2)
            return round(bmi, 1)
        return None

    def get_bmi_category(self):
        """BMI toifasi"""
        bmi = self.get_bmi()
        if bmi:
            if bmi < 18.5:
                return "Kam vazn"
            elif 18.5 <= bmi < 25:
                return "Normal vazn"
            elif 25 <= bmi < 30:
                return "Ortiqcha vazn"
            else:
                return "Semizlik"
        return None

    def check_profile_completeness(self):
        """Profil to'liqligini tekshirish"""
        required_fields = [
            self.first_name, self.last_name, self.phone,
            self.birth_date, self.gender
        ]
        self.is_profile_complete = all(required_fields)
        self.save(update_fields=['is_profile_complete'])
        return self.is_profile_complete


class UserMedicalHistory(models.Model):
    """Foydalanuvchi tibbiy tarixi"""

    RECORD_TYPES = [
        ('diagnosis', 'Tashxis'),
        ('treatment', 'Davolash'),
        ('surgery', 'Operatsiya'),
        ('allergy', 'Allergiya'),
        ('medication', 'Dori'),
        ('test', 'Tahlil'),
        ('vaccination', 'Emlash'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='medical_history',
        verbose_name="Foydalanuvchi"
    )

    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPES,
        verbose_name="Yozuv turi"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Sarlavha"
    )

    description = models.TextField(
        verbose_name="Tavsif"
    )

    date_recorded = models.DateField(
        verbose_name="Sana"
    )

    doctor_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Shifokor ismi"
    )

    hospital_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Shifoxona nomi"
    )

    attachment = models.FileField(
        upload_to='users/medical_records/',
        blank=True,
        null=True,
        verbose_name="Fayl biriktirma"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan"
    )

    class Meta:
        verbose_name = "Tibbiy tarix"
        verbose_name_plural = "Tibbiy tarix"
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"


class UserPreferences(models.Model):
    """Foydalanuvchi parametrlari"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        verbose_name="Foydalanuvchi"
    )

    preferred_language = models.CharField(
        max_length=5,
        choices=[('uz', 'O\'zbek'), ('ru', 'Rus'), ('en', 'English')],
        default='uz',
        verbose_name="Afzal ko'rilgan til"
    )

    preferred_doctor_gender = models.CharField(
        max_length=1,
        choices=[('M', 'Erkak'), ('F', 'Ayol'), ('A', 'Ahamiyatsiz')],
        default='A',
        verbose_name="Afzal ko'rilgan shifokor jinsi"
    )

    max_consultation_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Maksimal konsultatsiya narxi"
    )

    preferred_consultation_time = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'Ertalab (08:00-12:00)'),
            ('afternoon', 'Tushdan keyin (12:00-17:00)'),
            ('evening', 'Kechqurun (17:00-20:00)'),
        ],
        default='morning',
        verbose_name="Afzal ko'rilgan konsultatsiya vaqti"
    )

    auto_save_history = models.BooleanField(
        default=True,
        verbose_name="Tarixni avtomatik saqlash"
    )

    share_data_for_research = models.BooleanField(
        default=False,
        verbose_name="Ma'lumotlarni tadqiqot uchun ulashish"
    )

    class Meta:
        verbose_name = "Foydalanuvchi parametrlari"
        verbose_name_plural = "Foydalanuvchi parametrlari"

    def __str__(self):
        return f"{self.user.get_full_name()} - Parametrlar"
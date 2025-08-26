from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import date

from apps.hospitals.models import Hospital


class CustomUserManager(BaseUserManager):
    """Custom user manager"""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username kiritilishi shart')

        user = self.model(**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, models.Model):
    """Kengaytirilgan foydalanuvchi modeli"""

    USER_TYPES = [
        ('patient', 'Bemor'),
        ('doctor', 'Shifokor'),
        ('admin', 'Administrator'),
        ('hospital_admin', 'Shifoxona administratori'),
    ]

    GENDER_CHOICES = [
        ('M', 'Erkak'),
        ('F', 'Ayol'),
        ('O', 'Boshqa'),
    ]

    BLOOD_TYPES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    LANGUAGES = [
        ('uz', "O'zbek"),
        ('ru', 'Rus'),
        ('en', 'Ingliz'),
    ]

    # Shaxsiy ma'lumotlar
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    phone = models.CharField(
        max_length=13,
        unique=True,
        validators=[RegexValidator(regex=r'^\+998\d{9}$', message='Telefon raqam noto\'g\'ri formatda')],
        verbose_name="Telefon raqam",
        help_text="Telefon raqam +998901234567 formatida bo'lishi kerak",
        error_messages={
            'unique': "Bu telefon raqam allaqachon ro'yxatdan o'tgan.",
            'blank': "Telefon raqam kiritilishi shart.",
            'null': "Telefon raqam kiritilishi shart."
        },
        null=True,
        blank=True,
    )
    email = models.EmailField(blank=True, null=True, verbose_name="Email")

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default='patient',
        verbose_name="Foydalanuvchi turi"
    )

    # Personal information
    first_name = models.CharField(max_length=50, verbose_name="Ism")
    last_name = models.CharField(max_length=50, verbose_name="Familiya")
    middle_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Otasining ismi")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Tug'ilgan sana")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Jins")
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True, verbose_name="Avatar")
    language = models.CharField(max_length=10, choices=LANGUAGES, default='uz', verbose_name="Til")


    # Tibbiy ma'lumotlar
    blood_type = models.CharField(max_length=5, choices=BLOOD_TYPES, blank=True, null=True, verbose_name="Qon guruhi")
    height = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(50), MaxValueValidator(250)],
        verbose_name="Bo'y (sm)"
    )
    weight = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(20), MaxValueValidator(300)],
        verbose_name="Vazn (kg)"
    )
    allergies = models.TextField(blank=True, null=True, verbose_name="Allergiyalar")
    chronic_diseases = models.TextField(blank=True, null=True, verbose_name="Surunkali kasalliklar")
    current_medications = models.TextField(blank=True, null=True, verbose_name="Hozirgi dorilar")

    # Address information
    region = models.ForeignKey('hospitals.Regions', on_delete=models.SET_NULL, blank=True, null=True,)
    district = models.ForeignKey('hospitals.Districts', on_delete=models.SET_NULL, blank=True, null=True,)
    address = models.TextField(blank=True, null=True, verbose_name="Manzil")

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True,
                                              verbose_name="Favqulodda aloqa ismi")
    emergency_contact_phone = models.CharField(max_length=13, blank=True, null=True,
                                               verbose_name="Favqulodda aloqa telefoni")
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True,
                                                  verbose_name="Favqulodda aloqa munosabati")

    # Settings
    notifications_enabled = models.BooleanField(default=True, verbose_name="Bildirishnomalar")
    email_notifications = models.BooleanField(default=True, verbose_name="Email bildirishnomalar")
    sms_notifications = models.BooleanField(default=True, verbose_name="SMS bildirishnomalar")

    # System fields
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    is_staff = models.BooleanField(default=False, verbose_name="Xodim")
    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlangan")
    is_profile_complete = models.BooleanField(default=False, verbose_name="Profil to'liq")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="Oxirgi kirish IP")

    # Doctor-specific approval fields
    is_approved_by_admin = models.BooleanField(default=False, verbose_name="Admin tomonidan tasdiqlangan")
    approval_date = models.DateTimeField(blank=True, null=True, verbose_name="Tasdiq sanasi")
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_users',
        verbose_name="Kim tomonidan tasdiqlangan"
    )

    # Hospital relationship (for hospitals admins and doctors)
    managed_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='administrators',
        verbose_name="Boshqariladigan shifoxona"
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'user_type']

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone})"

    def get_full_name(self):
        """To'liq ismni qaytarish"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.phone

    def get_age(self):
        """Yoshni hisoblash"""
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                        (today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

    def get_bmi(self):
        """BMI hisoblash"""
        if self.height and self.weight:
            return round(self.weight / ((self.height / 100) ** 2), 1)
        return None

    def get_bmi_category(self):
        """BMI kategoriyasini aniqlash"""
        bmi = self.get_bmi()
        if not bmi:
            return None

        if bmi < 18.5:
            return "Kam vazn"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Ortiqcha vazn"
        else:
            return "Semizlik"

    def is_doctor(self):
        """Doctor ekanligini tekshirish"""
        return self.user_type == 'doctor'

    def is_admin(self):
        """Admin ekanligini tekshirish"""
        return self.user_type == 'admin'

    def is_hospital_admin(self):
        """Hospital admin ekanligini tekshirish"""
        return self.user_type == 'hospital_admin'

    def is_patient(self):
        """Patient ekanligini tekshirish"""
        return self.user_type == 'patient'

    def can_manage_doctors(self):
        """Doctor boshqara oladimi"""
        return self.user_type in ['admin', 'hospital_admin']

    def approve_doctor(self, doctor_user, approved_by):
        """Doctorni tasdiqlash"""
        if self.user_type == 'admin':
            doctor_user.is_approved_by_admin = True
            doctor_user.approval_date = timezone.now()
            doctor_user.approved_by = approved_by
            doctor_user.is_verified = True
            doctor_user.save()
            return True
        return False

    def check_profile_completeness(self):
        """Profil to'liqligini tekshirish"""
        required_fields = [self.first_name, self.last_name, self.phone]

        if self.user_type == 'doctor':
            # Doctor uchun qo'shimcha talablar
            required_fields.extend([self.birth_date, self.gender])

        is_complete = all(required_fields)

        # CRITICAL FIX: Only update if the value actually changed
        if self.is_profile_complete != is_complete:
            self.is_profile_complete = is_complete
            # Use update_fields to prevent calling the full save method again
            super(User, self).save(update_fields=['is_profile_complete'])

        return self.is_profile_complete



    def save(self, *args, **kwargs):
        # Username avtomatik yaratish
        if not self.username:
            print(self.__dict__)
            raise ValueError("Username kiritilishi shart")

        # CRITICAL FIX: Avoid recursion by checking if we're already in a save operation
        # Check if update_fields is specified (means we're in a recursive call)
        updating_profile_complete = kwargs.get('update_fields') == ['is_profile_complete']

        if not updating_profile_complete:
            # Only check profile completeness if this is not a recursive call
            if self.pk:  # Existing user
                # Calculate profile completeness without saving
                required_fields = [self.first_name, self.last_name, self.phone]
                if self.user_type == 'doctor':
                    required_fields.extend([self.birth_date, self.gender])
                self.is_profile_complete = all(required_fields)

        # Call the parent save method
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        """Parolni o'rnatish va username ni telefon raqamga moslashtirish"""
        self.password = make_password(raw_password)
        self.save()



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

    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Tavsif")
    date_recorded = models.DateField(verbose_name="Sana")
    doctor_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shifokor ismi")
    hospital_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Shifoxona nomi")
    attachment = models.FileField(upload_to='users/medical_records/', blank=True, null=True,
                                  verbose_name="Fayl biriktirma")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Tibbiy tarix"
        verbose_name_plural = "Tibbiy tarix"
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"


class UserPreferences(models.Model):
    """Foydalanuvchi parametrlari"""

    DOCTOR_GENDER_PREFERENCES = [
        ('any', 'Farqi yo\'q'),
        ('male', 'Erkak shifokor'),
        ('female', 'Ayol shifokor'),
    ]

    CONSULTATION_TIME_PREFERENCES = [
        ('morning', 'Ertalab (08:00-12:00)'),
        ('afternoon', 'Tushdan keyin (12:00-17:00)'),
        ('evening', 'Kechqurun (17:00-20:00)'),
        ('any', 'Istalgan vaqt'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        verbose_name="Foydalanuvchi"
    )

    preferred_language = models.CharField(
        max_length=10,
        choices=User.LANGUAGES,
        default='uz',
        verbose_name="Afzal til"
    )

    preferred_doctor_gender = models.CharField(
        max_length=10,
        choices=DOCTOR_GENDER_PREFERENCES,
        default='any',
        verbose_name="Afzal shifokor jinsi"
    )

    max_consultation_price = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Maksimal konsultatsiya narxi"
    )

    preferred_consultation_time = models.CharField(
        max_length=20,
        choices=CONSULTATION_TIME_PREFERENCES,
        default='any',
        verbose_name="Afzal konsultatsiya vaqti"
    )

    auto_save_history = models.BooleanField(
        default=True,
        verbose_name="Avtomatik tarix saqlash"
    )

    share_data_for_research = models.BooleanField(
        default=False,
        verbose_name="Tadqiqot uchun ma'lumot ulashish"
    )

    class Meta:
        verbose_name = "Foydalanuvchi parametrlari"
        verbose_name_plural = "Foydalanuvchi parametrlari"

    def __str__(self):
        return f"{self.user.get_full_name()} - Parametrlar"


# Signal for creating user preferences automatically
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Yangi user yaratilganda preferences ham yaratish"""
    if created:
        UserPreferences.objects.create(user=instance)
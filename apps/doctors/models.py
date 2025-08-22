# apps/doctors/models.py - Enhanced Doctor Model
from typing import List

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.contrib.auth import get_user_model

from django.utils import timezone

User = get_user_model()


class Doctor(models.Model):
    """Shifokorlar modeli - User model bilan bog'langan"""

    SPECIALTIES = [
        ('terapevt', 'Terapevt'),
        ('stomatolog', 'Stomatolog'),
        ('kardiolog', 'Kardiolog'),
        ('urolog', 'Urolog'),
        ('ginekolog', 'Ginekolog'),
        ('pediatr', 'Pediatr'),
        ('dermatolog', 'Dermatolog'),
        ('nevrolog', 'Nevrolog'),
        ('oftalmolog', 'Oftalmolog'),
        ('lor', 'LOR (Quloq-Burun-Tomoq)'),
        ('ortoped', 'Ortoped'),
        ('psixiatr', 'Psixiatr'),
        ('endokrinolog', 'Endokrinolog'),
        ('gastroenterolog', 'Gastroenterolog'),
        ('pulmonolog', 'Pulmonolog'),
    ]

    DEGREES = [
        ('oliy', 'Oliy toifa'),
        ('birinchi', 'Birinchi toifa'),
        ('ikkinchi', 'Ikkinchi toifa'),
        ('yoshlar', 'Yoshlar toifasi'),
    ]

    VERIFICATION_STATUS = [
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
        ('suspended', "To'xtatilgan"),
    ]

    # User relationship (One-to-One)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        verbose_name="Foydalanuvchi"
    )

    # Hospital relationship
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='doctors',
        verbose_name="Shifoxona"
    )

    # Professional information
    specialty = models.CharField(
        max_length=50,
        choices=SPECIALTIES,
        verbose_name="Mutaxassislik"
    )

    degree = models.CharField(
        max_length=20,
        choices=DEGREES,
        default='yoshlar',
        verbose_name="Toifa"
    )

    experience = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        verbose_name="Tajriba (yil)"
    )

    license_number = models.CharField(
        max_length=50,
        verbose_name="Litsenziya raqami",
        blank=True,
        null=True,
    )

    education = models.TextField(verbose_name="Ta'lim")
    achievements = models.TextField(blank=True, null=True, verbose_name="Yutuqlar")
    bio = models.TextField(blank=True, null=True, verbose_name="Biografiya")

    # Work information
    workplace = models.CharField(max_length=200, verbose_name="Ish joyi")
    workplace_address = models.TextField(blank=True, null=True, verbose_name="Ish joyi manzili")
    consultation_price = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Konsultatsiya narxi"
    )

    # # Professional documents
    # diploma_image = models.FileField(
    #     upload_to='doctors/diplomas/',
    #     blank=True,
    #     null=True,
    #     verbose_name="Diploma rasmi"
    # )
    #
    # license_image = models.ImageField(
    #     upload_to='doctors/licenses/',
    #     blank=True,
    #     null=True,
    #     verbose_name="Litsenziya rasmi"
    # )
    #
    # certificate_images = models.JSONField(
    #     default=list,
    #     blank=True,
    #     verbose_name="Sertifikat rasmlari"
    # )

    # Schedule and availability
    is_available = models.BooleanField(default=True, verbose_name="Mavjud")
    is_online_consultation = models.BooleanField(default=True, verbose_name="Online konsultatsiya")

    work_start_time = models.TimeField(blank=True, null=True, verbose_name="Ish boshlanish vaqti")
    work_end_time = models.TimeField(blank=True, null=True, verbose_name="Ish tugash vaqti")
    work_days = models.JSONField(
        default=list,
        verbose_name="Ish kunlari",
        help_text="Masalan: ['monday', 'tuesday', 'wednesday']"
    )

    # Verification and approval
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='pending',
        verbose_name="Tasdiq holati"
    )

    verification_documents_submitted = models.BooleanField(
        default=False,
        verbose_name="Hujjatlar topshirilgan"
    )

    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Admin eslatmalari"
    )

    # Statistics and ratings
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Reyting"
    )

    total_reviews = models.PositiveIntegerField(default=0, verbose_name="Jami sharhlar")
    total_consultations = models.PositiveIntegerField(default=0, verbose_name="Jami konsultatsiyalar")
    successful_consultations = models.PositiveIntegerField(default=0, verbose_name="Muvaffaqiyatli konsultatsiyalar")

    # View statistics
    profile_views = models.PositiveIntegerField(default=0, verbose_name="Profil ko'rishlar")
    weekly_views = models.PositiveIntegerField(default=0, verbose_name="Haftalik ko'rishlar")
    monthly_views = models.PositiveIntegerField(default=0, verbose_name="Oylik ko'rishlar")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")
    last_activity = models.DateTimeField(blank=True, null=True, verbose_name="Oxirgi faollik")

    class Meta:
        verbose_name = "Shifokor"
        verbose_name_plural = "Shifokorlar"
        ordering = ['-rating', '-total_reviews', 'user__last_name']
        indexes = [
            models.Index(fields=['specialty']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['is_available']),
            models.Index(fields=['rating']),
            models.Index(fields=['hospital']),
        ]

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.get_specialty_display()}"

    def get_absolute_url(self):
        return reverse('doctors:detail', kwargs={'pk': self.pk})

    @property
    def full_name(self):
        """Doctor to'liq ismi"""
        return self.user.get_full_name()

    @property
    def phone(self):
        """Doctor telefon raqami"""
        return self.user.phone

    @property
    def email(self):
        """Doctor email manzili"""
        return self.user.email

    @property
    def is_verified(self):
        """Doctor tasdiqlanganmi"""
        return self.verification_status == 'approved' and self.user.is_verified

    @property
    def success_rate(self):
        """Muvaffaqiyat foizi"""
        if self.total_consultations > 0:
            return round((self.successful_consultations / self.total_consultations) * 100, 1)
        return 0

    def increment_profile_views(self):
        """Profil ko'rishlarni oshirish"""
        self.profile_views += 1
        self.weekly_views += 1
        self.monthly_views += 1
        self.save(update_fields=['profile_views', 'weekly_views', 'monthly_views'])

    def reset_weekly_views(self):
        """Haftalik ko'rishlarni reset qilish"""
        self.weekly_views = 0
        self.save(update_fields=['weekly_views'])

    def reset_monthly_views(self):
        """Oylik ko'rishlarni reset qilish"""
        self.monthly_views = 0
        self.save(update_fields=['monthly_views'])

    def update_rating(self):
        """Reytingni yangilash"""
        from apps.consultations.models import Review
        reviews = Review.objects.filter(doctor=self, is_active=True)

        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(avg_rating, 1)
            self.total_reviews = reviews.count()
        else:
            self.rating = 0.0
            self.total_reviews = 0

        self.save(update_fields=['rating', 'total_reviews'])

    def update_consultation_stats(self):
        """Konsultatsiya statistikalarini yangilash"""
        from apps.consultations.models import Consultation

        consultations = Consultation.objects.filter(doctor=self)
        self.total_consultations = consultations.count()
        self.successful_consultations = consultations.filter(
            status__in=['completed', 'successful']
        ).count()

        self.save(update_fields=['total_consultations', 'successful_consultations'])

    def can_take_consultation(self):
        """Konsultatsiya qabul qila oladimi"""
        return (
                self.is_available and
                self.is_verified and
                self.user.is_active and
                self.verification_status == 'approved'
        )

    def approve(self, approved_by):
        """Doctorni tasdiqlash"""
        self.verification_status = 'approved'
        self.user.is_verified = True
        self.user.is_approved_by_admin = True
        self.user.approved_by = approved_by
        self.user.approval_date = timezone.now()

        self.save()
        self.user.save()

    def reject(self, reason=""):
        """Doctorni rad etish"""
        self.verification_status = 'rejected'
        if reason:
            self.admin_notes = reason
        self.save()

    def suspend(self, reason=""):
        """Doctorni to'xtatish"""
        self.verification_status = 'suspended'
        self.is_available = False
        if reason:
            self.admin_notes = reason
        self.save()

    def get_translated_field(self, field_name: str, language: str = None) -> str:
        """Get translated field value"""
        if not language:
            # Use default language from settings or user preference
            language = getattr(settings, 'LANGUAGE_CODE', 'uzn_Latn')

        try:
            translation = self.translations
            return translation.get_translation(field_name, language,
                                               fallback=getattr(self, field_name, ''))
        except DoctorTranslation.DoesNotExist:
            return getattr(self, field_name, '')

    def get_bio_translated(self, language: str = 'uzn_Latn') -> str:
        """Get translated bio"""
        return self.get_translated_field('bio', language)

    def get_education_translated(self, language: str = 'uzn_Latn') -> str:
        """Get translated education"""
        return self.get_translated_field('education', language)

    def get_achievements_translated(self, language: str = 'uzn_Latn') -> str:
        """Get translated achievements"""
        return self.get_translated_field('achievements', language)

    def get_workplace_translated(self, language: str = 'uzn_Latn') -> str:
        """Get translated workplace"""
        return self.get_translated_field('workplace', language)

    def has_translations(self) -> bool:
        """Check if doctor has any translations"""
        try:
            return bool(self.translations.translations)
        except DoctorTranslation.DoesNotExist:
            return False

    def get_translation_languages(self) -> List[str]:
        """Get list of available translation languages"""
        try:
            return self.translations.get_available_languages()
        except DoctorTranslation.DoesNotExist:
            return []


class DoctorFiles(models.Model):
    """Shifokor professional hujjatlari"""

    doctor = models.OneToOneField(
        Doctor,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name="Shifokor"
    )

    FILE_TYPES = [
        ('diploma', 'Diploma'),
        ('license', 'Litsenziya'),
        ('certificate', 'Sertifikat'),
    ]

    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        verbose_name="Hujjat turi"
    )
    file = models.FileField(
        upload_to='doctors/documents/',
        verbose_name="Hujjat fayli",
        help_text="PDF, JPG, PNG formatlarida bo'lishi mumkin"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuklangan sana")

    class Meta:
        verbose_name = "Shifokor hujjati"
        verbose_name_plural = "Shifokor hujjatlari"
        unique_together = ['doctor', 'file_type']

    def __str__(self):
        return f"{self.doctor.full_name} - {self.get_file_type_display()}"



class DoctorSchedule(models.Model):
    """Shifokor ish jadvali"""

    WEEKDAYS = [
        ('monday', 'Dushanba'),
        ('tuesday', 'Seshanba'),
        ('wednesday', 'Chorshanba'),
        ('thursday', 'Payshanba'),
        ('friday', 'Juma'),
        ('saturday', 'Shanba'),
        ('sunday', 'Yakshanba'),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Shifokor"
    )

    weekday = models.CharField(
        max_length=10,
        choices=WEEKDAYS,
        verbose_name="Kun"
    )

    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    end_time = models.TimeField(verbose_name="Tugash vaqti")

    break_start = models.TimeField(blank=True, null=True, verbose_name="Tanaffus boshlanishi")
    break_end = models.TimeField(blank=True, null=True, verbose_name="Tanaffus tugashi")

    is_available = models.BooleanField(default=True, verbose_name="Mavjud")
    max_patients = models.PositiveIntegerField(default=20, verbose_name="Maksimal bemorlar")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Shifokor jadvali"
        verbose_name_plural = "Shifokor jadvallari"
        unique_together = ['doctor', 'weekday']

    def __str__(self):
        return f"{self.doctor.full_name} - {self.get_weekday_display()}"


class DoctorSpecialization(models.Model):
    """Shifokor qo'shimcha mutaxassisliklari"""

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='specializations',
        verbose_name="Shifokor"
    )

    specialty_name = models.CharField(max_length=100, verbose_name="Mutaxassislik nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    certificate_image = models.ImageField(
        upload_to='doctors/specializations/',
        blank=True,
        null=True,
        verbose_name="Sertifikat rasmi"
    )

    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlangan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Qo'shimcha mutaxassislik"
        verbose_name_plural = "Qo'shimcha mutaxassisliklar"

    def __str__(self):
        return f"{self.doctor.full_name} - {self.specialty_name}"


class DoctorViewStatistics(models.Model):
    """Doctor profil ko'rish statistikalari"""

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='view_statistics',
        verbose_name="Shifokor"
    )

    date = models.DateField(verbose_name="Sana")
    daily_views = models.PositiveIntegerField(default=0, verbose_name="Kunlik ko'rishlar")
    unique_visitors = models.PositiveIntegerField(default=0, verbose_name="Yagona ziyoratchilar")

    # Visitor details (optional)
    visitor_regions = models.JSONField(default=dict, verbose_name="Ziyoratchilar viloyatlari")
    referral_sources = models.JSONField(default=dict, verbose_name="Havola manbalari")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Ko'rish statistikasi"
        verbose_name_plural = "Ko'rish statistikalari"
        unique_together = ['doctor', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.doctor.full_name} - {self.date} ({self.daily_views} ko'rish)"


class DoctorTranslation(models.Model):
    """Store translations for doctor profiles"""

    doctor = models.OneToOneField(
        Doctor,
        on_delete=models.CASCADE,
        related_name='translations',
        verbose_name="Shifokor"
    )

    # Store all translations as JSON
    translations = models.JSONField(
        default=dict,
        verbose_name="Tarjimalar",
        help_text="All field translations in different languages"
    )

    # Translation metadata
    source_language = models.CharField(
        max_length=10,
        default='uzn_Latn',
        verbose_name="Manba til"
    )

    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Oxirgi yangilanish"
    )

    is_auto_translated = models.BooleanField(
        default=True,
        verbose_name="Avtomatik tarjima"
    )

    # Quality control
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Tasdiqlangan"
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_doctor_translations',
        verbose_name="Tasdiqlovchi"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Shifokor tarjimasi"
        verbose_name_plural = "Shifokor tarjimalari"
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} tarjimalari"

    def get_translation(self, field_name: str, language: str, fallback: str = '') -> str:
        """Get specific field translation"""
        try:
            return self.translations.get(field_name, {}).get(language, fallback)
        except (AttributeError, TypeError):
            return fallback

    def set_translation(self, field_name: str, language: str, value: str):
        """Set specific field translation"""
        if field_name not in self.translations:
            self.translations[field_name] = {}
        self.translations[field_name][language] = value

    def get_available_languages(self) -> List[str]:
        """Get list of available languages for this doctor"""
        languages = set()
        for field_translations in self.translations.values():
            if isinstance(field_translations, dict):
                languages.update(field_translations.keys())
        return list(languages)

    def is_field_translated(self, field_name: str, language: str) -> bool:
        """Check if specific field is translated to language"""
        return bool(self.get_translation(field_name, language))


class ConsultationTranslation(models.Model):
    """Store translations for consultation data"""

    consultation = models.OneToOneField(
        'consultations.Consultation',
        on_delete=models.CASCADE,
        related_name='translations',
        verbose_name="Konsultatsiya"
    )

    translations = models.JSONField(
        default=dict,
        verbose_name="Tarjimalar"
    )

    source_language = models.CharField(
        max_length=10,
        default='uzn_Latn',
        verbose_name="Manba til"
    )

    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Konsultatsiya tarjimasi"
        verbose_name_plural = "Konsultatsiya tarjimalari"

    def __str__(self):
        return f"Konsultatsiya {self.consultation.id} tarjimalari"


class ChatMessageTranslation(models.Model):
    """Store translations for chat messages"""

    message = models.OneToOneField(
        'chat.ChatMessage',
        on_delete=models.CASCADE,
        related_name='translations',
        verbose_name="Xabar"
    )

    translations = models.JSONField(
        default=dict,
        verbose_name="Tarjimalar"
    )

    source_language = models.CharField(
        max_length=10,
        default='uzn_Latn',
        verbose_name="Manba til"
    )

    auto_detected_language = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Aniqlangan til"
    )

    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xabar tarjimasi"
        verbose_name_plural = "Xabar tarjimalari"

    def __str__(self):
        return f"Xabar {self.message.id} tarjimalari"

class DoctorServiceName(models.Model):
    """Shifokor xizmatlari nomlari"""

    name = models.CharField(max_length=255, unique=True, verbose_name="Xizmat nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Shifokor xizmat nomi"
        verbose_name_plural = "Shifokor xizmat nomlari"

    def __str__(self):
        return self.name

class DoctorService(models.Model):
    """Shifokor xizmatlari"""

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name="Shifokor"
    )

    name = models.ForeignKey(
        DoctorServiceName,
        on_delete=models.CASCADE,
        related_name='doctor_services',
        verbose_name="Xizmat nomi"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Narxi"
    )
    duration = models.PositiveIntegerField(
        default=30,
        verbose_name="Davomiyligi (daqiqa)",
        help_text="Xizmatning davomiyligi daqiqalarda"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Shifokor xizmati"
        verbose_name_plural = "Shifokor xizmatlari"
        unique_together = ['doctor', 'name']

    def __str__(self):
        return f"{self.doctor.full_name} - {self.name}"

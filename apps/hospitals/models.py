from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
import uuid


class Hospital(models.Model):
    """Shifoxonalar modeli"""

    HOSPITAL_TYPES = [
        ('government', 'Davlat'),
        ('private', 'Xususiy'),
        ('clinic', 'Klinika'),
        ('polyclinic', 'Poliklinika'),
        ('hospital', 'Kasalxona'),
        ('medical_center', 'Tibbiy markaz'),
        ('labaratory', 'Laboratoriya'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Shifoxona nomi")
    short_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Qisqa nomi")
    hospital_type = models.CharField(
        max_length=20,
        choices=HOSPITAL_TYPES,
        default='clinic',
        verbose_name="Shifoxona turi"
    )

    # Contact information
    phone = models.CharField(
        max_length=13,
        validators=[RegexValidator(regex=r'^\+998\d{9}$', message='Telefon raqam noto\'g\'ri formatda')],
        verbose_name="Telefon raqam"
    )
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    website = models.URLField(blank=True, null=True, verbose_name="Veb-sayt")
    founded_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Tashkil etilgan yili",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    specialization = models.TextField(
        blank=True,
        null=True,
        verbose_name="Ixtisoslashuvi",
        help_text="Shifoxonaning asosiy ixtisoslashuvi yoki xizmatlari haqida ma'lumot"
    )

    # Address
    region = models.CharField(max_length=100, verbose_name="Viloyat")
    district = models.CharField(max_length=100, verbose_name="Tuman")
    address = models.TextField(verbose_name="Manzil")

    # Additional info
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    working_hours = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ish vaqti")

    # System fields
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlangan")
    logo = models.ImageField(upload_to='hospitals/logos/', blank=True, null=True, verbose_name="Logo")

    # Statistics
    total_doctors = models.PositiveIntegerField(default=0, verbose_name="Jami shifokorlar")
    total_patients = models.PositiveIntegerField(default=0, verbose_name="Jami bemorlar")
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Reyting"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Shifoxona"
        verbose_name_plural = "Shifoxonalar"
        ordering = ['name']
        indexes = [
            models.Index(fields=['region', 'district']),
            models.Index(fields=['hospital_type']),
            models.Index(fields=['is_active', 'is_verified']),
        ]

    def __str__(self):
        return self.name

    def update_statistics(self):
        """Statistikalarni yangilash"""
        # Shifokorlar sonini hisoblash
        self.total_doctors = self.doctors.filter(is_available=True, user__is_verified=True).count()

        # Bemorlar sonini hisoblash (unique patients from consultations)
        from apps.consultations.models import Consultation
        patient_ids = Consultation.objects.filter(
            doctor__hospital=self
        ).values_list('patient_id', flat=True).distinct()
        self.total_patients = len(patient_ids)

        self.save(update_fields=['total_doctors', 'total_patients'])


class HospitalDepartment(models.Model):
    """Shifoxona bo'limlari"""

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='departments',
        verbose_name="Shifoxona"
    )

    name = models.CharField(max_length=100, verbose_name="Bo'lim nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    head_doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='headed_departments',
        verbose_name="Bosh shifokor"
    )

    floor = models.PositiveIntegerField(blank=True, null=True, verbose_name="Qavat")
    room_numbers = models.CharField(max_length=100, blank=True, null=True, verbose_name="Xona raqamlari")

    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Shifoxona bo'limi"
        verbose_name_plural = "Shifoxona bo'limlari"
        unique_together = ['hospital', 'name']

    def __str__(self):
        return f"{self.hospital.name} - {self.name}"


class HospitalStatistics(models.Model):
    """Shifoxona statistikalari"""

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='statistics',
        verbose_name="Shifoxona"
    )

    # Date range
    date = models.DateField(verbose_name="Sana")

    # Doctor statistics
    active_doctors = models.PositiveIntegerField(default=0, verbose_name="Faol shifokorlar")
    new_doctors = models.PositiveIntegerField(default=0, verbose_name="Yangi shifokorlar")

    # Patient statistics
    total_consultations = models.PositiveIntegerField(default=0, verbose_name="Jami konsultatsiyalar")
    new_patients = models.PositiveIntegerField(default=0, verbose_name="Yangi bemorlar")
    returning_patients = models.PositiveIntegerField(default=0, verbose_name="Qaytgan bemorlar")

    # Consultation types
    online_consultations = models.PositiveIntegerField(default=0, verbose_name="Online konsultatsiyalar")
    offline_consultations = models.PositiveIntegerField(default=0, verbose_name="Offline konsultatsiyalar")

    # Revenue (if needed)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Jami daromad"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Shifoxona statistikasi"
        verbose_name_plural = "Shifoxona statistikalari"
        unique_together = ['hospital', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.hospital.name} - {self.date}"

class HospitalService(models.Model):
    """Shifoxona xizmatlari"""

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name="Shifoxona"
    )

    name = models.CharField(max_length=255, verbose_name="Xizmat nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Narxi"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    duration = models.PositiveIntegerField(
        default=30,
        verbose_name="Davomiyligi (daqiqa)",
        help_text="Xizmatning davomiyligi daqiqalarda"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Shifoxona xizmati"
        verbose_name_plural = "Shifoxona xizmatlari"
        unique_together = ['hospital', 'name']

    def __str__(self):
        return f"{self.hospital.name} - {self.name}"

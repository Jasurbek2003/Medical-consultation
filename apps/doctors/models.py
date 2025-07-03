from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.urls import reverse
from PIL import Image

class Doctor(models.Model):
    """Shifokorlar modeli"""

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

    LANGUAGES = [
        ('uz', 'O\'zbek'),
        ('ru', 'Rus'),
        ('en', 'Ingliz'),
    ]

    # Asosiy ma'lumotlar
    first_name = models.CharField(
        max_length=50,
        verbose_name="Ism"
    )
    last_name = models.CharField(
        max_length=50,
        verbose_name="Familiya"
    )
    middle_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Otasining ismi"
    )

    # Professional ma'lumotlar
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
        max_length=20,
        unique=True,
        verbose_name="Litsenziya raqami"
    )

    # Kontakt ma'lumotlar
    phone_regex = RegexValidator(
        regex=r'^\+998[0-9]{9}$',
        message="Telefon raqami +998xxxxxxxxx formatida bo'lishi kerak"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=13,
        verbose_name="Telefon raqami"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email"
    )

    # Manzil
    region = models.CharField(
        max_length=50,
        verbose_name="Viloyat/Shahar"
    )
    district = models.CharField(
        max_length=50,
        verbose_name="Tuman"
    )
    address = models.TextField(
        verbose_name="To'liq manzil"
    )

    # Ish joyxi
    workplace = models.CharField(
        max_length=200,
        verbose_name="Ish joyi"
    )
    workplace_address = models.TextField(
        verbose_name="Ish joyi manzili"
    )

    # Qo'shimcha ma'lumotlar
    languages = models.CharField(
        max_length=10,
        choices=LANGUAGES,
        default='uz',
        verbose_name="Tillar"
    )
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name="Qisqacha ma'lumot"
    )
    education = models.TextField(
        blank=True,
        null=True,
        verbose_name="Ta'lim"
    )
    achievements = models.TextField(
        blank=True,
        null=True,
        verbose_name="Yutuqlar"
    )

    # Rasm
    photo = models.ImageField(
        upload_to='doctors/photos/',
        blank=True,
        null=True,
        verbose_name="Rasmi"
    )

    # Narx va mavjudlik
    consultation_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Konsultatsiya narxi (so'm)"
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="Mavjud"
    )
    is_online_consultation = models.BooleanField(
        default=False,
        verbose_name="Online konsultatsiya"
    )

    # Reyting
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Reyting"
    )
    total_reviews = models.PositiveIntegerField(
        default=0,
        verbose_name="Umumiy sharhlar soni"
    )

    # Ish vaqti
    work_start_time = models.TimeField(
        verbose_name="Ish boshlash vaqti"
    )
    work_end_time = models.TimeField(
        verbose_name="Ish tugash vaqti"
    )
    work_days = models.CharField(
        max_length=20,
        default='1,2,3,4,5,6',  # Dushanba-Shanba
        verbose_name="Ish kunlari (1-7)"
    )

    # Meta ma'lumotlar
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="O'zgartirilgan vaqt"
    )

    class Meta:
        verbose_name = "Shifokor"
        verbose_name_plural = "Shifokorlar"
        ordering = ['-rating', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['specialty']),
            models.Index(fields=['is_available']),
            models.Index(fields=['rating']),
            models.Index(fields=['region', 'district']),
        ]

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} - {self.get_specialty_display()}"

    def get_full_name(self):
        """To'liq ism"""
        if self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        return f"{self.last_name} {self.first_name}"

    def get_short_name(self):
        """Qisqa ism"""
        return f"Dr. {self.first_name} {self.last_name}"

    def get_absolute_url(self):
        """Detail sahifasiga link"""
        return reverse('doctors:detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Rasmni kichraytirish"""
        super().save(*args, **kwargs)

        if self.photo:
            img = Image.open(self.photo.path)
            if img.height > 400 or img.width > 400:
                output_size = (400, 400)
                img.thumbnail(output_size)
                img.save(self.photo.path)

    def update_rating(self):
        """Reytingni yangilash"""
        from apps.consultations.models import Review
        reviews = Review.objects.filter(doctor=self, is_active=True)
        if reviews.exists():
            total_rating = sum([review.rating for review in reviews])
            self.rating = total_rating / reviews.count()
            self.total_reviews = reviews.count()
            self.save(update_fields=['rating', 'total_reviews'])


class DoctorSchedule(models.Model):
    """Shifokor ish jadvali"""

    WEEKDAYS = [
        (1, 'Dushanba'),
        (2, 'Seshanba'),
        (3, 'Chorshanba'),
        (4, 'Payshanba'),
        (5, 'Juma'),
        (6, 'Shanba'),
        (7, 'Yakshanba'),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Shifokor"
    )
    weekday = models.IntegerField(
        choices=WEEKDAYS,
        verbose_name="Kun"
    )
    start_time = models.TimeField(
        verbose_name="Boshlash vaqti"
    )
    end_time = models.TimeField(
        verbose_name="Tugash vaqti"
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="Mavjud"
    )

    class Meta:
        verbose_name = "Ish jadvali"
        verbose_name_plural = "Ish jadvallari"
        unique_together = ['doctor', 'weekday']
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return f"{self.doctor.get_short_name()} - {self.get_weekday_display()}"


class DoctorSpecialization(models.Model):
    """Shifokor qo'shimcha mutaxassisliklari"""

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='specializations',
        verbose_name="Shifokor"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Mutaxassislik nomi"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )
    certificate = models.FileField(
        upload_to='doctors/certificates/',
        blank=True,
        null=True,
        verbose_name="Sertifikat"
    )

    class Meta:
        verbose_name = "Qo'shimcha mutaxassislik"
        verbose_name_plural = "Qo'shimcha mutaxassisliklar"

    def __str__(self):
        return f"{self.doctor.get_short_name()} - {self.name}"
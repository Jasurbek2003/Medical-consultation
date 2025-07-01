from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()


class Consultation(models.Model):
    """Konsultatsiya modeli"""

    STATUS_CHOICES = [
        ('scheduled', 'Rejalashtirilgan'),
        ('in_progress', 'Jarayonda'),
        ('completed', 'Tugallangan'),
        ('cancelled', 'Bekor qilingan'),
        ('no_show', 'Kelmagan'),
        ('rescheduled', 'Qayta rejalashtirilgan'),
    ]

    CONSULTATION_TYPES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('phone', 'Telefon'),
        ('video', 'Video'),
        ('home_visit', 'Uyga tashrif'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Past'),
        ('normal', 'Oddiy'),
        ('high', 'Yuqori'),
        ('urgent', 'Shoshilinch'),
    ]

    # Asosiy ma'lumotlar
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name="Bemor"
    )

    doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name="Shifokor"
    )

    # Chat session bog'lanishi
    chat_session = models.OneToOneField(
        'chat.ChatSession',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='consultation',
        verbose_name="Chat sessiyasi"
    )

    # Konsultatsiya ma'lumotlari
    consultation_type = models.CharField(
        max_length=20,
        choices=CONSULTATION_TYPES,
        default='online',
        verbose_name="Konsultatsiya turi"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name="Holat"
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='normal',
        verbose_name="Muhimlik darajasi"
    )

    # Vaqt ma'lumotlari
    scheduled_date = models.DateField(
        verbose_name="Rejalashtirilgan sana"
    )

    scheduled_time = models.TimeField(
        verbose_name="Rejalashtirilgan vaqt"
    )

    duration_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name="Davomiyligi (daqiqa)"
    )

    actual_start_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Haqiqiy boshlanish vaqti"
    )

    actual_end_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Haqiqiy tugash vaqti"
    )

    # Bemor shikoyatlari
    chief_complaint = models.TextField(
        verbose_name="Asosiy shikoyat"
    )

    symptoms = models.TextField(
        blank=True,
        null=True,
        verbose_name="Simptomlar"
    )

    symptom_duration = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Simptomlar davomiyligi"
    )

    current_medications = models.TextField(
        blank=True,
        null=True,
        verbose_name="Hozirgi dorilar"
    )

    allergies = models.TextField(
        blank=True,
        null=True,
        verbose_name="Allergiyalar"
    )

    # Narx va to'lov
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Konsultatsiya narxi"
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Chegirma miqdori"
    )

    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Yakuniy summa"
    )

    is_paid = models.BooleanField(
        default=False,
        verbose_name="To'langan"
    )

    payment_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="To'lov usuli"
    )

    # Qo'shimcha ma'lumotlar
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )

    referral_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Yuborish sababi"
    )

    # Meta ma'lumotlar
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqt"
    )

    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Bekor qilingan vaqt"
    )

    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Bekor qilish sababi"
    )

    class Meta:
        verbose_name = "Konsultatsiya"
        verbose_name_plural = "Konsultatsiyalar"
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['scheduled_date', 'scheduled_time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.get_short_name()} ({self.scheduled_date})"

    def save(self, *args, **kwargs):
        # Yakuniy summani hisoblash
        if self.consultation_fee and self.discount_amount:
            self.final_amount = self.consultation_fee - self.discount_amount
        elif self.consultation_fee:
            self.final_amount = self.consultation_fee

        super().save(*args, **kwargs)

    def get_scheduled_datetime(self):
        """Rejalashtirilgan to'liq vaqt"""
        return timezone.datetime.combine(self.scheduled_date, self.scheduled_time)

    def get_actual_duration(self):
        """Haqiqiy davomiylik"""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return int(delta.total_seconds() / 60)  # daqiqalarda
        return None

    def can_cancel(self):
        """Bekor qilish mumkinmi"""
        if self.status in ['completed', 'cancelled']:
            return False

        # Konsultatsiyadan 2 soat oldin bekor qilish mumkin
        scheduled_datetime = self.get_scheduled_datetime()
        if timezone.now() + timedelta(hours=2) > scheduled_datetime:
            return False

        return True

    def can_reschedule(self):
        """Qayta rejalash mumkinmi"""
        return self.can_cancel()


class ConsultationDiagnosis(models.Model):
    """Konsultatsiya tashxisi"""

    DIAGNOSIS_TYPES = [
        ('primary', 'Asosiy tashxis'),
        ('secondary', 'Qo\'shimcha tashxis'),
        ('differential', 'Differentsial tashxis'),
        ('provisional', 'Dastlabki tashxis'),
    ]

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='diagnoses',
        verbose_name="Konsultatsiya"
    )

    diagnosis_type = models.CharField(
        max_length=20,
        choices=DIAGNOSIS_TYPES,
        default='primary',
        verbose_name="Tashxis turi"
    )

    diagnosis_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="ICD-10 kod"
    )

    diagnosis_name = models.CharField(
        max_length=200,
        verbose_name="Tashxis nomi"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )

    confidence_level = models.CharField(
        max_length=20,
        choices=[
            ('confirmed', 'Tasdiqlangan'),
            ('probable', 'Ehtimoliy'),
            ('possible', 'Mumkin'),
            ('ruled_out', 'Istisno qilingan'),
        ],
        default='probable',
        verbose_name="Ishonch darajasi"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Tashxis"
        verbose_name_plural = "Tashxislar"
        ordering = ['diagnosis_type', 'created_at']

    def __str__(self):
        return f"{self.diagnosis_name} ({self.get_diagnosis_type_display()})"


class ConsultationPrescription(models.Model):
    """Retsept"""

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name="Konsultatsiya"
    )

    medication_name = models.CharField(
        max_length=200,
        verbose_name="Dori nomi"
    )

    dosage = models.CharField(
        max_length=100,
        verbose_name="Dozasi"
    )

    frequency = models.CharField(
        max_length=100,
        verbose_name="Qabul qilish chastotasi"
    )

    duration = models.CharField(
        max_length=100,
        verbose_name="Qabul qilish muddati"
    )

    instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name="Ko'rsatmalar"
    )

    side_effects = models.TextField(
        blank=True,
        null=True,
        verbose_name="Nojo'ya ta'sirlar"
    )

    contraindications = models.TextField(
        blank=True,
        null=True,
        verbose_name="Qarshlashuvlar"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Retsept"
        verbose_name_plural = "Retseptlar"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.medication_name} - {self.dosage}"


class ConsultationRecommendation(models.Model):
    """Shifokor tavsiylari"""

    RECOMMENDATION_TYPES = [
        ('lifestyle', 'Turmush tarzi'),
        ('diet', 'Parhez'),
        ('exercise', 'Jismoniy mashqlar'),
        ('follow_up', 'Takroriy ko\'rik'),
        ('test', 'Tahlil'),
        ('specialist', 'Mutaxassis ko\'rigi'),
        ('procedure', 'Protsedura'),
    ]

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name="Konsultatsiya"
    )

    recommendation_type = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_TYPES,
        verbose_name="Tavsiya turi"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Sarlavha"
    )

    description = models.TextField(
        verbose_name="Tavsif"
    )

    priority = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Past'),
            ('medium', 'O\'rta'),
            ('high', 'Yuqori'),
            ('urgent', 'Shoshilinch'),
        ],
        default='medium',
        verbose_name="Muhimlik"
    )

    follow_up_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Takroriy ko'rik sanasi"
    )

    is_completed = models.BooleanField(
        default=False,
        verbose_name="Bajarilgan"
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Bajarilgan vaqt"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Tavsiya"
        verbose_name_plural = "Tavsiyalar"
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f"{self.title} - {self.get_recommendation_type_display()}"


class Review(models.Model):
    """Shifokor haqida sharh"""

    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name="Konsultatsiya"
    )

    doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Shifokor"
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Bemor"
    )

    # Baholar
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Umumiy baho"
    )

    professionalism_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Professionallik"
    )

    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Muloqot"
    )

    punctuality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Vaqtni saqlash"
    )

    # Sharh
    title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Sarlavha"
    )

    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Sharh"
    )

    # Tavsiya
    would_recommend = models.BooleanField(
        verbose_name="Tavsiya qilasizmi?"
    )

    # Holat
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name="Tasdiqlangan"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"
        ordering = ['-created_at']
        unique_together = ['consultation', 'patient']

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.get_short_name()} ({self.overall_rating}/5)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Shifokor reytingini yangilash
        self.doctor.update_rating()
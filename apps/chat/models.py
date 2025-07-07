from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class ChatSession(models.Model):
    """Chat sessiyasi"""

    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('completed', 'Tugallangan'),
        ('cancelled', 'Bekor qilingan'),
        ('expired', 'Muddati tugagan'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        blank=True,
        null=True,  # Anonymous userlar uchun
        verbose_name="Foydalanuvchi"
    )

    # Session ma'lumotlari
    session_ip = models.GenericIPAddressField(
        verbose_name="IP manzil"
    )

    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name="User Agent"
    )

    # Chat holati
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Holat"
    )

    # AI tomonidan tahlil qilingan ma'lumotlar
    detected_specialty = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Aniqlangan mutaxassislik"
    )

    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name="Ishonch darajasi"
    )

    # Suhbat statistikasi
    total_messages = models.PositiveIntegerField(
        default=0,
        verbose_name="Jami xabarlar soni"
    )

    user_messages_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Foydalanuvchi xabarlari"
    )

    ai_messages_count = models.PositiveIntegerField(
        default=0,
        verbose_name="AI xabarlari"
    )

    # Vaqt ma'lumotlari
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Boshlangan vaqt"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Oxirgi faollik"
    )

    ended_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Tugagan vaqt"
    )

    duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="Davomiyligi (daqiqa)"
    )

    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Qo'shimcha ma'lumotlar",
        help_text="Session haqida qo'shimcha ma'lumotlar (til, qurilma turi va boshqalar)"
    )

    class Meta:
        verbose_name = "Chat sessiyasi"
        verbose_name_plural = "Chat sessiyalari"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['detected_specialty']),
        ]

    def __str__(self):
        if self.user:
            return f"Chat: {self.user.get_full_name()} - {self.created_at.strftime('%d.%m.%Y %H:%M')}"
        return f"Anonymous Chat - {self.created_at.strftime('%d.%m.%Y %H:%M')}"

    def update_message_counts(self):
        """Xabarlar sonini yangilash"""
        user_count = self.messages.filter(sender_type='user').count()
        ai_count = self.messages.filter(sender_type='ai').count()

        self.user_messages_count = user_count
        self.ai_messages_count = ai_count
        self.total_messages = user_count + ai_count
        self.save(update_fields=['user_messages_count', 'ai_messages_count', 'total_messages'])

    def calculate_duration(self):
        """Suhbat davomiyligini hisoblash"""
        if self.ended_at:
            delta = self.ended_at - self.created_at
            self.duration_minutes = int(delta.total_seconds() / 60)
            self.save(update_fields=['duration_minutes'])


class ChatMessage(models.Model):
    """Chat xabari"""

    SENDER_TYPES = [
        ('user', 'Foydalanuvchi'),
        ('ai', 'AI Assistant'),
        ('system', 'Tizim'),
    ]

    MESSAGE_TYPES = [
        ('text', 'Matn'),
        ('image', 'Rasm'),
        ('file', 'Fayl'),
        ('location', 'Joylashuv'),
        ('doctor_recommendation', 'Shifokor tavsiyasi'),
        ('system_info', 'Tizim ma\'lumoti'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Chat sessiyasi"
    )

    # Xabar ma'lumotlari
    sender_type = models.CharField(
        max_length=10,
        choices=SENDER_TYPES,
        verbose_name="Yuboruvchi turi"
    )

    message_type = models.CharField(
        max_length=23,
        choices=MESSAGE_TYPES,
        default='text',
        verbose_name="Xabar turi"
    )

    content = models.TextField(
        verbose_name="Mazmun"
    )

    # Qo'shimcha ma'lumotlar
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Qo'shimcha ma'lumotlar"
    )

    # Fayl biriktirma
    attachment = models.FileField(
        upload_to='chat/attachments/',
        blank=True,
        null=True,
        verbose_name="Biriktirma"
    )

    # AI javob ma'lumotlari
    ai_model_used = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Ishlatilgan AI model"
    )

    ai_response_time = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="AI javob vaqti (soniya)"
    )

    ai_tokens_used = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Ishlatilgan tokenlar"
    )

    # Xabar holati
    is_read = models.BooleanField(
        default=False,
        verbose_name="O'qilgan"
    )

    is_important = models.BooleanField(
        default=False,
        verbose_name="Muhim"
    )

    is_edited = models.BooleanField(
        default=False,
        verbose_name="Tahrirlangan"
    )

    # Vaqt ma'lumotlari
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yuborilgan vaqt"
    )

    edited_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Tahrirlangan vaqt"
    )

    class Meta:
        verbose_name = "Chat xabari"
        verbose_name_plural = "Chat xabarlari"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['sender_type']),
            models.Index(fields=['message_type']),
        ]

    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.get_sender_type_display()}: {content_preview}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Session statistikasini yangilash
        self.session.update_message_counts()


class AIAnalysis(models.Model):
    """AI tahlili natijasi"""

    ANALYSIS_TYPES = [
        ('symptom_classification', 'Simptom tasnifi'),
        ('specialty_detection', 'Mutaxassislik aniqlash'),
        ('urgency_assessment', 'Shoshilinchlik baholash'),
        ('general_advice', 'Umumiy maslahat'),
    ]

    URGENCY_LEVELS = [
        ('low', 'Past'),
        ('medium', 'O\'rta'),
        ('high', 'Yuqori'),
        ('emergency', 'Favqulodda'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='ai_analyses',
        verbose_name="Chat sessiyasi"
    )

    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='ai_analyses',
        verbose_name="Tahlil qilingan xabar"
    )

    analysis_type = models.CharField(
        max_length=30,
        choices=ANALYSIS_TYPES,
        verbose_name="Tahlil turi"
    )

    # Tahlil natijalari
    detected_keywords = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Aniqlangan kalit so'zlar"
    )

    detected_symptoms = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Aniqlangan simptomlar"
    )

    recommended_specialty = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tavsiya etilgan mutaxassislik"
    )

    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name="Ishonch darajasi"
    )

    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_LEVELS,
        default='medium',
        verbose_name="Shoshilinchlik darajasi"
    )

    # AI model ma'lumotlari
    model_version = models.CharField(
        max_length=50,
        verbose_name="Model versiyasi"
    )

    processing_time = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        verbose_name="Tahlil vaqti (soniya)"
    )

    raw_response = models.TextField(
        verbose_name="Xom javob"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "AI tahlili"
        verbose_name_plural = "AI tahlilar"
        ordering = ['-created_at']

    def __str__(self):
        return f"AI Tahlil: {self.get_analysis_type_display()} - {self.confidence_score}"


class DoctorRecommendation(models.Model):
    """Shifokor tavsiyasi"""

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='doctor_recommendations',
        verbose_name="Chat sessiyasi"
    )

    # Tavsiya ma'lumotlari
    recommended_doctors = models.JSONField(
        verbose_name="Tavsiya etilgan shifokorlar"
    )

    specialty = models.CharField(
        max_length=50,
        verbose_name="Mutaxassislik"
    )

    reason = models.TextField(
        verbose_name="Tavsiya sababi"
    )

    # Filter parametrlari
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Maksimal narx"
    )

    preferred_location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Afzal ko'rilgan joylashuv"
    )

    online_consultation = models.BooleanField(
        default=False,
        verbose_name="Online konsultatsiya"
    )

    # Foydalanuvchi amalları
    doctors_clicked = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Bosilgan shifokorlar"
    )

    selected_doctor_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Tanlangan shifokor ID"
    )

    is_helpful = models.BooleanField(
        blank=True,
        null=True,
        verbose_name="Foydali bo'ldi"
    )

    feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name="Fikr-mulohaza"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Shifokor tavsiyasi"
        verbose_name_plural = "Shifokor tavsiylari"
        ordering = ['-created_at']

    def __str__(self):
        return f"Tavsiya: {self.specialty} - {self.created_at.strftime('%d.%m.%Y')}"


class ChatFeedback(models.Model):
    """Chat fikr-mulohaza"""

    RATING_CHOICES = [
        (1, '1 - Juda yomon'),
        (2, '2 - Yomon'),
        (3, '3 - O\'rtacha'),
        (4, '4 - Yaxshi'),
        (5, '5 - A\'lo'),
    ]

    session = models.OneToOneField(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name="Chat sessiyasi"
    )

    # Baho
    overall_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Umumiy baho"
    )

    ai_accuracy_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        verbose_name="AI aniqlik bahosi"
    )

    response_time_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Javob tezligi bahosi"
    )

    # Fikr-mulohaza
    positive_feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name="Ijobiy fikr"
    )

    negative_feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name="Salbiy fikr"
    )

    suggestions = models.TextField(
        blank=True,
        null=True,
        verbose_name="Takliflar"
    )

    # Qo'shimcha savollar
    would_recommend = models.BooleanField(
        verbose_name="Boshqalarga tavsiya qilasizmi?"
    )

    found_doctor = models.BooleanField(
        blank=True,
        null=True,
        verbose_name="Shifokor topdingizmi?"
    )

    contacted_doctor = models.BooleanField(
        blank=True,
        null=True,
        verbose_name="Shifokor bilan bog'landingizmi?"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Chat fikr-mulohaza"
        verbose_name_plural = "Chat fikr-mulohazalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback: {self.overall_rating}/5 - {self.created_at.strftime('%d.%m.%Y')}"
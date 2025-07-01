from django.contrib import admin
from .models import (
    Consultation, ConsultationDiagnosis, ConsultationPrescription,
    ConsultationRecommendation, Review
)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'doctor', 'scheduled_date', 'scheduled_time',
        'status', 'consultation_type', 'final_amount', 'is_paid'
    ]
    list_filter = [
        'status', 'consultation_type', 'priority', 'is_paid',
        'scheduled_date', 'created_at'
    ]
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'doctor__first_name', 'doctor__last_name',
        'chief_complaint'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'final_amount'
    ]
    date_hierarchy = 'scheduled_date'

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('id', 'patient', 'doctor', 'chat_session')
        }),
        ('Konsultatsiya', {
            'fields': (
                'consultation_type', 'status', 'priority',
                'scheduled_date', 'scheduled_time', 'duration_minutes'
            )
        }),
        ('Tibbiy ma\'lumotlar', {
            'fields': (
                'chief_complaint', 'symptoms', 'symptom_duration',
                'current_medications', 'allergies'
            )
        }),
        ('Moliyaviy', {
            'fields': (
                'consultation_fee', 'discount_amount', 'final_amount',
                'is_paid', 'payment_method'
            )
        }),
        ('Qo\'shimcha', {
            'fields': ('notes', 'referral_reason'),
            'classes': ('collapse',)
        }),
        ('Vaqt', {
            'fields': (
                'actual_start_time', 'actual_end_time',
                'created_at', 'updated_at', 'cancelled_at', 'cancellation_reason'
            ),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_as_completed', 'mark_as_paid']

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f"{queryset.count()} ta konsultatsiya tugallandi.")

    mark_as_completed.short_description = "Tugallangan deb belgilash"

    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True)
        self.message_user(request, f"{queryset.count()} ta konsultatsiya to'landi.")

    mark_as_paid.short_description = "To'langan deb belgilash"


@admin.register(ConsultationDiagnosis)
class ConsultationDiagnosisAdmin(admin.ModelAdmin):
    list_display = ['consultation', 'diagnosis_type', 'diagnosis_name', 'confidence_level']
    list_filter = ['diagnosis_type', 'confidence_level']
    search_fields = ['diagnosis_name', 'diagnosis_code', 'consultation__patient__first_name']


@admin.register(ConsultationPrescription)
class ConsultationPrescriptionAdmin(admin.ModelAdmin):
    list_display = ['consultation', 'medication_name', 'dosage', 'frequency', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['medication_name', 'consultation__patient__first_name']


@admin.register(ConsultationRecommendation)
class ConsultationRecommendationAdmin(admin.ModelAdmin):
    list_display = ['consultation', 'recommendation_type', 'title', 'priority', 'is_completed']
    list_filter = ['recommendation_type', 'priority', 'is_completed']
    search_fields = ['title', 'consultation__patient__first_name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'doctor', 'overall_rating', 'would_recommend',
        'is_verified', 'created_at'
    ]
    list_filter = [
        'overall_rating', 'would_recommend', 'is_active',
        'is_verified', 'created_at'
    ]
    search_fields = [
        'patient__first_name', 'doctor__first_name',
        'title', 'comment'
    ]
    readonly_fields = ['created_at']

    actions = ['verify_reviews', 'unverify_reviews']

    def verify_reviews(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} ta sharh tasdiqlandi.")

    verify_reviews.short_description = "Sharhlarni tasdiqlash"

    def unverify_reviews(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f"{queryset.count()} ta sharh tasdiqlanmadi.")

    unverify_reviews.short_description = "Sharhlar tasdiqini bekor qilish"
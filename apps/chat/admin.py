from django.contrib import admin
from .models import (
    ChatSession, ChatMessage, AIAnalysis,
    DoctorRecommendation, ChatFeedback
)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'get_user_display', 'status', 'detected_specialty',
        'total_messages', 'duration_minutes', 'created_at'
    ]
    list_filter = [
        'status', 'detected_specialty', 'created_at'
    ]
    search_fields = ['user__first_name', 'user__last_name', 'session_ip']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'total_messages',
        'user_messages_count', 'ai_messages_count', 'duration_minutes'
    ]

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('id', 'user', 'status', 'session_ip', 'user_agent')
        }),
        ('AI Tahlil', {
            'fields': ('detected_specialty', 'confidence_score'),
            'classes': ('collapse',)
        }),
        ('Statistika', {
            'fields': (
                'total_messages', 'user_messages_count',
                'ai_messages_count', 'duration_minutes'
            ),
            'classes': ('collapse',)
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at', 'ended_at'),
            'classes': ('collapse',)
        })
    )

    def get_user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.phone
        return f"Anonymous ({obj.session_ip})"

    get_user_display.short_description = 'Foydalanuvchi'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'sender_type', 'message_type',
        'content_preview', 'created_at'
    ]
    list_filter = ['sender_type', 'message_type', 'is_read', 'is_important']
    search_fields = ['content', 'session__user__first_name']
    readonly_fields = ['created_at', 'edited_at']

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = 'Xabar'


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'analysis_type', 'recommended_specialty',
        'confidence_score', 'urgency_level', 'created_at'
    ]
    list_filter = ['analysis_type', 'urgency_level', 'recommended_specialty']
    readonly_fields = ['created_at', 'processing_time', 'model_version']


@admin.register(DoctorRecommendation)
class DoctorRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'specialty', 'selected_doctor_id',
        'is_helpful', 'created_at'
    ]
    list_filter = ['specialty', 'is_helpful', 'online_consultation']
    readonly_fields = ['created_at']


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'overall_rating', 'ai_accuracy_rating',
        'would_recommend', 'found_doctor', 'created_at'
    ]
    list_filter = [
        'overall_rating', 'would_recommend', 'found_doctor', 'contacted_doctor'
    ]
    readonly_fields = ['created_at']

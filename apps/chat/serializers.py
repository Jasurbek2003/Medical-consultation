from rest_framework import serializers
from .models import ChatSession, ChatMessage, AIAnalysis, DoctorRecommendation, ChatFeedback

class ChatMessageSerializer(serializers.ModelSerializer):
    """Chat xabar serializer"""

    sender_display = serializers.CharField(source='get_sender_type_display', read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender_type', 'sender_display', 'message_type',
            'content', 'metadata', 'attachment', 'is_read', 'is_important',
            'created_at', 'ai_model_used', 'ai_response_time'
        ]


class ChatSessionSerializer(serializers.ModelSerializer):
    """Chat session serializer"""

    recent_messages = serializers.SerializerMethodField()
    user_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'user_display', 'status', 'status_display',
            'detected_specialty', 'confidence_score', 'total_messages',
            'user_messages_count', 'ai_messages_count', 'duration_minutes',
            'created_at', 'updated_at', 'recent_messages'
        ]

    def get_recent_messages(self, obj):
        messages = obj.messages.order_by('-created_at')[:5]
        return ChatMessageSerializer(messages, many=True).data

    def get_user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.phone
        return f"Anonymous ({obj.session_ip})"


class AIAnalysisSerializer(serializers.ModelSerializer):
    """AI tahlil serializer"""

    class Meta:
        model = AIAnalysis
        fields = [
            'id', 'analysis_type', 'detected_keywords', 'detected_symptoms',
            'recommended_specialty', 'confidence_score', 'urgency_level',
            'model_version', 'processing_time', 'created_at'
        ]


class DoctorRecommendationSerializer(serializers.ModelSerializer):
    """Shifokor tavsiyasi serializer"""

    class Meta:
        model = DoctorRecommendation
        fields = [
            'id', 'recommended_doctors', 'specialty', 'reason',
            'max_price', 'preferred_location', 'online_consultation',
            'doctors_clicked', 'selected_doctor_id', 'is_helpful',
            'feedback', 'created_at'
        ]


class ChatFeedbackSerializer(serializers.ModelSerializer):
    """Chat fikr-mulohaza serializer"""

    overall_rating_display = serializers.CharField(source='get_overall_rating_display', read_only=True)

    class Meta:
        model = ChatFeedback
        fields = [
            'id', 'overall_rating', 'overall_rating_display',
            'ai_accuracy_rating', 'response_time_rating',
            'positive_feedback', 'negative_feedback', 'suggestions',
            'would_recommend', 'found_doctor', 'contacted_doctor',
            'created_at'
        ]
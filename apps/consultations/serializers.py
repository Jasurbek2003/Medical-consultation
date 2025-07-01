from rest_framework import serializers
from .models import (
    Consultation, ConsultationDiagnosis, ConsultationPrescription,
    ConsultationRecommendation, Review
)


class ConsultationSerializer(serializers.ModelSerializer):
    """Konsultatsiya serializer"""

    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_short_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    consultation_type_display = serializers.CharField(source='get_consultation_type_display', read_only=True)
    scheduled_datetime = serializers.DateTimeField(source='get_scheduled_datetime', read_only=True)
    actual_duration = serializers.IntegerField(source='get_actual_duration', read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'consultation_type', 'consultation_type_display', 'status', 'status_display',
            'priority', 'scheduled_date', 'scheduled_time', 'scheduled_datetime',
            'duration_minutes', 'actual_duration', 'chief_complaint', 'symptoms',
            'consultation_fee', 'discount_amount', 'final_amount', 'is_paid',
            'created_at', 'actual_start_time', 'actual_end_time'
        ]


class ConsultationDetailSerializer(ConsultationSerializer):
    """Konsultatsiya batafsil serializer"""

    diagnoses = serializers.SerializerMethodField()
    prescriptions = serializers.SerializerMethodField()
    recommendations = serializers.SerializerMethodField()

    class Meta(ConsultationSerializer.Meta):
        fields = ConsultationSerializer.Meta.fields + [
            'symptom_duration', 'current_medications', 'allergies',
            'notes', 'referral_reason', 'payment_method',
            'diagnoses', 'prescriptions', 'recommendations'
        ]

    def get_diagnoses(self, obj):
        diagnoses = obj.diagnoses.all()
        return ConsultationDiagnosisSerializer(diagnoses, many=True).data

    def get_prescriptions(self, obj):
        prescriptions = obj.prescriptions.filter(is_active=True)
        return ConsultationPrescriptionSerializer(prescriptions, many=True).data

    def get_recommendations(self, obj):
        recommendations = obj.recommendations.all()
        return ConsultationRecommendationSerializer(recommendations, many=True).data


class ConsultationDiagnosisSerializer(serializers.ModelSerializer):
    """Tashxis serializer"""

    diagnosis_type_display = serializers.CharField(source='get_diagnosis_type_display', read_only=True)
    confidence_level_display = serializers.CharField(source='get_confidence_level_display', read_only=True)

    class Meta:
        model = ConsultationDiagnosis
        fields = [
            'id', 'diagnosis_type', 'diagnosis_type_display',
            'diagnosis_code', 'diagnosis_name', 'description',
            'confidence_level', 'confidence_level_display', 'created_at'
        ]


class ConsultationPrescriptionSerializer(serializers.ModelSerializer):
    """Retsept serializer"""

    class Meta:
        model = ConsultationPrescription
        fields = [
            'id', 'medication_name', 'dosage', 'frequency', 'duration',
            'instructions', 'side_effects', 'contraindications',
            'is_active', 'created_at'
        ]


class ConsultationRecommendationSerializer(serializers.ModelSerializer):
    """Tavsiya serializer"""

    recommendation_type_display = serializers.CharField(source='get_recommendation_type_display', read_only=True)

    class Meta:
        model = ConsultationRecommendation
        fields = [
            'id', 'recommendation_type', 'recommendation_type_display',
            'title', 'description', 'priority', 'follow_up_date',
            'is_completed', 'completed_at', 'created_at'
        ]


class ReviewSerializer(serializers.ModelSerializer):
    """Sharh serializer"""

    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_short_name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'overall_rating', 'professionalism_rating', 'communication_rating',
            'punctuality_rating', 'title', 'comment', 'would_recommend',
            'is_active', 'is_verified', 'created_at'
        ]

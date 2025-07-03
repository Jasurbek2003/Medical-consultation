from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import date, timedelta

from .models import (
    Consultation, ConsultationDiagnosis, ConsultationPrescription,
    ConsultationRecommendation, Review
)
from .serializers import (
    ConsultationSerializer, ConsultationDetailSerializer,
    ConsultationDiagnosisSerializer, ConsultationPrescriptionSerializer,
    ConsultationRecommendationSerializer, ReviewSerializer
)


class ConsultationViewSet(viewsets.ModelViewSet):
    """Consultation API ViewSet"""
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConsultationDetailSerializer
        return ConsultationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        # Filter by doctor
        doctor_id = self.request.query_params.get('doctor_id')
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by consultation type
        consultation_type = self.request.query_params.get('consultation_type')
        if consultation_type:
            queryset = queryset.filter(consultation_type=consultation_type)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)

        return queryset.order_by('-scheduled_date', '-scheduled_time')

    @action(detail=True, methods=['post'])
    def start_consultation(self, request, pk=None):
        """Konsultatsiyani boshlash"""
        consultation = self.get_object()

        if consultation.status != 'scheduled':
            return Response(
                {'error': 'Konsultatsiya faqat rejalashtirilgan holatda boshlanishi mumkin'},
                status=status.HTTP_400_BAD_REQUEST
            )

        consultation.status = 'in_progress'
        consultation.actual_start_time = timezone.now()
        consultation.save()

        return Response({'message': 'Konsultatsiya boshlandi'})

    @action(detail=True, methods=['post'])
    def complete_consultation(self, request, pk=None):
        """Konsultatsiyani yakunlash"""
        consultation = self.get_object()

        if consultation.status != 'in_progress':
            return Response(
                {'error': 'Konsultatsiya faqat jarayonda holatda yakunlanishi mumkin'},
                status=status.HTTP_400_BAD_REQUEST
            )

        consultation.status = 'completed'
        consultation.actual_end_time = timezone.now()
        consultation.save()

        return Response({'message': 'Konsultatsiya yakunlandi'})

    @action(detail=True, methods=['post'])
    def cancel_consultation(self, request, pk=None):
        """Konsultatsiyani bekor qilish"""
        consultation = self.get_object()

        if not consultation.can_cancel():
            return Response(
                {'error': 'Bu konsultatsiyani bekor qilib bo\'lmaydi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        consultation.status = 'cancelled'
        consultation.cancelled_at = timezone.now()
        consultation.cancellation_reason = request.data.get('reason', '')
        consultation.save()

        return Response({'message': 'Konsultatsiya bekor qilindi'})

    @action(detail=True, methods=['post'])
    def add_diagnosis(self, request, pk=None):
        """Tashxis qo'shish"""
        consultation = self.get_object()
        data = request.data.copy()
        data['consultation'] = consultation.id

        serializer = ConsultationDiagnosisSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_prescription(self, request, pk=None):
        """Retsept qo'shish"""
        consultation = self.get_object()
        data = request.data.copy()
        data['consultation'] = consultation.id

        serializer = ConsultationPrescriptionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_recommendation(self, request, pk=None):
        """Tavsiya qo'shish"""
        consultation = self.get_object()
        data = request.data.copy()
        data['consultation'] = consultation.id

        serializer = ConsultationRecommendationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Bugungi konsultatsiyalar"""
        today = date.today()
        consultations = self.get_queryset().filter(scheduled_date=today)

        page = self.paginate_queryset(consultations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(consultations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Kelgusi konsultatsiyalar"""
        today = date.today()
        upcoming = self.get_queryset().filter(
            scheduled_date__gte=today,
            status='scheduled'
        )

        page = self.paginate_queryset(upcoming)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Konsultatsiya statistikasi"""
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        stats = {
            'total_consultations': self.get_queryset().count(),
            'today_consultations': self.get_queryset().filter(scheduled_date=today).count(),
            'week_consultations': self.get_queryset().filter(scheduled_date__gte=week_ago).count(),
            'month_consultations': self.get_queryset().filter(scheduled_date__gte=month_ago).count(),

            'by_status': dict(
                self.get_queryset().values('status').annotate(count=Count('id'))
            ),

            'by_type': dict(
                self.get_queryset().values('consultation_type').annotate(count=Count('id'))
            ),

            'avg_duration': self.get_queryset().filter(
                actual_start_time__isnull=False,
                actual_end_time__isnull=False
            ).aggregate(avg_duration=Avg('duration_minutes'))['avg_duration'] or 0,

            'revenue': {
                'total': float(self.get_queryset().filter(is_paid=True).aggregate(
                    total=models.Sum('final_amount'))['total'] or 0),
                'this_month': float(self.get_queryset().filter(
                    is_paid=True,
                    scheduled_date__gte=month_ago
                ).aggregate(total=models.Sum('final_amount'))['total'] or 0)
            }
        }

        return Response(stats)


class ReviewViewSet(viewsets.ModelViewSet):
    """Review API ViewSet"""
    queryset = Review.objects.filter(is_active=True)
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by doctor
        doctor_id = self.request.query_params.get('doctor_id')
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        # Filter by patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        # Filter by rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(overall_rating__gte=min_rating)

        # Only verified reviews
        if self.request.query_params.get('verified_only') == 'true':
            queryset = queryset.filter(is_verified=True)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Sharh statistikasi"""
        stats = {
            'total_reviews': self.get_queryset().count(),
            'verified_reviews': self.get_queryset().filter(is_verified=True).count(),
            'avg_rating': self.get_queryset().aggregate(avg=Avg('overall_rating'))['avg'] or 0,
            'rating_distribution': {},
            'would_recommend_percentage': (
                    self.get_queryset().filter(would_recommend=True).count() /
                    max(self.get_queryset().count(), 1) * 100
            )
        }

        # Rating distribution
        for i in range(1, 6):
            stats['rating_distribution'][f'rating_{i}'] = self.get_queryset().filter(
                overall_rating=i
            ).count()

        return Response(stats)


class ConsultationDiagnosisViewSet(viewsets.ModelViewSet):
    """Consultation Diagnosis API ViewSet"""
    queryset = ConsultationDiagnosis.objects.all()
    serializer_class = ConsultationDiagnosisSerializer
    permission_classes = [AllowAny]


class ConsultationPrescriptionViewSet(viewsets.ModelViewSet):
    """Consultation Prescription API ViewSet"""
    queryset = ConsultationPrescription.objects.filter(is_active=True)
    serializer_class = ConsultationPrescriptionSerializer
    permission_classes = [AllowAny]


class ConsultationRecommendationViewSet(viewsets.ModelViewSet):
    """Consultation Recommendation API ViewSet"""
    queryset = ConsultationRecommendation.objects.all()
    serializer_class = ConsultationRecommendationSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Tavsiyani bajarilgan deb belgilash"""
        recommendation = self.get_object()
        recommendation.is_completed = True
        recommendation.completed_at = timezone.now()
        recommendation.save()

        return Response({'message': 'Tavsiya bajarilgan deb belgilandi'})

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Bajarilmagan tavsiyalar"""
        pending = self.get_queryset().filter(is_completed=False)

        page = self.paginate_queryset(pending)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
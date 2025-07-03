from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from .models import ChatSession, ChatMessage, AIAnalysis, DoctorRecommendation, ChatFeedback
from .serializers import (
    ChatSessionSerializer, ChatMessageSerializer, AIAnalysisSerializer,
    DoctorRecommendationSerializer, ChatFeedbackSerializer
)

try:
    from apps.ai_assistant.services import GeminiService

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


    class GeminiService:
        def classify_medical_issue(self, message, context=None):
            return {'specialty': 'terapevt', 'confidence': 0.5, 'explanation': 'Fallback'}


class ChatSessionViewSet(viewsets.ModelViewSet):
    """Chat Session API ViewSet"""
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by user if authenticated
        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Session xabarlarini olish"""
        session = self.get_object()
        messages = session.messages.order_by('created_at')

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Session ga xabar yuborish"""
        session = self.get_object()
        message_content = request.data.get('message', '').strip()

        if not message_content:
            return Response(
                {'error': 'Xabar bo\'sh bo\'lishi mumkin emas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # User xabarini saqlash
        user_message = ChatMessage.objects.create(
            session=session,
            sender_type='user',
            message_type='text',
            content=message_content
        )

        # AI javobini olish
        gemini_service = GeminiService()
        classification = gemini_service.classify_medical_issue(message_content)

        # AI javobini yaratish
        ai_response = self._generate_ai_response(classification, session)

        ai_message = ChatMessage.objects.create(
            session=session,
            sender_type='ai',
            message_type='text',
            content=ai_response['content'],
            ai_model_used=ai_response.get('model_used', 'fallback'),
            ai_response_time=ai_response.get('processing_time', 0),
            metadata=ai_response.get('metadata', {})
        )

        # Session ma'lumotlarini yangilash
        session.detected_specialty = classification.get('specialty')
        session.confidence_score = classification.get('confidence', 0.5)
        session.save()

        return Response({
            'user_message': ChatMessageSerializer(user_message).data,
            'ai_message': ChatMessageSerializer(ai_message).data,
            'classification': classification
        })

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """Session ni yakunlash"""
        session = self.get_object()
        session.status = 'completed'
        session.ended_at = timezone.now()
        session.calculate_duration()
        session.save()

        return Response({'message': 'Session yakunlandi'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Chat statistikasi"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        stats = {
            'total_sessions': ChatSession.objects.count(),
            'active_sessions': ChatSession.objects.filter(status='active').count(),
            'sessions_today': ChatSession.objects.filter(created_at__date=today).count(),
            'sessions_this_week': ChatSession.objects.filter(created_at__date__gte=week_ago).count(),
            'total_messages': ChatMessage.objects.count(),
            'ai_messages': ChatMessage.objects.filter(sender_type='ai').count(),
            'user_messages': ChatMessage.objects.filter(sender_type='user').count(),
            'average_session_duration': ChatSession.objects.filter(
                duration_minutes__gt=0
            ).aggregate(avg=Avg('duration_minutes'))['avg'] or 0,
        }

        # Eng ko'p so'ralgan mutaxassisliklar
        specialties = ChatSession.objects.filter(
            detected_specialty__isnull=False
        ).values('detected_specialty').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        stats['top_specialties'] = list(specialties)

        # Feedback statistikasi
        feedback_stats = ChatFeedback.objects.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_accuracy=Avg('ai_accuracy_rating'),
            avg_response_time=Avg('response_time_rating'),
            total_feedback=Count('id')
        )

        stats['feedback'] = feedback_stats
        stats['ai_available'] = AI_AVAILABLE

        return Response(stats)

    def _generate_ai_response(self, classification, session):
        """AI javobini yaratish"""
        from apps.doctors.models import Doctor

        specialty = classification.get('specialty', 'terapevt')
        confidence = classification.get('confidence', 0.5)

        # Shifokorlarni topish
        doctors = Doctor.objects.filter(
            specialty=specialty,
            is_available=True
        ).order_by('-rating', 'consultation_price')[:3]

        doctors_data = []
        for doctor in doctors:
            doctors_data.append({
                'id': doctor.id,
                'name': doctor.get_short_name(),
                'experience': doctor.experience,
                'rating': float(doctor.rating),
                'total_reviews': doctor.total_reviews,
                'consultation_price': float(doctor.consultation_price),
                'workplace': doctor.workplace,
                'phone': doctor.phone,
                'is_online_consultation': doctor.is_online_consultation
            })

        # Shifokor tavsiyasini saqlash
        if doctors_data:
            DoctorRecommendation.objects.create(
                session=session,
                recommended_doctors=doctors_data,
                specialty=specialty,
                reason=classification.get('explanation', '')
            )

        # Javob yaratish
        specialty_display = dict(Doctor.SPECIALTIES).get(specialty, specialty)

        response_content = f"""**Sizning muammoingizni tahlil qildim.**

🔍 **Tavsiya etilgan mutaxassis:** {specialty_display}
📊 **Ishonch darajasi:** {confidence * 100:.0f}%
💡 **Sabab:** {classification.get('explanation', '')}

"""

        if doctors_data:
            response_content += f"**🏥 {specialty_display} mutaxassislari:**\n\n"
            for i, doctor in enumerate(doctors_data, 1):
                response_content += f"""{i}. **{doctor['name']}**
   - Tajriba: {doctor['experience']} yil
   - Reyting: {doctor['rating']}/5 ⭐ ({doctor['total_reviews']} sharh)
   - Narx: {doctor['consultation_price']:,.0f} so'm
   - Ish joyi: {doctor['workplace']}
   - Telefon: {doctor['phone']}

"""
        else:
            response_content += "❌ Hozircha bu mutaxassislik bo'yicha shifokorlar mavjud emas.\n\n"

        response_content += "**❗ Muhim:** Bu faqat umumiy maslahat. Aniq tashxis uchun shifokor bilan maslahatlashing."

        return {
            'content': response_content,
            'model_used': classification.get('model_used', 'fallback'),
            'processing_time': classification.get('processing_time', 0),
            'metadata': {
                'classification': classification,
                'doctors': doctors_data,
                'response_type': 'medical_analysis'
            }
        }


class ChatMessageViewSet(viewsets.ModelViewSet):
    """Chat Message API ViewSet"""
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by session
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        # Filter by sender type
        sender_type = self.request.query_params.get('sender_type')
        if sender_type:
            queryset = queryset.filter(sender_type=sender_type)

        return queryset.order_by('created_at')


class ChatFeedbackViewSet(viewsets.ModelViewSet):
    """Chat Feedback API ViewSet"""
    queryset = ChatFeedback.objects.all()
    serializer_class = ChatFeedbackSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Feedback statistikasi"""
        stats = self.queryset.aggregate(
            total_feedback=Count('id'),
            avg_overall=Avg('overall_rating'),
            avg_accuracy=Avg('ai_accuracy_rating'),
            avg_response_time=Avg('response_time_rating'),
            recommend_percentage=Avg('would_recommend') * 100,
            found_doctor_percentage=Count('found_doctor', filter=Q(found_doctor=True)) * 100.0 / Count('id')
        )

        # Rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[f'rating_{i}'] = self.queryset.filter(overall_rating=i).count()

        stats['rating_distribution'] = rating_distribution

        return Response(stats)


class DoctorRecommendationViewSet(viewsets.ModelViewSet):
    """Doctor Recommendation API ViewSet"""
    queryset = DoctorRecommendation.objects.all()
    serializer_class = DoctorRecommendationSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def mark_helpful(self, request, pk=None):
        """Tavsiya foydali deb belgilash"""
        recommendation = self.get_object()
        recommendation.is_helpful = request.data.get('is_helpful', True)
        recommendation.feedback = request.data.get('feedback', '')
        recommendation.save()

        return Response({'message': 'Fikr-mulohaza saqlandi'})

    @action(detail=True, methods=['post'])
    def doctor_clicked(self, request, pk=None):
        """Shifokor bosilganini belgilash"""
        recommendation = self.get_object()
        doctor_id = request.data.get('doctor_id')

        if doctor_id:
            clicked_doctors = recommendation.doctors_clicked or []
            if doctor_id not in clicked_doctors:
                clicked_doctors.append(doctor_id)
                recommendation.doctors_clicked = clicked_doctors
                recommendation.save()

        return Response({'message': 'Click qayd qilindi'})

    @action(detail=True, methods=['post'])
    def doctor_selected(self, request, pk=None):
        """Shifokor tanlanganini belgilash"""
        recommendation = self.get_object()
        doctor_id = request.data.get('doctor_id')

        if doctor_id:
            recommendation.selected_doctor_id = doctor_id
            recommendation.save()

        return Response({'message': 'Shifokor tanlandi'})

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Tavsiya analitikasi"""
        total_recommendations = self.queryset.count()
        helpful_count = self.queryset.filter(is_helpful=True).count()

        # Eng ko'p tavsiya qilingan mutaxassisliklar
        top_specialties = self.queryset.values('specialty').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        # Eng ko'p bosilgan shifokorlar
        clicked_doctors = {}
        for rec in self.queryset.filter(doctors_clicked__isnull=False):
            for doctor_id in rec.doctors_clicked:
                clicked_doctors[doctor_id] = clicked_doctors.get(doctor_id, 0) + 1

        analytics = {
            'total_recommendations': total_recommendations,
            'helpful_recommendations': helpful_count,
            'helpful_percentage': (helpful_count / total_recommendations * 100) if total_recommendations > 0 else 0,
            'top_specialties': list(top_specialties),
            'most_clicked_doctors': dict(sorted(clicked_doctors.items(), key=lambda x: x[1], reverse=True)[:5])
        }

        return Response(analytics)
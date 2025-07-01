from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Models
from .models import ChatSession, ChatMessage, AIAnalysis, DoctorRecommendation, ChatFeedback
from apps.doctors.models import Doctor

# AI Service - try/except bilan himoyalash
try:
    from apps.ai_assistant.services import GeminiService

    AI_AVAILABLE = True
except ImportError as e:
    print(f"AI Service import error: {e}")
    AI_AVAILABLE = False


    # Fallback GeminiService klassi
    class GeminiService:
        def __init__(self):
            pass

        def classify_medical_issue(self, user_message, user_context=None):
            # Oddiy klassifikatsiya
            message_lower = user_message.lower()
            if 'tish' in message_lower:
                specialty = 'stomatolog'
            elif 'yurak' in message_lower:
                specialty = 'kardiolog'
            elif 'siydik' in message_lower:
                specialty = 'urolog'
            else:
                specialty = 'terapevt'

            return {
                'specialty': specialty,
                'confidence': 0.7,
                'explanation': 'Oddiy kalit so\'z tahlili asosida',
                'processing_time': 0.1,
                'model_used': 'fallback',
                'symptoms_analysis': {'detected_symptoms': [], 'keywords': []},
                'urgency_assessment': {'urgency_level': 'medium', 'description': 'Shifokorga ko\'rsating'}
            }

        def get_medical_advice(self, user_message, specialty, symptoms=None):
            advice_map = {
                'terapevt': 'Umumiy holatni yaxshilash uchun shifokorga murojaat qiling.',
                'stomatolog': 'Tish gigienasini saqlang va shifokorga ko\'rsating.',
                'kardiolog': 'Qon bosimingizni nazorat qiling.',
                'urolog': 'Ko\'p suv iching va shifokorga murojaat qiling.'
            }

            return {
                'advice': advice_map.get(specialty, 'Shifokor bilan maslahatlashing.'),
                'specialty': specialty,
                'processing_time': 0.1,
                'model_used': 'fallback'
            }

import json
import logging

logger = logging.getLogger(__name__)


# Web Views
class ChatRoomView(TemplateView):
    """Chat xonasi sahifasi"""
    template_name = 'chat/chat_room.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Session yaratish yoki olish
        session_id = self.request.GET.get('session')
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
                context['session'] = session
                context['messages'] = session.messages.order_by('created_at')
            except ChatSession.DoesNotExist:
                session = None

        context['specialties'] = Doctor.SPECIALTIES
        context['ai_available'] = AI_AVAILABLE
        return context


class ChatInterfaceView(TemplateView):
    """Chat interface sahifasi"""
    template_name = 'chat/chat_interface.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ai_available'] = AI_AVAILABLE
        return context


# API Views
@method_decorator(csrf_exempt, name='dispatch')
class ChatMessageView(TemplateView):
    """Chat xabar yuborish API"""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            session_id = data.get('session_id')

            if not user_message:
                return JsonResponse({
                    'success': False,
                    'error': 'Xabar bo\'sh bo\'lishi mumkin emas'
                })

            # Session olish yoki yaratish
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id)
                except ChatSession.DoesNotExist:
                    session = self._create_session(request)
            else:
                session = self._create_session(request)

            # Foydalanuvchi xabarini saqlash
            user_chat_message = ChatMessage.objects.create(
                session=session,
                sender_type='user',
                message_type='text',
                content=user_message
            )

            # AI tahlili
            gemini_service = GeminiService()

            # 1. Tibbiy muammoni klassifikatsiya qilish
            classification_result = gemini_service.classify_medical_issue(
                user_message,
                user_context=self._get_user_context(request)
            )

            # Session ma'lumotlarini yangilash
            session.detected_specialty = classification_result.get('specialty')
            session.confidence_score = classification_result.get('confidence', 0.5)
            session.save()

            # 2. Mos shifokorlarni topish
            recommended_doctors = self._get_recommended_doctors(
                classification_result.get('specialty'),
                user_context=self._get_user_context(request)
            )

            # 3. Tibbiy maslahat olish
            advice_result = gemini_service.get_medical_advice(
                user_message,
                classification_result.get('specialty'),
                classification_result.get('symptoms_analysis', {}).get('detected_symptoms', [])
            )

            # AI javob xabarini formatlash va saqlash
            ai_response_content = self._format_ai_response(
                classification_result,
                recommended_doctors,
                advice_result.get('advice', '')
            )

            ai_chat_message = ChatMessage.objects.create(
                session=session,
                sender_type='ai',
                message_type='doctor_recommendation',
                content=ai_response_content,
                ai_model_used=classification_result.get('model_used', 'gemini-pro'),
                ai_response_time=advice_result.get('processing_time', 0),
                metadata={
                    'classification': classification_result,
                    'doctors': recommended_doctors,
                    'advice': advice_result
                }
            )

            # Javobni qaytarish
            return JsonResponse({
                'success': True,
                'session_id': str(session.id),
                'user_message': {
                    'id': user_chat_message.id,
                    'content': user_message,
                    'timestamp': user_chat_message.created_at.isoformat()
                },
                'ai_response': {
                    'id': ai_chat_message.id,
                    'content': ai_response_content,
                    'timestamp': ai_chat_message.created_at.isoformat(),
                    'metadata': ai_chat_message.metadata
                },
                'classification': {
                    'specialty': classification_result.get('specialty'),
                    'specialty_display': dict(Doctor.SPECIALTIES).get(
                        classification_result.get('specialty'), ''
                    ),
                    'confidence': classification_result.get('confidence'),
                    'explanation': classification_result.get('explanation'),
                    'urgency_level': classification_result.get('urgency_assessment', {}).get('urgency_level')
                },
                'recommended_doctors': recommended_doctors,
                'ai_available': AI_AVAILABLE
            })

        except Exception as e:
            logger.error(f"Chat message processing error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Xatolik yuz berdi. Iltimos qayta urinib ko\'ring.',
                'error_details': str(e) if settings.DEBUG else None
            })

    def _create_session(self, request):
        """Yangi chat session yaratish"""
        return ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_ip=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def _get_client_ip(self, request):
        """Client IP manzilini olish"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _get_user_context(self, request):
        """Foydalanuvchi kontekstini olish"""
        context = {}
        if request.user.is_authenticated:
            user = request.user
            context.update({
                'age': user.get_age() if hasattr(user, 'get_age') else None,
                'gender': getattr(user, 'gender', None),
                'blood_type': getattr(user, 'blood_type', None),
            })
        return context

    def _get_recommended_doctors(self, specialty, user_context=None, limit=5):
        """Tavsiya etilgan shifokorlarni olish"""
        try:
            doctors = Doctor.objects.filter(
                specialty=specialty,
                is_available=True
            ).order_by('-rating', 'consultation_price')[:limit]

            doctors_data = []
            for doctor in doctors:
                doctors_data.append({
                    'id': doctor.id,
                    'name': doctor.get_short_name(),
                    'full_name': doctor.get_full_name(),
                    'specialty_display': doctor.get_specialty_display(),
                    'experience': doctor.experience,
                    'rating': float(doctor.rating),
                    'total_reviews': doctor.total_reviews,
                    'consultation_price': float(doctor.consultation_price),
                    'workplace': doctor.workplace,
                    'region': doctor.region,
                    'district': doctor.district,
                    'phone': doctor.phone,
                    'is_online_consultation': doctor.is_online_consultation,
                    'work_hours': f"{doctor.work_start_time.strftime('%H:%M')} - {doctor.work_end_time.strftime('%H:%M')}",
                    'photo_url': doctor.photo.url if doctor.photo else None,
                    'bio': doctor.bio or '',
                    'detail_url': f'/doctors/{doctor.id}/'
                })

            return doctors_data

        except Exception as e:
            logger.error(f"Error getting recommended doctors: {e}")
            return []

    def _format_ai_response(self, classification, doctors, advice):
        """AI javobini formatlash"""
        specialty_display = dict(Doctor.SPECIALTIES).get(
            classification.get('specialty'), classification.get('specialty', '')
        )

        response = f"""**Sizning muammoingizni tahlil qildim.**

🔍 **Tavsiya etilgan mutaxassis:** {specialty_display}
📊 **Ishonch darajasi:** {classification.get('confidence', 0.5) * 100:.0f}%
💡 **Sabab:** {classification.get('explanation', '')}

"""

        if classification.get('urgency_assessment', {}).get('urgency_level') == 'emergency':
            response += """⚠️ **DIQQAT: Bu shoshilinch holat bo'lishi mumkin!**
Zudlik bilan eng yaqin shifoxonaga boring yoki tez yordam chaqiring: 103

"""

        if doctors:
            response += f"""**🏥 {specialty_display} mutaxassislari:**

"""
            for i, doctor in enumerate(doctors[:3], 1):
                response += f"""{i}. **{doctor['name']}**
   - Tajriba: {doctor['experience']} yil
   - Reyting: {doctor['rating']}/5 ⭐ ({doctor['total_reviews']} sharh)
   - Narx: {doctor['consultation_price']:,.0f} so'm
   - Ish joyi: {doctor['workplace']}
   - Telefon: {doctor['phone']}

"""

        if advice:
            response += f"""**💊 Umumiy maslahat:**
{advice}

"""

        response += """**❗ Muhim eslatma:** Bu faqat umumiy ma'lumot. Aniq tashxis va davolash uchun albatta shifokor bilan maslahatlashing."""

        return response


@api_view(['POST'])
@permission_classes([AllowAny])
def classify_issue(request):
    """Tibbiy muammoni klassifikatsiya qilish (oddiy API)"""
    try:
        user_message = request.data.get('message', '').strip()

        if not user_message:
            return Response({
                'success': False,
                'error': 'Xabar bo\'sh bo\'lishi mumkin emas'
            }, status=status.HTTP_400_BAD_REQUEST)

        # AI tahlili
        gemini_service = GeminiService()
        result = gemini_service.classify_medical_issue(user_message)

        return Response({
            'success': True,
            'classification': result,
            'specialty_display': dict(Doctor.SPECIALTIES).get(
                result.get('specialty'), result.get('specialty', '')
            ),
            'ai_available': AI_AVAILABLE
        })

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return Response({
            'success': False,
            'error': 'Tahlil qilishda xatolik yuz berdi'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_session_history(request, session_id):
    """Chat session tarixini olish"""
    try:
        session = get_object_or_404(ChatSession, id=session_id)
        messages = session.messages.order_by('created_at')

        messages_data = []
        for message in messages:
            messages_data.append({
                'id': message.id,
                'sender_type': message.sender_type,
                'message_type': message.message_type,
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
                'metadata': message.metadata
            })

        return Response({
            'success': True,
            'session': {
                'id': str(session.id),
                'status': session.status,
                'detected_specialty': session.detected_specialty,
                'confidence_score': session.confidence_score,
                'total_messages': session.total_messages,
                'created_at': session.created_at.isoformat()
            },
            'messages': messages_data
        })

    except Exception as e:
        logger.error(f"Session history error: {e}")
        return Response({
            'success': False,
            'error': 'Session tarixini olishda xatolik'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_feedback(request):
    """Chat uchun fikr-mulohaza yuborish"""
    try:
        session_id = request.data.get('session_id')
        overall_rating = request.data.get('overall_rating')

        if not session_id or not overall_rating:
            return Response({
                'success': False,
                'error': 'Session ID va umumiy baho talab qilinadi'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Session topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)

        # Feedback yaratish yoki yangilash
        feedback, created = ChatFeedback.objects.get_or_create(
            session=session,
            defaults={
                'overall_rating': overall_rating,
                'ai_accuracy_rating': request.data.get('ai_accuracy_rating', overall_rating),
                'response_time_rating': request.data.get('response_time_rating', overall_rating),
                'would_recommend': request.data.get('would_recommend', True),
                'positive_feedback': request.data.get('positive_feedback', ''),
                'negative_feedback': request.data.get('negative_feedback', ''),
                'found_doctor': request.data.get('found_doctor'),
                'contacted_doctor': request.data.get('contacted_doctor')
            }
        )

        return Response({
            'success': True,
            'message': 'Fikr-mulohaza saqlandi. Rahmat!',
            'feedback_id': feedback.id
        })

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return Response({
            'success': False,
            'error': 'Fikr-mulohaza yuborishda xatolik'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
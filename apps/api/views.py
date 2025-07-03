from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import date, timedelta

from apps.doctors.models import Doctor
from apps.chat.models import ChatSession, ChatMessage
from apps.consultations.models import Consultation, Review

# Chat API'lari kengaytirilgan import
try:
    from apps.ai_assistant.services import GeminiService

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


    class GeminiService:
        def classify_medical_issue(self, message, context=None):
            return {'specialty': 'terapevt', 'confidence': 0.5, 'explanation': 'Fallback'}


@api_view(['GET'])
@permission_classes([AllowAny])
def api_overview(request):
    """API umumiy ko'rinish"""
    return Response({
        'message': 'Tibbiy Konsultatsiya API',
        'version': '1.0.0',
        'ai_available': AI_AVAILABLE,
        'endpoints': {
            'chat': '/api/chat/',
            'doctors': '/api/doctors/',
            'users': '/api/users/',
            'consultations': '/api/consultations/',
            'quick_endpoints': {
                'send_message': '/api/quick/send-message/',
                'get_doctors': '/api/quick/doctors/',
                'get_specialties': '/api/quick/specialties/',
                'search_doctors': '/api/quick/search-doctors/',
                'health_check': '/api/quick/health/',
                'stats': '/api/quick/stats/'
            }
        },
        'documentation': '/api/',
        'timestamp': timezone.now().isoformat()
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def quick_send_message(request):
    """Tez chat xabar yuborish"""
    try:
        message = request.data.get('message', '').strip()
        if not message:
            return Response({
                'success': False,
                'error': 'Xabar bo\'sh bo\'lishi mumkin emas'
            }, status=400)

        # Session yaratish
        session = ChatSession.objects.create(
            session_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # User xabarini saqlash
        user_message = ChatMessage.objects.create(
            session=session,
            sender_type='user',
            message_type='text',
            content=message
        )

        # AI tahlil
        gemini_service = GeminiService()
        classification = gemini_service.classify_medical_issue(message)

        # Session yangilash
        session.detected_specialty = classification.get('specialty')
        session.confidence_score = classification.get('confidence', 0.5)
        session.save()

        # Shifokorlarni topish
        doctors = Doctor.objects.filter(
            specialty=classification.get('specialty'),
            is_available=True
        ).order_by('-rating')[:3]

        doctors_data = []
        for doctor in doctors:
            doctors_data.append({
                'id': doctor.id,
                'name': doctor.get_short_name(),
                'specialty': doctor.get_specialty_display(),
                'experience': doctor.experience,
                'rating': float(doctor.rating),
                'total_reviews': doctor.total_reviews,
                'consultation_price': float(doctor.consultation_price),
                'workplace': doctor.workplace,
                'phone': doctor.phone,
                'is_online_consultation': doctor.is_online_consultation
            })

        # AI javob yaratish
        specialty_display = dict(Doctor.SPECIALTIES).get(
            classification.get('specialty'),
            classification.get('specialty', 'Terapevt')
        )

        ai_response = f"""**Sizning muammoingizni tahlil qildim.**

🔍 **Tavsiya etilgan mutaxassis:** {specialty_display}
📊 **Ishonch darajasi:** {classification.get('confidence', 0.5) * 100:.0f}%
💡 **Sabab:** {classification.get('explanation', '')}

**🏥 Tavsiya etilgan shifokorlar:**
"""

        for i, doctor in enumerate(doctors_data, 1):
            ai_response += f"""
{i}. **{doctor['name']}**
   - Tajriba: {doctor['experience']} yil
   - Reyting: {doctor['rating']}/5 ⭐ ({doctor['total_reviews']} sharh)
   - Narx: {doctor['consultation_price']:,.0f} so'm
   - Telefon: {doctor['phone']}
"""

        ai_response += "\n**❗ Muhim:** Bu umumiy maslahat. Aniq tashxis uchun shifokor bilan maslahatlashing."

        # AI xabarini saqlash
        ai_message = ChatMessage.objects.create(
            session=session,
            sender_type='ai',
            message_type='text',
            content=ai_response,
            ai_model_used=classification.get('model_used', 'fallback'),
            ai_response_time=classification.get('processing_time', 0)
        )

        return Response({
            'success': True,
            'session_id': str(session.id),
            'user_message': {
                'content': message,
                'timestamp': user_message.created_at.isoformat()
            },
            'ai_response': {
                'content': ai_response,
                'timestamp': ai_message.created_at.isoformat()
            },
            'classification': classification,
            'recommended_doctors': doctors_data,
            'ai_available': AI_AVAILABLE
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': 'Xatolik yuz berdi: ' + str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_get_doctors(request):
    """Tez shifokorlar ro'yxati"""
    specialty = request.GET.get('specialty')
    region = request.GET.get('region')
    max_price = request.GET.get('max_price')
    limit = int(request.GET.get('limit', 10))

    doctors = Doctor.objects.filter(is_available=True)

    if specialty:
        doctors = doctors.filter(specialty=specialty)
    if region:
        doctors = doctors.filter(region__icontains=region)
    if max_price:
        try:
            doctors = doctors.filter(consultation_price__lte=float(max_price))
        except ValueError:
            pass

    doctors = doctors.order_by('-rating', 'consultation_price')[:limit]

    doctors_data = []
    for doctor in doctors:
        doctors_data.append({
            'id': doctor.id,
            'name': doctor.get_short_name(),
            'full_name': doctor.get_full_name(),
            'specialty': doctor.specialty,
            'specialty_display': doctor.get_specialty_display(),
            'experience': doctor.experience,
            'rating': float(doctor.rating),
            'total_reviews': doctor.total_reviews,
            'consultation_price': float(doctor.consultation_price),
            'workplace': doctor.workplace,
            'region': doctor.region,
            'district': doctor.district,
            'phone': doctor.phone,
            'email': doctor.email,
            'is_available': doctor.is_available,
            'is_online_consultation': doctor.is_online_consultation,
            'photo_url': doctor.photo.url if doctor.photo else None,
            'work_start_time': doctor.work_start_time.strftime('%H:%M'),
            'work_end_time': doctor.work_end_time.strftime('%H:%M'),
            'bio': doctor.bio or ''
        })

    return Response({
        'success': True,
        'count': len(doctors_data),
        'doctors': doctors_data,
        'filters': {
            'specialty': specialty,
            'region': region,
            'max_price': max_price,
            'limit': limit
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_get_specialties(request):
    """Barcha mutaxassisliklar ro'yxati"""
    specialties = []

    for code, name in Doctor.SPECIALTIES:
        count = Doctor.objects.filter(specialty=code, is_available=True).count()
        specialties.append({
            'code': code,
            'name': name,
            'count': count,
            'available': count > 0
        })

    return Response({
        'success': True,
        'specialties': specialties,
        'total_specialties': len(specialties),
        'total_doctors': sum(s['count'] for s in specialties)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_search_doctors(request):
    """Tez shifokor qidirish"""
    query = request.GET.get('q', '').strip()
    if not query:
        return Response({
            'success': False,
            'error': 'Qidiruv so\'zi kiritilmagan'
        }, status=400)

    # Shifokor ismi yoki ish joyi bo'yicha qidirish
    doctors = Doctor.objects.filter(
        models.Q(first_name__icontains=query) |
        models.Q(last_name__icontains=query) |
        models.Q(workplace__icontains=query) |
        models.Q(bio__icontains=query),
        is_available=True
    ).order_by('-rating')[:20]

    results = []
    for doctor in doctors:
        results.append({
            'id': doctor.id,
            'name': doctor.get_short_name(),
            'specialty': doctor.get_specialty_display(),
            'experience': doctor.experience,
            'rating': float(doctor.rating),
            'consultation_price': float(doctor.consultation_price),
            'workplace': doctor.workplace,
            'phone': doctor.phone,
            'region': doctor.region,
            'match_reason': 'name' if query.lower() in doctor.get_full_name().lower() else 'workplace'
        })

    return Response({
        'success': True,
        'query': query,
        'count': len(results),
        'results': results
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_health_check(request):
    """Tizim holatini tekshirish"""
    try:
        # Database ulanishini tekshirish
        doctors_count = Doctor.objects.count()
        sessions_count = ChatSession.objects.count()

        # AI xizmatini tekshirish
        ai_status = 'available' if AI_AVAILABLE else 'unavailable'

        return Response({
            'success': True,
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': {
                'status': 'connected',
                'doctors_count': doctors_count,
                'chat_sessions_count': sessions_count
            },
            'ai_service': {
                'status': ai_status,
                'available': AI_AVAILABLE
            },
            'version': '1.0.0'
        })

    except Exception as e:
        return Response({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_stats(request):
    """Tizim statistikasi"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    try:
        stats = {
            'doctors': {
                'total': Doctor.objects.count(),
                'available': Doctor.objects.filter(is_available=True).count(),
                'online_consultation': Doctor.objects.filter(
                    is_available=True,
                    is_online_consultation=True
                ).count(),
                'by_specialty': dict(
                    Doctor.objects.filter(is_available=True)
                    .values('specialty')
                    .annotate(count=Count('id'))
                    .values_list('specialty', 'count')
                ),
                'avg_rating': Doctor.objects.filter(is_available=True)
                              .aggregate(avg=Avg('rating'))['avg'] or 0,
                'avg_price': Doctor.objects.filter(is_available=True)
                             .aggregate(avg=Avg('consultation_price'))['avg'] or 0
            },

            'chat': {
                'total_sessions': ChatSession.objects.count(),
                'active_sessions': ChatSession.objects.filter(status='active').count(),
                'sessions_today': ChatSession.objects.filter(
                    created_at__date=today
                ).count(),
                'sessions_this_week': ChatSession.objects.filter(
                    created_at__date__gte=week_ago
                ).count(),
                'total_messages': ChatMessage.objects.count(),
                'ai_available': AI_AVAILABLE,
                'top_specialties': list(
                    ChatSession.objects.filter(detected_specialty__isnull=False)
                    .values('detected_specialty')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )
            },

            'consultations': {
                'total': Consultation.objects.count(),
                'today': Consultation.objects.filter(scheduled_date=today).count(),
                'this_week': Consultation.objects.filter(
                    scheduled_date__gte=week_ago
                ).count(),
                'by_status': dict(
                    Consultation.objects.values('status')
                    .annotate(count=Count('id'))
                    .values_list('status', 'count')
                )
            },

            'reviews': {
                'total': Review.objects.filter(is_active=True).count(),
                'avg_rating': Review.objects.filter(is_active=True)
                              .aggregate(avg=Avg('overall_rating'))['avg'] or 0,
                'verified': Review.objects.filter(
                    is_active=True,
                    is_verified=True
                ).count()
            },

            'timestamp': timezone.now().isoformat(),
            'ai_available': AI_AVAILABLE
        }

        return Response({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


def get_client_ip(request):
    """Client IP manzilini olish"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
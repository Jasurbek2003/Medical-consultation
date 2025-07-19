from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
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
            'chat': {
                'send_message': '/api/chat/send-message/',
                'classify': '/api/chat/classify/',
                'sessions': '/api/chat/sessions/',
                'quick_message': '/api/chat/quick-message/'
            },
            'doctors': {
                'list': '/api/doctors/',
                'search': '/api/doctors/search/',
                'specialties': '/api/doctors/specialties/',
                'by_specialty': '/api/doctors/by-specialty/'
            },
            'users': '/api/users/',
            'consultations': '/api/consultations/',
            'system': {
                'health': '/api/health/',
                'stats': '/api/stats/',
                'regions': '/api/regions/',
                'emergency': '/api/emergency-info/'
            }
        },
        'documentation': '/docs/',
        'timestamp': timezone.now().isoformat()
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def quick_send_message(request):
    """Tez chat xabar yuborish - to'liq AI tahlil bilan"""
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
        ).order_by('-rating')[:5]

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
                'is_online_consultation': doctor.is_online_consultation,
                'photo_url': doctor.photo.url if doctor.photo else None
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

        for i, doctor in enumerate(doctors_data[:3], 1):
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


@api_view(['POST'])
@permission_classes([AllowAny])
def quick_classify_issue(request):
    """Tez klassifikatsiya - faqat tahlil"""
    try:
        message = request.data.get('message', '').strip()
        if not message:
            return Response({
                'success': False,
                'error': 'Xabar bo\'sh bo\'lishi mumkin emas'
            }, status=400)

        # AI tahlili
        gemini_service = GeminiService()
        result = gemini_service.classify_medical_issue(message)

        return Response({
            'success': True,
            'classification': result,
            'specialty_display': dict(Doctor.SPECIALTIES).get(
                result.get('specialty'), result.get('specialty', '')
            ),
            'ai_available': AI_AVAILABLE
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': 'Tahlil qilishda xatolik: ' + str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_get_doctors(request):
    """Tez shifokorlar ro'yxati"""
    specialty = request.GET.get('specialty')
    region = request.GET.get('region')
    max_price = request.GET.get('max_price')
    online_only = request.GET.get('online_only') == 'true'
    limit = int(request.GET.get('limit', 20))

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
    if online_only:
        doctors = doctors.filter(is_online_consultation=True)

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
            'email': doctor.email or '',
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
            'online_only': online_only,
            'limit': limit
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_get_specialties(request):
    """Barcha mutaxassisliklar ro'yxati"""
    include_count = request.GET.get('include_count', 'true') == 'true'

    specialties = []
    for code, name in Doctor.SPECIALTIES:
        specialty_data = {
            'code': code,
            'name': name
        }

        if include_count:
            count = Doctor.objects.filter(specialty=code, is_available=True).count()
            specialty_data.update({
                'count': count,
                'available': count > 0
            })

        specialties.append(specialty_data)

    total_doctors = Doctor.objects.filter(is_available=True).count() if include_count else 0

    return Response({
        'success': True,
        'specialties': specialties,
        'total_specialties': len(specialties),
        'total_doctors': total_doctors
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_doctors_by_specialty(request):
    """Mutaxassislik bo'yicha shifokorlar"""
    specialty = request.GET.get('specialty')
    if not specialty:
        return Response({
            'success': False,
            'error': 'specialty parametri talab qilinadi'
        }, status=400)

    limit = int(request.GET.get('limit', 10))

    doctors = Doctor.objects.filter(
        specialty=specialty,
        is_available=True
    ).order_by('-rating', 'consultation_price')[:limit]

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
            'region': doctor.region,
            'phone': doctor.phone,
            'is_online_consultation': doctor.is_online_consultation,
            'photo_url': doctor.photo.url if doctor.photo else None
        })

    return Response({
        'success': True,
        'specialty': specialty,
        'specialty_display': dict(Doctor.SPECIALTIES).get(specialty, specialty),
        'count': len(doctors_data),
        'doctors': doctors_data
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
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(workplace__icontains=query) |
        Q(bio__icontains=query),
        is_available=True
    ).order_by('-rating')[:20]

    results = []
    for doctor in doctors:
        # Match reason aniqlash
        match_reason = 'name' if query.lower() in doctor.get_full_name().lower() else 'workplace'

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
            'match_reason': match_reason
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


@api_view(['GET'])
@permission_classes([AllowAny])
def get_regions(request):
    """Barcha viloyatlar ro'yxati"""
    try:
        # Shifokorlardan mavjud viloyatlarni olish
        regions = Doctor.objects.values_list('region', flat=True).distinct()
        regions = [region for region in regions if region]  # Bo'sh qiymatlarni olib tashlash

        # Har bir viloyat uchun shifokorlar sonini hisoblash
        regions_with_count = []
        for region in sorted(regions):
            count = Doctor.objects.filter(region=region, is_available=True).count()
            regions_with_count.append({
                'name': region,
                'count': count
            })

        return Response({
            'success': True,
            'regions': regions_with_count,
            'total_regions': len(regions_with_count)
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_emergency_info(request):
    """Shoshilinch yordam ma'lumotlari"""
    emergency_info = {
        'emergency_numbers': [
            {
                'service': 'Tez yordam',
                'number': '103',
                'description': 'Tibbiy shoshilinch yordam'
            },
            {
                'service': "Yong'in xizmati",
                'number': '101',
                'description': "Yong'in va qutqaruv xizmati"
            },
            {
                'service': 'Politsiya',
                'number': '102',
                'description': 'Politsiya xizmati'
            },
            {
                'service': "Yagona qo'ng'iroq markazi",
                'number': '112',
                'description': 'Barcha shoshilinch xizmatlar'
            }
        ],

        'urgent_symptoms': [
            {
                'symptom': "Ko'krak og'rig'i",
                'action': "Zudlik bilan 103 ga qo'ng'iroq qiling",
                'priority': 'critical'
            },
            {
                'symptom': 'Nafas qisilishi',
                'action': 'Tez yordam chaqiring',
                'priority': 'critical'
            },
            {
                'symptom': "Hushni yo'qotish",
                'action': "Darhol 103 ga qo'ng'iroq qiling",
                'priority': 'critical'
            },
            {
                'symptom': 'Yuqori harorat (39°C+)',
                'action': "Shifokor bilan bog'laning yoki shifoxonaga boring",
                'priority': 'high'
            },
            {
                'symptom': "Keskin qorin og'rig'i",
                'action': 'Tez yordam chaqiring',
                'priority': 'high'
            }
        ],

        'first_aid_tips': [
            {
                'situation': 'Yurak tutilishi',
                'steps': [
                    "103 ga qo'ng'iroq qiling",
                    'Bemorni yotqizing',
                    "Ko'krakning o'rtasiga qattiq bosing",
                    'CPR boshlang (agar bilsangiz)'
                ]
            },
            {
                'situation': 'Qon ketish',
                'steps': [
                    'Toza mato bilan bosing',
                    'Jarohatni yuqoriga ko\'taring',
                    'Bosimni davom eting',
                    'Tez yordam chaqiring'
                ]
            },
            {
                'situation': 'Kuyish',
                'steps': [
                    'Sovuq suv bilan yuvib chiqing',
                    "Toza mato bilan o'rang",
                    "Muz qo'ymang",
                    'Shifokorga murojaat qiling'
                ]
            }
        ],

        'hospitals': [
            {
                'name': 'Respublika Shoshilinch Tibbiy Yordam Markazi',
                'address': 'Toshkent shahar, Farabi ko\'chasi 2',
                'phone': '+998712441515',
                'available_24_7': True
            },
            {
                'name': 'Toshkent Tibbiy Akademiyasi Klinikasi',
                'address': 'Toshkent shahar, Farabi ko\'chasi 2',
                'phone': '+998712441414',
                'available_24_7': True
            }
        ],

        'warning': "Bu ma'lumotlar faqat umumiy yo'l-yo'riq uchun. Shoshilinch holatda darhol 103 ga qo'ng'iroq qiling!"
    }

    return Response({
        'success': True,
        'emergency_info': emergency_info
    })


def get_client_ip(request):
    """Client IP manzilini olish"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def custom_404(request, exception):
    """Custom 404 page"""
    from django.shortcuts import render
    from django.http import JsonResponse

    if request.content_type == 'application/json' or 'api' in request.path:
        return JsonResponse({
            'error': 'Page not found',
            'status': 404,
            'message': 'The requested resource was not found.'
        }, status=404)

    return render(request, '404.html', status=404)


def custom_500(request):
    """Custom 500 page"""
    from django.shortcuts import render
    from django.http import JsonResponse

    if request.content_type == 'application/json' or 'api' in request.path:
        return JsonResponse({
            'error': 'Internal server error',
            'status': 500,
            'message': 'An internal server error occurred.'
        }, status=500)

    return render(request, '500.html', status=500)
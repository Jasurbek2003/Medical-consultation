from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework import  status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils.translation import get_language, activate
from django.utils.translation import gettext as _

# Models
from .models import ChatSession, ChatMessage, DoctorRecommendation, ChatFeedback
from apps.doctors.models import Doctor

# AI Service - try/except bilan himoyalash
try:
    from apps.ai_assistant.services import GeminiService

    AI_AVAILABLE = True
except ImportError as e:
    print(f"AI Service import error: {e}")
    AI_AVAILABLE = False


    class GeminiService:
        def classify_medical_issue(self, user_message, user_context=None, language='uz'):
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
                'explanation': _('Oddiy kalit so\'z tahlili asosida'),
                'processing_time': 0.1,
                'model_used': 'fallback',
                'symptoms_analysis': {'detected_symptoms': [], 'keywords': []},
                'urgency_assessment': {'urgency_level': 'medium', 'description': _('Shifokorga ko\'rsating')}
            }

        def get_medical_advice(self, user_message, specialty, symptoms=None, language='uz'):
            advice_map = {
                'terapevt': _('Umumiy holatni yaxshilash uchun shifokorga murojaat qiling.'),
                'stomatolog': _('Tish gigienasini saqlang va shifokorga ko\'rsating.'),
                'kardiolog': _('Qon bosimingizni nazorat qiling.'),
                'urolog': _('Ko\'p suv iching va shifokorga murojaat qiling.')
            }

            return {
                'advice': advice_map.get(specialty, _('Shifokor bilan maslahatlashing.')),
                'specialty': specialty,
                'processing_time': 0.1,
                'model_used': 'fallback'
            }

import json
import logging

logger = logging.getLogger(__name__)


# ============================================
# API VIEWS (JSON response qaytaradi)
# ============================================

def get_client_ip(request):
    """Client IP manzilini olish"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@method_decorator(csrf_exempt, name='dispatch')
class ChatMessageView(TemplateView):
    """Chat xabar yuborish API (JSON response)"""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            session_id = data.get('session_id')
            user_language = data.get('language', get_language())  # Til parametri

            # Tilni o'rnatish
            if user_language:
                activate(user_language)

            if not user_message:
                return JsonResponse({
                    'success': False,
                    'error': _('Xabar bo\'sh bo\'lishi mumkin emas')
                }, status=400)

                # Session olish yoki yaratish
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id)
                except ChatSession.DoesNotExist:
                    session = self._create_session(request, user_language)
            else:
                session = self._create_session(request, user_language)

                # Foydalanuvchi xabarini saqlash
            user_chat_message = ChatMessage.objects.create(
                session=session,
                sender_type='user',
                message_type='text',
                content=user_message,
                metadata={'language': user_language}
            )

            # Xabar turini aniqlash
            message_type = self._analyze_message_type(user_message, session, user_language)

            if message_type == 'greeting':
                ai_response = self._get_greeting_response(user_language)
            elif message_type == 'general_question':
                ai_response = self._get_clarification_response(user_language)
            elif message_type == 'medical_complaint':
                ai_response = self._process_medical_complaint(user_message, session, request, user_language)
            else:
                ai_response = self._get_help_response(user_language)

            # AI javob xabarini saqlash
            ai_chat_message = ChatMessage.objects.create(
                session=session,
                sender_type='ai',
                message_type='text',
                content=ai_response['content'],
                ai_model_used=ai_response.get('model_used', 'rule-based'),
                ai_response_time=ai_response.get('processing_time', 0.1),
                metadata={**ai_response.get('metadata', {}), 'language': user_language}
            )

            return JsonResponse({
                'success': True,
                'session_id': str(session.id),
                'user_message': {
                    'id': user_chat_message.id,
                    'content': user_message,
                    'timestamp': user_chat_message.created_at.isoformat(),
                    'language': user_language
                },
                'ai_response': {
                    'id': ai_chat_message.id,
                    'content': ai_response['content'],
                    'timestamp': ai_chat_message.created_at.isoformat(),
                    'metadata': ai_response.get('metadata', {}),
                    'language': user_language
                },
                'message_type': message_type,
                'ai_available': AI_AVAILABLE,
                'language': user_language
            })

        except Exception as e:
            logger.error(f"Chat message processing error: {e}")
            return JsonResponse({
                'success': False,
                'error': _('Xatolik yuz berdi. Iltimos qayta urinib ko\'ring.'),
                'error_details': str(e) if settings.DEBUG else None
            }, status=500)

    def _analyze_message_type(self, message, session, language='uz'):
        """Xabar turini aniqlash (ko'p tilli)"""
        message_lower = message.lower().strip()

        # Ko'p tilli salomlashish so'zlari
        greeting_words = {
            'uz': ['salom', 'assalomu alaykum', 'alik'],
            'ru': ['привет', 'здравствуйте', 'добро пожаловать', 'салам'],
            'en': ['hello', 'hi', 'hey', 'good morning', 'good day']
        }

        current_greetings = greeting_words.get(language, greeting_words['uz'])
        for word in current_greetings:
            if message_lower.startswith(word) and len(message_lower.split()) <= 2:
                return 'greeting'

        # Ko'p tilli tibbiy kalit so'zlar
        from apps.ai_assistant.prompts import get_symptom_keywords
        medical_keywords = []

        # Hozirgi til va boshqa tillarning kalit so'zlarini olish
        for lang in ['uz', 'ru', 'en']:
            lang_keywords = get_symptom_keywords(lang)
            for specialty_keywords in lang_keywords.values():
                medical_keywords.extend(specialty_keywords)

        # Kalit so'zlarni tekshirish
        for keyword in medical_keywords:
            if keyword in message_lower:
                return 'medical_complaint'

        # Umumiy savollar
        if len(message.split()) <= 2 and '?' not in message:
            return 'general_question'

        # Aniq tibbiy shikoyat (uzunroq matn)
        if len(message.split()) >= 3:
            return 'medical_complaint'

        return 'general_question'

    # def _analyze_message_type(self, message, session):
    #     """Xabar turini aniqlash"""
    #     message_lower = message.lower().strip()
    #     # Salomlashish so'zlari
    #     greeting_words = ['salom', 'assalomu alaykum', 'alik', 'hello', 'hi', 'hey']
    #     for word in greeting_words:
    #         if message_lower.startswith(word) and len(message_lower.split()) <= 3:
    #             return 'greeting'
    #
    #     # Tana a'zolari va organlar
    #     body_parts = [
    #         'tish', 'bosh', 'qorin', 'yurak', 'jigar', 'buyrak', 'ichak',
    #         'oshqozon', 'teri', "ko'z", 'quloq', 'nafas', 'qon'
    #     ]
    #
    #     # Simptomlar va alomatlar
    #     symptoms = [
    #         "og'riq", "og'riyapti", 'harorat', "yo'tal", 'allergiya',
    #         'stress', 'charchoq', 'holsizlik', 'qichish', "shish",
    #         'isitma', 'bosh aylanishi', 'belgi', 'alomat', 'qizaloq',
    #         'bezgak', "yon ta'sir"
    #     ]
    #
    #     # Kasalliklar
    #     diseases = [
    #         'kasallik', 'shamollash', 'gripp', 'sovuq', 'angina', 'bronxit',
    #         'astma', 'diabat', 'bosim', 'gipertaniya', 'hipotaniya',
    #         'migran', 'qandli'
    #     ]
    #
    #     # Tibbiy mutaxassislar
    #     medical_specialists = [
    #         'shifokor', 'hamshira', 'mutaxassis', 'nevropatolog', 'kardiolog',
    #         'oftalmolog', 'lor', 'ginekolog', 'pediatr', 'terapevt',
    #         'stomatolog', "stamatolog", 'urolog', 'xirurg', 'radiolog', 'laborant',
    #         'farmatsevt', 'dermatolog', 'endokrinolog', 'gastroenterolog',
    #         'pulmonolog', 'psixiatr', 'nevrolog', 'onkolog', 'reabilitolog',
    #         'fizioterapevt', 'akusher', 'androlog', 'psixolog', 'psixoterapevt',
    #         'genetik', 'immunolog', 'infektsionist', 'allergolog',
    #         'reanimatolog', 'anesteziolog'
    #     ]
    #
    #     # Dorilar va davolash usullari
    #     treatment_medicine = [
    #         'dori', 'malham', 'tabletkalar', 'kapsulalar', 'davolash',
    #         'tuzalish', 'tiklanish', 'profilaktika', 'vaksinatsiya',
    #         'emlash', 'jarrohlik', 'operatsiya', 'bandaj', 'davolanish',
    #         'instruktsiya', 'dozalash', 'kontraindikasiya', 'fizioterapiya',
    #         'retsept'
    #     ]
    #
    #     # Tibbiy tekshiruvlar va asboblar
    #     medical_tests_equipment = [
    #         'tahlil', 'tekshiruv', 'tashxis', 'rentgen', 'ultrasonografiya',
    #         'tomografiya', 'kardiogramma'
    #     ]
    #
    #     # Tibbiy muassasalar va xizmatlar
    #     medical_institutions = [
    #         'klinika', 'shifoxona', 'poliklinika', 'bemorxona', 'reanimatsiya',
    #         'ginekologiya'
    #     ]
    #
    #     # Favqulodda tibbiy yordam
    #     emergency_medical = [
    #         'tez yordam', 'shoshilinch yordam', 'favqulodda vaziyat',
    #         'favqulodda', 'kechakrish', 'zarurat', 'shoshilinch'
    #     ]
    #
    #     # Umumiy tibbiy terminlar
    #     general_medical = [
    #         'bemor', 'tibbiy', 'holat', 'ahvol', 'muloyimlik', 'siydik',
    #         'vazn', 'uyqu'
    #     ]
    #
    #     medical_keywords = (body_parts + symptoms + diseases + medical_specialists + treatment_medicine +
    #                         medical_institutions + medical_tests_equipment + emergency_medical + general_medical)
    #
    #     for keyword in medical_keywords:
    #         if keyword in message_lower.split():
    #             return 'medical_complaint'
    #
    #     uzbek_suffixes = [
    #         'im', 'lar', 'larim', 'ga', 'ni', 'da', 'dan', 'ga',
    #         'laridan', 'lari', 'lariyim', 'larimiz', 'ning', 'niki',
    #         'man', 'miz', 'san', 'siz', 'di', 'dilar', 'dik', 'dingiz',
    #         'yapti', 'yabdi', 'yotir', 'moqda', 'adi', 'ayapti',
    #         'cha', 'roq', 'gina', 'day', 'dek', 'simon'
    #     ]
    #
    #     # Har bir so'zni tekshirish
    #     for word in message_lower.split():
    #         # Qo'shimchalarni olib tashlash va ildizni topish
    #         for suffix in uzbek_suffixes:
    #             if word.endswith(suffix):
    #                 root = word[:-len(suffix)]
    #                 # To'liq mos kelishi tekshiruvi
    #                 if root in medical_keywords:
    #                     return 'medical_complaint'
    #
    #
    #
    #     # Umumiy savollar
    #     if len(message.split()) <= 5 and '?' not in message:
    #         return 'general_question'
    #
    #     # Aniq tibbiy shikoyat (uzunroq matn)
    #     if len(message.split()) > 5:
    #         return 'medical_complaint'
    #
    #     return 'general_question'

    def _get_greeting_response(self, language='uz'):
        """Ko'p tilli salomlashish javobi"""
        greeting_templates = {
            'uz': """Assalomu alaykum! Men sizning tibbiy yordamchingizman. 🏥

Men sizga to'g'ri shifokorni topishda yordam beraman.

Iltimos, muammoingizni batafsil aytib bering:
• Qanday belgilar yoki og'riqlar bor?
• Qachondan beri sezayapsiz?
• Qaysi joyda og'riq bor?

**Misollar:**
• "Ikki kundan beri boshim og'riyapti"
• "Tishim juda og'riyapti, yeyolmayapman"
• "Qon bosimim yuqori ko'tarilgan"

Sizning ma'lumotlaringiz asosida eng mos mutaxassisni tavsiya qilaman! 👨‍⚕️""",

            'ru': """Здравствуйте! Я ваш медицинский помощник. 🏥

Я помогу вам найти подходящего врача.

Пожалуйста, расскажите подробно о вашей проблеме:
• Какие симптомы или боли есть?
• Как давно вы их ощущаете?
• Где локализуется боль?

**Примеры:**
• "Уже два дня болит голова"
• "Очень болит зуб, не могу есть"
• "Повысилось артериальное давление"

На основе вашей информации я порекомендую наиболее подходящего специалиста! 👨‍⚕️""",

            'en': """Hello! I'm your medical assistant. 🏥

I'll help you find the right doctor.

Please tell me in detail about your problem:
• What symptoms or pain do you have?
• How long have you been experiencing them?
• Where is the pain located?

**Examples:**
• "I've had a headache for two days"
• "My tooth hurts a lot, I can't eat"
• "My blood pressure has risen"

Based on your information, I'll recommend the most suitable specialist! 👨‍⚕️"""
        }

        return {
            'content': greeting_templates.get(language, greeting_templates['uz']),
            'model_used': 'rule-based',
            'processing_time': 0.1,
            'metadata': {'response_type': 'greeting', 'language': language}
        }

    def _get_clarification_response(self, language='uz'):
        """Ko'p tilli qo'shimcha ma'lumot so'rash"""
        clarification_templates = {
            'uz': """Sizga yordam berish uchun muammoingizni batafsil aytib bering.

Quyidagilarni ma'lum qiling:
🔍 **Aniq qanday belgilar bor?**
⏰ **Qachondan beri sezayapsiz?**
📍 **Qaysi joyda og'riq yoki noqulaylik?**
📊 **Og'riq darajasi qanday (1-10)?**

**Misollar:**
• "3 kundan beri ko'kragimda og'riq bor, yurishda kuchayadi"
• "Bugun ertalabdan beri oshqozonim og'riyapti, qayt qilish ham bor"
• "Bir haftadan beri ko'z qichiyapti va ko'z yoshi chiqyapti"

Bu ma'lumotlar bilan sizga eng to'g'ri shifokorni tavsiya qila olaman! 🎯""",

            'ru': """Чтобы помочь вам, расскажите подробно о вашей проблеме.

Укажите следующее:
🔍 **Какие именно симптомы есть?**
⏰ **Как давно вы их ощущаете?**
📍 **Где локализуется боль или дискомфорт?**
📊 **Какая интенсивность боли (1-10)?**

**Примеры:**
• "Уже 3 дня болит в груди, усиливается при ходьбе"
• "С утра болит живот, есть тошнота"
• "Неделю чешутся глаза и слезятся"

С этой информацией я смогу порекомендовать вам самого подходящего врача! 🎯""",

            'en': """To help you, please tell me in detail about your problem.

Please specify:
🔍 **What exact symptoms do you have?**
⏰ **How long have you been experiencing them?**
📍 **Where is the pain or discomfort located?**
📊 **What's the pain intensity (1-10)?**

**Examples:**
• "Chest pain for 3 days, gets worse when walking"
• "Stomach pain since morning, with nausea"
• "Eyes have been itchy and watery for a week"

With this information, I can recommend the most suitable doctor for you! 🎯"""
        }

        return {
            'content': clarification_templates.get(language, clarification_templates['uz']),
            'model_used': 'rule-based',
            'processing_time': 0.1,
            'metadata': {'response_type': 'clarification', 'language': language}
        }

    def _get_help_response(self, language='uz'):
        """Ko'p tilli yordam javobi"""
        help_templates = {
            'uz': """Men sizga tibbiy masalalar bo'yicha to'g'ri shifokorni topishda yordam beraman.

**Men qila olaman:**
• Simptomlaringizni tahlil qilish
• Mos mutaxassisni tavsiya qilish
• Shifokorlar ro'yxatini ko'rsatish
• Umumiy tibbiy maslahat berish

**Foydalanish:**
Shunchaki muammoingizni oddiy tilida yozing, masalan:
"Boshim og'riyapti", "Tish og'rig'i bor", "Yurak tez uradi"

Buyurtma bering! 😊""",

            'ru': """Я помогаю найти подходящего врача по медицинским вопросам.

**Что я могу делать:**
• Анализировать ваши симптомы
• Рекомендовать подходящего специалиста
• Показывать список врачей
• Давать общие медицинские советы

**Как пользоваться:**
Просто опишите вашу проблему простыми словами, например:
"Болит голова", "Болит зуб", "Сердце быстро бьется"

Обращайтесь! 😊""",

            'en': """I help you find the right doctor for medical issues.

**What I can do:**
• Analyze your symptoms
• Recommend suitable specialists
• Show list of doctors
• Provide general medical advice

**How to use:**
Just describe your problem in simple words, for example:
"Headache", "Tooth pain", "Heart beating fast"

Feel free to ask! 😊"""
        }

        return {
            'content': help_templates.get(language, help_templates['uz']),
            'model_used': 'rule-based',
            'processing_time': 0.1,
            'metadata': {'response_type': 'help', 'language': language}
        }


    def _process_medical_complaint(self, user_message, session, request, language='uz'):
        """Ko'p tilli tibbiy shikoyatni qayta ishlash"""
        # AI tahlili
        gemini_service = GeminiService()

        # Tibbiy muammoni klassifikatsiya qilish
        classification_result = gemini_service.classify_medical_issue(
            user_message,
            user_context=self._get_user_context(request),
            language=language
        )

        # Session ma'lumotlarini yangilash
        session.detected_specialty = classification_result.get('specialty')
        session.confidence_score = classification_result.get('confidence', 0.5)
        session.save()

        # Mos shifokorlarni topish
        recommended_doctors = self._get_recommended_doctors(
            classification_result.get('specialty'),
            user_context=self._get_user_context(request)
        )

        # Tibbiy maslahat olish
        advice_result = gemini_service.get_medical_advice(
            user_message,
            classification_result.get('specialty'),
            classification_result.get('symptoms_analysis', {}).get('detected_symptoms', []),
            language=language
        )

        # Shifokor tavsiyasini saqlash
        if recommended_doctors:
            DoctorRecommendation.objects.create(
                session=session,
                recommended_doctors=recommended_doctors,
                specialty=classification_result.get('specialty'),
                reason=classification_result.get('explanation', '')
            )

        # AI javobini formatlash
        ai_response_content = self._format_medical_response(
            classification_result,
            recommended_doctors,
            advice_result.get('advice', ''),
            language
        )

        return {
            'content': ai_response_content,
            'model_used': classification_result.get('model_used', 'gemini-pro'),
            'processing_time': advice_result.get('processing_time', 0),
            'metadata': {
                'classification': classification_result,
                'doctors': recommended_doctors,
                'advice': advice_result,
                'response_type': 'medical_analysis',
                'language': language
            }
        }

    def _format_medical_response(self, classification, doctors, advice, language='uz'):
        """Ko'p tilli tibbiy javobni formatlash"""
        specialty_display = dict(Doctor.SPECIALTIES).get(
            classification.get('specialty'), classification.get('specialty', '')
        )

        # Ko'p tilli response shablonlari
        response_templates = {
            'uz': {
                'header': "**Sizning muammoingizni tahlil qildim.**\n\n",
                'specialist': "🔍 **Tavsiya etilgan mutaxassis:** {specialty}\n",
                'confidence': "📊 **Ishonch darajasi:** {confidence}%\n",
                'reason': "💡 **Sabab:** {explanation}\n\n",
                'doctors_header': "**🏥 {specialty} mutaxassislari:**\n\n",
                'no_doctors': "❌ Hozircha {specialty} mutaxassislari mavjud emas.\n\n",
                'advice_header': "**💊 Umumiy maslahat:**\n{advice}\n\n",
                'footer': "**❗ Muhim eslatma:** Bu faqat umumiy ma'lumot. Aniq tashxis va davolash uchun albatta shifokor bilan maslahatlashing.",
                'online_badge': " 💻 Online"
            },
            'ru': {
                'header': "**Я проанализировал вашу жалобу.**\n\n",
                'specialist': "🔍 **Рекомендуемый специалист:** {specialty}\n",
                'confidence': "📊 **Уровень уверенности:** {confidence}%\n",
                'reason': "💡 **Причина:** {explanation}\n\n",
                'doctors_header': "**🏥 Специалисты {specialty}:**\n\n",
                'no_doctors': "❌ В настоящее время специалисты {specialty} недоступны.\n\n",
                'advice_header': "**💊 Общие советы:**\n{advice}\n\n",
                'footer': "**❗ Важное примечание:** Это только общая информация. Для точного диагноза и лечения обязательно проконсультируйтесь с врачом.",
                'online_badge': " 💻 Онлайн"
            },
            'en': {
                'header': "**I've analyzed your complaint.**\n\n",
                'specialist': "🔍 **Recommended specialist:** {specialty}\n",
                'confidence': "📊 **Confidence level:** {confidence}%\n",
                'reason': "💡 **Reason:** {explanation}\n\n",
                'doctors_header': "**🏥 {specialty} specialists:**\n\n",
                'no_doctors': "❌ Currently no {specialty} specialists available.\n\n",
                'advice_header': "**💊 General advice:**\n{advice}\n\n",
                'footer': "**❗ Important note:** This is general information only. For accurate diagnosis and treatment, please consult with a doctor.",
                'online_badge': " 💻 Online"
            }
        }

        template = response_templates.get(language, response_templates['uz'])

        response = template['header']
        response += template['specialist'].format(specialty=specialty_display)
        response += template['confidence'].format(confidence=classification.get('confidence', 0.5) * 100)
        response += template['reason'].format(explanation=classification.get('explanation', ''))

        # Shoshilinchlik tekshirish
        urgency = classification.get('urgency_assessment', {})
        if urgency.get('urgency_level') == 'emergency':
            emergency_warnings = {
                'uz': """⚠️ **DIQQAT: Bu shoshilinch holat bo'lishi mumkin!**
Zudlik bilan eng yaqin shifoxonaga boring yoki tez yordam chaqiring: 103

""",
                'ru': """⚠️ **ВНИМАНИЕ: Это может быть экстренная ситуация!**
Срочно обратитесь в ближайшую больницу или вызовите скорую помощь: 103

""",
                'en': """⚠️ **WARNING: This may be an emergency!**
Immediately go to the nearest hospitals or call emergency services: 103

"""
            }
            response += emergency_warnings.get(language, emergency_warnings['uz'])

        if doctors:
            response += template['doctors_header'].format(specialty=specialty_display)
            for i, doctor in enumerate(doctors[:3], 1):
                online_badge = template['online_badge'] if doctor.get('is_online_consultation') else ""

                doctor_info_templates = {
                    'uz': """{i}. **{name}**{online_badge}
   - Tajriba: {experience} yil
   - Reyting: {rating}/5 ⭐ ({total_reviews} sharh)
   - Narx: {consultation_price:,.0f} so'm
   - Ish joyi: {workplace}
   - Telefon: {phone}

""",
                    'ru': """{i}. **{name}**{online_badge}
   - Опыт: {experience} лет
   - Рейтинг: {rating}/5 ⭐ ({total_reviews} отзывов)
   - Цена: {consultation_price:,.0f} сум
   - Место работы: {workplace}
   - Телефон: {phone}

""",
                    'en': """{i}. **{name}**{online_badge}
   - Experience: {experience} years
   - Rating: {rating}/5 ⭐ ({total_reviews} reviews)
   - Price: {consultation_price:,.0f} sum
   - Workplace: {workplace}
   - Phone: {phone}

"""
                }

                doctor_template = doctor_info_templates.get(language, doctor_info_templates['uz'])
                response += doctor_template.format(
                    i=i,
                    name=doctor['name'],
                    online_badge=online_badge,
                    experience=doctor['experience'],
                    rating=doctor['rating'],
                    total_reviews=doctor['total_reviews'],
                    consultation_price=doctor['consultation_price'],
                    workplace=doctor['workplace'],
                    phone=doctor['phone']
                )
        else:
            response += template['no_doctors'].format(specialty=specialty_display)

        if advice:
            response += template['advice_header'].format(advice=advice)

        response += template['footer']

        return response

    def _create_session(self, request, language='uz'):
        """Yangi chat session yaratish"""
        return ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_ip=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={'language': language}
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
            print("Getting recommended doctors for specialty:", specialty)
            doctors = Doctor.objects.filter(
                specialty=specialty,
                is_available=True
            ).order_by('-rating', 'consultation_price')[:limit]
            print(doctors)

            doctors_data = []
            for doctor in doctors:
                print(type(doctor))
                doctors_data.append({
                    'id': doctor.id,
                    'name': doctor.user.get_full_name() or doctor.user.username,
                    'specialty_display': doctor.get_specialty_display(),
                    'experience': doctor.experience,
                    'rating': float(doctor.rating),
                    'total_reviews': doctor.total_reviews,
                    'consultation_price': float(doctor.consultation_price),
                    'workplace': doctor.workplace,
                    'phone': doctor.phone,
                    'is_online_consultation': doctor.is_online_consultation,
                    'work_hours': f"{doctor.work_start_time.strftime('%H:%M')} - {doctor.work_end_time.strftime('%H:%M')}" if doctor.work_start_time and doctor.work_end_time else 'N/A',
                    'photo_url': doctor.user.avatar.url if doctor.user.avatar else None,
                    'bio': doctor.bio or '',
                    'detail_url': f'/doctors/{doctor.id}/'
                })
            print("Recommended doctors data:", doctors_data)
            return doctors_data

        except Exception as e:
            logger.error(f"Error getting recommended doctors: {e}")
            return []



@api_view(['POST'])
@permission_classes([AllowAny])
def classify_issue(request):
    """Ko'p tilli tibbiy muammoni klassifikatsiya qilish (JSON response)"""
    try:
        user_message = request.data.get('message', '').strip()
        user_language = request.data.get('language', get_language())

        if user_language:
            activate(user_language)

        if not user_message:
            return Response({
                'success': False,
                'error': _('Xabar bo\'sh bo\'lishi mumkin emas')
            }, status=status.HTTP_400_BAD_REQUEST)

        # AI tahlili
        gemini_service = GeminiService()
        result = gemini_service.classify_medical_issue(user_message, language=user_language)

        return Response({
            'success': True,
            'classification': result,
            'specialty_display': dict(Doctor.SPECIALTIES).get(
                result.get('specialty'), result.get('specialty', '')
            ),
            'ai_available': AI_AVAILABLE,
            'language': user_language
        })

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return Response({
            'success': False,
            'error': _('Tahlil qilishda xatolik yuz berdi')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_session_history(request, session_id):
    """Chat session tarixini olish (JSON response)"""
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
                'metadata': message.metadata,
                'language': message.metadata.get('language', 'uz') if message.metadata else 'uz'
            })

        return Response({
            'success': True,
            'session': {
                'id': str(session.id),
                'status': session.status,
                'detected_specialty': session.detected_specialty,
                'confidence_score': session.confidence_score,
                'total_messages': session.total_messages,
                'created_at': session.created_at.isoformat(),
                'language': session.metadata.get('language', 'uz') if session.metadata else 'uz'
            },
            'messages': messages_data
        })

    except Exception as e:
        logger.error(f"Session history error: {e}")
        return Response({
            'success': False,
            'error': _('Session tarixini olishda xatolik')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_feedback(request):
    """Ko'p tilli chat uchun fikr-mulohaza yuborish (JSON response)"""
    try:
        session_id = request.data.get('session_id')
        overall_rating = request.data.get('overall_rating')
        user_language = request.data.get('language', get_language())

        if user_language:
            activate(user_language)

        if not session_id or not overall_rating:
            return Response({
                'success': False,
                'error': _('Session ID va umumiy baho talab qilinadi')
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return Response({
                'success': False,
                'error': _('Session topilmadi')
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
            'message': _('Fikr-mulohaza saqlandi. Rahmat!'),
            'feedback_id': feedback.id,
            'language': user_language
        })

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return Response({
            'success': False,
            'error': _('Fikr-mulohaza yuborishda xatolik')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_message(request):
    """Chat xabar yuborish - yangilangan versiya"""
    try:
        user_message = request.data.get('message', '').strip()
        user_language = request.data.get('language', 'uz')
        session_id = request.data.get('session_id')

        if not user_message:
            return Response({
                'success': False,
                'error': _('Xabar bo\'sh bo\'lishi mumkin emas')
            }, status=400)

        # Session olish yoki yaratish
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
            except ChatSession.DoesNotExist:
                session = None
        else:
            session = None

        if not session:
            # Yangi session yaratish
            session = ChatSession.objects.create(
                session_ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={  # metadata to'g'ri ishlatish
                    'language': user_language,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'created_via': 'api'
                }
            )

        # User xabarini saqlash
        user_chat_message = ChatMessage.objects.create(
            session=session,
            sender_type='user',
            message_type='text',
            content=user_message,
            metadata={
                'language': user_language,
                'timestamp': timezone.now().isoformat()
            }
        )

        # AI tahlil
        gemini_service = GeminiService()
        ai_result = gemini_service.classify_medical_issue(
            user_message,
            language=user_language
        )

        # AI javobini yaratish
        ai_response_content = f"Sizning muammoingiz bo'yicha tahlil:\n\n"
        ai_response_content += f"Tavsiya etilgan mutaxassislik: {ai_result.get('specialty', 'terapevt')}\n"
        ai_response_content += f"Ishonch darajasi: {ai_result.get('confidence', 0.7) * 100:.0f}%\n"
        ai_response_content += f"Tavsif: {ai_result.get('explanation', 'Umumiy tahlil')}\n\n"

        # Shifokorlar ro'yxatini olish
        recommended_doctors = gemini_service.get_doctor_recommendations(
            specialty=ai_result.get('specialty', 'terapevt')
        )

        if recommended_doctors.get('success') and recommended_doctors.get('recommendations'):
            ai_response_content += "Tavsiya etilgan shifokorlar:\n"
            for doctor in recommended_doctors['recommendations'][:3]:
                ai_response_content += f"• {doctor['name']} - {doctor['specialty']} (Reyting: {doctor['rating']})\n"

        # AI javob xabarini saqlash
        ai_chat_message = ChatMessage.objects.create(
            session=session,
            sender_type='ai',
            message_type='doctor_recommendation',
            content=ai_response_content,
            ai_model_used=ai_result.get('model_used', 'gemini-fallback'),
            ai_response_time=ai_result.get('processing_time', 0.1),
            metadata={
                'language': user_language,
                'ai_classification': ai_result,
                'recommended_doctors': recommended_doctors.get('recommendations', [])
            }
        )

        # Session ma'lumotlarini yangilash
        session.detected_specialty = ai_result.get('specialty')
        session.confidence_score = ai_result.get('confidence', 0.7)
        session.save()

        return Response({
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
                'classification': ai_result,
                'recommended_doctors': recommended_doctors.get('recommendations', [])
            },
            'ai_available': AI_AVAILABLE,
            'language': user_language
        })

    except Exception as e:
        logger.error(f"Chat message processing error: {e}")
        return Response({
            'success': False,
            'error': _('Xatolik yuz berdi. Iltimos qayta urinib ko\'ring.')
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def quick_send_message(request):
    """Tez chat xabar yuborish - to'liq AI tahlil bilan"""
    try:
        message = request.data.get('message', '').strip()
        language = request.data.get('language', 'uz')

        if not message:
            return Response({
                'success': False,
                'error': 'Xabar bo\'sh bo\'lishi mumkin emas'
            }, status=400)

        # Session yaratish - metadata to'g'ri ishlatish
        session = ChatSession.objects.create(
            session_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={  # Bu yerda to'g'ri ishlatish
                'language': language,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'created_via': 'quick_api',
                'timestamp': timezone.now().isoformat()
            }
        )

        # User xabarini saqlash
        user_message = ChatMessage.objects.create(
            session=session,
            sender_type='user',
            message_type='text',
            content=message,
            metadata={
                'language': language,
                'message_source': 'quick_api'
            }
        )

        # AI tahlil
        gemini_service = GeminiService()
        classification_result = gemini_service.classify_medical_issue(
            message,
            language=language
        )

        # Shifokorlar tavsiyasi
        doctor_recommendations = gemini_service.get_doctor_recommendations(
            specialty=classification_result.get('specialty', 'terapevt')
        )

        # AI javob yaratish
        ai_content = f"🏥 **Tibbiy Tahlil Natijasi**\n\n"
        ai_content += f"📋 **Tavsiya etilgan mutaxassislik:** {classification_result.get('specialty', 'terapevt')}\n"
        ai_content += f"📊 **Ishonch darajasi:** {classification_result.get('confidence', 0.7) * 100:.0f}%\n"
        ai_content += f"💡 **Tahlil:** {classification_result.get('explanation', 'Umumiy tahlil')}\n\n"

        if doctor_recommendations.get('success') and doctor_recommendations.get('recommendations'):
            ai_content += "👨‍⚕️ **Tavsiya etilgan shifokorlar:**\n\n"
            for i, doctor in enumerate(doctor_recommendations['recommendations'][:3], 1):
                ai_content += f"{i}. **{doctor['name']}**\n"
                ai_content += f"   • Mutaxassislik: {doctor['specialty']}\n"
                ai_content += f"   • Tajriba: {doctor['experience']} yil\n"
                ai_content += f"   • Reyting: ⭐ {doctor['rating']}/5\n"
                ai_content += f"   • Narx: {doctor['price']} so'm\n"
                ai_content += f"   • Tel: {doctor['phone']}\n\n"

        # AI javob xabarini saqlash
        ai_message = ChatMessage.objects.create(
            session=session,
            sender_type='ai',
            message_type='doctor_recommendation',
            content=ai_content,
            ai_model_used=classification_result.get('model_used', 'gemini-fallback'),
            ai_response_time=classification_result.get('processing_time', 0.1),
            metadata={
                'language': language,
                'classification': classification_result,
                'doctor_recommendations': doctor_recommendations.get('recommendations', []),
                'response_type': 'quick_analysis'
            }
        )

        # Session yangilash
        session.detected_specialty = classification_result.get('specialty')
        session.confidence_score = classification_result.get('confidence', 0.7)
        session.save()

        return Response({
            'success': True,
            'session_id': str(session.id),
            'message_id': user_message.id,
            'ai_response_id': ai_message.id,
            'classification': {
                'specialty': classification_result.get('specialty'),
                'confidence': classification_result.get('confidence'),
                'explanation': classification_result.get('explanation')
            },
            'ai_response': ai_content,
            'recommended_doctors': doctor_recommendations.get('recommendations', []),
            'ai_available': AI_AVAILABLE,
            'language': language,
            'processing_time': classification_result.get('processing_time', 0.1)
        })

    except Exception as e:
        logger.error(f"Quick message error: {e}")
        return Response({
            'success': False,
            'error': f'Xatolik yuz berdi: {str(e)}'
        }, status=500)
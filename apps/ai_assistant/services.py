"""
AI Assistant Services - Gemini AI Integration
"""

import json
import time
import logging
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from django.core.cache import cache
from django.conf import settings
from django.utils.translation import get_language, gettext as _

# Google Gemini AI
try:
    import google.generativeai as genai

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Google Gemini AI bilan ishlash uchun servis
    """

    def __init__(self):
        """Servisni ishga tushirish"""
        self.model = None
        self.generation_config = None

        if AI_AVAILABLE and hasattr(settings, 'GOOGLE_API_KEY'):
            try:
                # Gemini sozlash
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

                # Generation config
                self.generation_config = genai.GenerationConfig(
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=1024,
                    response_mime_type="text/plain"
                )

                logger.info("Gemini AI muvaffaqiyatli ulandi")

            except Exception as e:
                logger.error(f"Gemini AI ulanish xatoligi: {e}")
                self.model = None
        else:
            logger.warning("Gemini API key topilmadi yoki kutubxona mavjud emas")

    def classify_medical_issue(self, user_message, user_context=None, language='uz'):
        """
        Tibbiy muammoni tasniflash va shifokor turini aniqlash

        Args:
            user_message (str): Foydalanuvchi xabari
            user_context (dict): Qo'shimcha kontekst ma'lumotlari
            language (str): Til kodi (default: 'uz')

        Returns:
            dict: Tasnif natijasi
        """
        try:
            start_time = time.time()

            # Cache kaliti yaratish
            cache_key = f"medical_classification_{hashlib.md5(user_message.encode()).hexdigest()}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result

            # Agar AI mavjud bo'lmasa, fallback ishlatish
            if not self.model:
                return self._get_fallback_classification(user_message)

            from .prompts import get_prompt
            # Prompt yaratish
            prompt = get_prompt('classification', language).format(user_message=user_message)

            # AI'dan javob olish
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            # Javobni qayta ishlash
            processing_time = time.time() - start_time
            result = self._process_classification_response(
                response.text,
                user_message,
                processing_time
            )

            # Cache'ga saqlash (5 daqiqa)
            cache.set(cache_key, result, 300)

            logger.info(f"Medical classification yakunlandi: {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Medical classification xatolik: {e}")
            return self._get_fallback_classification(user_message)

    def get_medical_advice(self, user_message, specialty, symptoms=None, language='uz'):
        """
        Tibbiy maslahat berish

        Args:
            user_message (str): Foydalanuvchi xabari
            specialty (str): Aniqlangan mutaxassislik
            symptoms (list): Aniqlangan simptomlar
            language (str): Til kodi (default: 'uz')

        Returns:
            dict: Maslahat natijasi
        """
        try:
            start_time = time.time()

            if not self.model:
                return self._get_fallback_advice(specialty)

            from .prompts import get_prompt

            prompt = get_prompt('advice', language).format(
                user_message=user_message,
                specialty=specialty
            )

            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            processing_time = time.time() - start_time

            result = {
                'advice': response.text,
                'specialty': specialty,
                'processing_time': processing_time,
                'model_used': 'gemini-2.0-flash',
                'timestamp': time.time()
            }

            logger.info(f"Medical advice yakunlandi: {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Medical advice xatolik: {e}")
            return self._get_fallback_advice(specialty)

    def analyze_symptoms(self, text, language='uz'):
        """
        Simptomlarni tahlil qilish

        Args:
            text (str): Tahlil qilinadigan matn

        Returns:
            dict: Simptom tahlili
        """
        try:
            # Oddiy kalit so'z tahlili
            text_lower = text.lower()
            detected_symptoms = []
            keywords = []

            from .prompts import SYMPTOM_KEYWORDS
            for symptom_category, symptom_list in SYMPTOM_KEYWORDS.items():
                for symptom in symptom_list:
                    if symptom in text_lower:
                        detected_symptoms.append({
                            'symptom': symptom,
                            'category': symptom_category,
                            'confidence': 0.8
                        })
                        keywords.append(symptom)

            return {
                'detected_symptoms': detected_symptoms,
                'keywords': keywords,
                'total_symptoms': len(detected_symptoms),
                'categories': list(set([s['category'] for s in detected_symptoms]))
            }

        except Exception as e:
            logger.error(f"Symptom analysis xatolik: {e}")
            return {
                'detected_symptoms': [],
                'keywords': [],
                'total_symptoms': 0,
                'categories': []
            }

    def assess_urgency(self, symptoms, user_message, language='uz'):
        """
        Shoshilinchlik darajasini baholash

        Args:
            symptoms (list): Aniqlangan simptomlar
            user_message (str): Foydalanuvchi xabari

        Returns:
            dict: Shoshilinchlik bahosi
        """
        try:
            urgency_score = 0
            urgency_keywords = {
                'urgent': ['tez', 'shoshilinch', 'og\'riq', 'qon', 'yurak', 'nafas'],
                'high': ['kuchli', 'zo\'r', 'og\'ir', 'isitma'],
                'medium': ['sekin', 'bosim', 'stress'],
                'low': ['oddiy', 'kichik', 'yengil']
            }

            message_lower = user_message.lower()

            # Urgency keywords bo'yicha ball berish
            for level, keywords in urgency_keywords.items():
                for keyword in keywords:
                    if keyword in message_lower:
                        if level == 'urgent':
                            urgency_score += 5
                        elif level == 'high':
                            urgency_score += 3
                        elif level == 'medium':
                            urgency_score += 1

            # Urgency level aniqlash
            if urgency_score >= 5:
                level = 'urgent'
                description = 'Darhol tibbiy yordam kerak'
            elif urgency_score >= 3:
                level = 'high'
                description = 'Tez orada shifokorga murojaat qiling'
            elif urgency_score >= 1:
                level = 'medium'
                description = 'Shifokorga ko\'rsating'
            else:
                level = 'low'
                description = 'Oddiy konsultatsiya'

            return {
                'urgency_level': level,
                'urgency_score': urgency_score,
                'description': description,
                'recommendation': self._get_urgency_recommendation(level)
            }

        except Exception as e:
            logger.error(f"Urgency assessment xatolik: {e}")
            return {
                'urgency_level': 'medium',
                'urgency_score': 1,
                'description': 'Shifokorga ko\'rsating',
                'recommendation': 'Shifokor bilan maslahatlashing'
            }

    def _process_classification_response(self, response_text, original_message, processing_time):
        """AI javobini qayta ishlash"""
        try:
            # JSON javobni tozalash
            cleaned_response = self._clean_json_response(response_text)
            result = json.loads(cleaned_response)

            # Validatsiya
            required_fields = ['specialty', 'confidence', 'explanation']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Yetishmayotgan maydon: {field}")

            # Qo'shimcha ma'lumotlar
            result.update({
                'processing_time': processing_time,
                'model_used': 'gemini-2.0-flash',
                'original_message': original_message,
                'timestamp': time.time(),
                'symptoms_analysis': self.analyze_symptoms(original_message),
                'urgency_assessment': self.assess_urgency([], original_message)
            })

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Classification response parse error: {e}")
            return self._get_fallback_classification(original_message)

    def _clean_json_response(self, response_text):
        """JSON javobni tozalash"""
        import re

        # Markdown kod bloklarini olib tashlash
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)

        # JSON qismini topish
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return response_text.strip()

    def _get_fallback_classification(self, user_message):
        """Fallback classification (AI ishlamasa)"""
        message_lower = user_message.lower()

        # Oddiy kalit so'z tahlili
        if any(word in message_lower for word in ['tish', 'diş', 'tooth']):
            specialty = 'stomatolog'
        elif any(word in message_lower for word in ['yurak', 'qalb', 'heart']):
            specialty = 'kardiolog'
        elif any(word in message_lower for word in ['siydik', 'buyrак', 'kidney']):
            specialty = 'urolog'
        elif any(word in message_lower for word in ['ko\'z', 'eye', 'глаз']):
            specialty = 'oftalmolog'
        elif any(word in message_lower for word in ['quloq', 'ear', 'ухо']):
            specialty = 'lor'
        elif any(word in message_lower for word in ['bola', 'child', 'ребенок']):
            specialty = 'pediatr'
        elif any(word in message_lower for word in ['ayol', 'woman', 'женщина']):
            specialty = 'ginekolog'
        else:
            specialty = 'terapevt'

        return {
            'specialty': specialty,
            'confidence': 0.7,
            'explanation': _('Oddiy kalit so\'z tahlili asosida'),
            'processing_time': 0.1,
            'model_used': 'fallback',
            'original_message': user_message,
            'timestamp': time.time(),
            'symptoms_analysis': self.analyze_symptoms(user_message),
            'urgency_assessment': self.assess_urgency([], user_message)
        }

    def _get_fallback_advice(self, specialty):
        """Fallback advice (AI ishlamasa)"""
        advice_map = {
            'terapevt': _('Umumiy holatni yaxshilash uchun shifokorga murojaat qiling.'),
            'stomatolog': _('Tish gigienasini saqlang va shifokorga ko\'rsating.'),
            'kardiolog': _('Qon bosimingizni nazorat qiling.'),
            'urolog': _('Ko\'p suv iching va shifokorga murojaat qiling.'),
            'oftalmolog': 'Ko\'z gigienasini saqlang va oftalmologga murojaat qiling.',
            'lor': 'Tomog\'ingizni iliq suv bilan chayqang va LOR shifokoriga murojaat qiling.',
            'pediatr': 'Bolangizning holatini kuzatib boring va pediatrga ko\'rsating.',
            'ginekolog': 'Muntazam tekshiruvdan o\'ting va ginekologga murojaat qiling.'
        }

        return {
            'advice': advice_map.get(specialty, _('Shifokor bilan maslahatlashing.')),
            'specialty': specialty,
            'processing_time': 0.1,
            'model_used': 'fallback',
            'timestamp': time.time()
        }

    def _get_urgency_recommendation(self, level):
        """Shoshilinchlik darajasiga qarab tavsiya"""
        recommendations = {
            'urgent': 'Darhol 103 ga qo\'ng\'iroq qiling yoki tez yordam chaqiring',
            'high': 'Bugun yoki ertaga shifokorga murojaat qiling',
            'medium': 'Bir necha kun ichida shifokorga ko\'rsating',
            'low': 'Imkoniyat bo\'lganda shifokor bilan maslahatlashing'
        }
        return recommendations.get(level, 'Shifokor bilan maslahatlashing')

    def get_doctor_recommendations(self, specialty, user_location=None, preferences=None):
        """
        Shifokor tavsiyalarini olish

        Args:
            specialty (str): Mutaxassislik
            user_location (str): Foydalanuvchi joylashuvi
            preferences (dict): Foydalanuvchi tanlovi

        Returns:
            dict: Shifokor tavsiyalari
        """
        try:
            from apps.doctors.models import Doctor

            # Shifokorlarni qidirish
            doctors = Doctor.objects.filter(
                specialty=specialty,
                is_available=True
            ).order_by('-rating', 'consultation_price')

            # Joylashuvga qarab filtrlash
            if user_location:
                doctors = doctors.filter(region__icontains=user_location)

            # Top 5 shifokor
            top_doctors = doctors[:5]

            recommendations = []
            for doctor in top_doctors:
                recommendations.append({
                    'id': doctor.id,
                    'name': doctor.get_full_name(),
                    'specialty': doctor.get_specialty_display(),
                    'experience': doctor.experience,
                    'rating': float(doctor.rating),
                    'price': float(doctor.consultation_price),
                    'workplace': doctor.workplace,
                    'phone': doctor.phone,
                    'is_online': doctor.is_online_consultation,
                    'work_hours': f"{doctor.work_start_time} - {doctor.work_end_time}"
                })

            return {
                'success': True,
                'specialty': specialty,
                'total_found': doctors.count(),
                'recommendations': recommendations,
                'search_location': user_location
            }

        except Exception as e:
            logger.error(f"Doctor recommendations xatolik: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommendations': []
            }

    def validate_medical_input(self, user_input):
        """
        Tibbiy input validatsiyasi

        Args:
            user_input (str): Foydalanuvchi kiritgan ma'lumot

        Returns:
            dict: Validatsiya natijasi
        """
        try:
            # Asosiy validatsiya
            if not user_input or len(user_input.strip()) < 3:
                return {
                    'is_valid': False,
                    'error': 'Iltimos, muammoingizni batafsil yozing',
                    'suggestions': [
                        'Kamida 3 ta harf yozing',
                        'Simptomlaringizni tasvirlab bering',
                        'Qachondan beri azob chekayotganingizni ayting'
                    ]
                }

            # Spam/noto'g'ri ma'lumot tekshirish
            spam_patterns = ['test', '123', 'aaa', 'spam']
            if any(pattern in user_input.lower() for pattern in spam_patterns):
                return {
                    'is_valid': False,
                    'error': 'Iltimos, haqiqiy tibbiy muammoyingizni yozing',
                    'suggestions': [
                        'Haqiqiy simptomlaringizni tasvirlab bering',
                        'Qanday og\'riq yoki noqulaylik bor?',
                        'Muammo qachondan boshlangan?'
                    ]
                }

            # Uzunlik tekshirish
            if len(user_input) > 500:
                return {
                    'is_valid': False,
                    'error': 'Xabar juda uzun. Iltimos, qisqartiring',
                    'suggestions': [
                        'Asosiy simptomlarni yozing',
                        'Eng muhim ma\'lumotlarni qoldiring',
                        '500 belgidan kam yozing'
                    ]
                }

            return {
                'is_valid': True,
                'message': 'Ma\'lumot to\'g\'ri kiritildi',
                'word_count': len(user_input.split()),
                'char_count': len(user_input)
            }

        except Exception as e:
            logger.error(f"Input validation xatolik: {e}")
            return {
                'is_valid': False,
                'error': 'Tekshirishda xatolik yuz berdi'
            }

    def get_health_tips(self, specialty=None, language='uz'):
        """
        Sog'liq maslahatlari

        Args:
            specialty (str): Mutaxassislik (ixtiyoriy)
            language (str): Til

        Returns:
            list: Maslahatlat ro'yxati
        """
        tips_by_specialty = {
            'terapevt': [
                'Kun davomida kamida 8 stakan suv iching',
                'Muntazam sport bilan shug\'ullaning',
                'Yetarli uyqu oling (7-8 soat)',
                'Stressdan saqlaning',
                'Yiliga kamida bir marta tekshiruvdan o\'ting'
            ],
            'stomatolog': [
                'Kuniga 2 marta tish yuvish kerak',
                'Dental floss ishlatishni unutmang',
                'Shakarli ovqatlarni kamroq iste\'mol qiling',
                '6 oyda bir marta stomatologga ko\'rsating',
                'Tish cho\'tkasini 3 oyda bir marta almashtiring'
            ],
            'kardiolog': [
                'Qon bosimingizni muntazam o\'lchang',
                'Tuzli ovqatlarni kamroq iste\'mol qiling',
                'Meva va sabzavot ko\'proq yeng',
                'Chekishni to\'xtating',
                'Stressdan saqlaning'
            ]
        }

        if specialty and specialty in tips_by_specialty:
            return tips_by_specialty[specialty]
        else:
            # Umumiy maslahatlat
            return [
                'Sog\'lom turmush tarzini olib boring',
                'Muntazam ravishda sport bilan shug\'ullaning',
                'Muvozanatli ovqatlaning',
                'Yetarli uyqu oling',
                "Stressdan saqlaning"
                "Muntazam tibbiy tekshiruvdan o'ting"
            ]


# Singlton instance
_gemini_service = None


def get_gemini_service():
    """Gemini servisini olish"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
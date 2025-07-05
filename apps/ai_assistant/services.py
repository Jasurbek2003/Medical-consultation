import google.generativeai as genai
import json
import time
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class GeminiService:
    """Google Gemini AI bilan ishlash uchun service"""

    def __init__(self):
        """Gemini AI'ni sozlash"""
        try:
            if not settings.GOOGLE_API_KEY:
                logger.warning("GOOGLE_API_KEY sozlanmagan")
                self.model = None
                return

            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.generation_config = {
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
            logger.info("Gemini AI muvaffaqiyatli sozlandi")
        except Exception as e:
            logger.error(f"Gemini AI sozlashda xatolik: {e}")
            self.model = None

    def classify_medical_issue(self, user_message, user_context=None, language='uz'):
        """
        Bemorning shikoyatini tahlil qilib, qaysi mutaxassis kerakligini aniqlash

        Args:
            user_message (str): Foydalanuvchi xabari
            user_context (dict): Foydalanuvchi konteksti

        Returns:
            dict: Tahlil natijasi
        """
        try:
            start_time = time.time()

            # Cache tekshirish
            cache_key = f"medical_classification_{hash(user_message)}"
            cached_result = cache.get(cache_key)

            if cached_result:
                logger.info("Cache'dan medical classification olindi")
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
                'total_symptoms': len(detected_symptoms),
                'keywords': keywords
            }

        except Exception as e:
            logger.error(f"Symptom analysis xatolik: {e}")
            return {'detected_symptoms': [], 'total_symptoms': 0, 'keywords': []}

    def assess_urgency(self, symptoms, user_message):
        """
        Shoshilinchlik darajasini baholash

        Args:
            symptoms (list): Aniqlangan simptomlar
            user_message (str): Foydalanuvchi xabari

        Returns:
            dict: Shoshilinchlik bahosi
        """
        try:
            # Shoshilinch kalit so'zlar
            urgent_keywords = [
                'o\'limga yaqin', 'nafas olmayman', 'ko\'krakda keskin og\'riq',
                'hushini yo\'qotish', 'yurak og\'rig\'i', 'qon ketish'
            ]

            # Yuqori prioritet
            high_priority_keywords = [
                'og\'riq', 'harorat', 'bosh og\'rig\'i', 'yo\'tal', 'nezle'
            ]

            text_lower = user_message.lower()
            urgency_score = 0

            # Shoshilinchlik tekshirish
            for keyword in urgent_keywords:
                if keyword in text_lower:
                    urgency_score += 3

            for keyword in high_priority_keywords:
                if keyword in text_lower:
                    urgency_score += 1

            # Darajani aniqlash
            if urgency_score >= 6:
                level = 'emergency'
                description = 'Zudlik bilan tibbiy yordam kerak!'
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
                'model_used': 'gemini-pro',
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
        """Xatolik yuz berganda standart klassifikatsiya"""
        # Oddiy kalit so'z asosida aniqlash
        message_lower = user_message.lower()

        if any(word in message_lower for word in ['tish', 'og\'iz']):
            specialty = 'stomatolog'
            confidence = 0.7
        elif any(word in message_lower for word in ['yurak', 'qon bosimi']):
            specialty = 'kardiolog'
            confidence = 0.7
        elif any(word in message_lower for word in ['siydik', 'buyrak']):
            specialty = 'urolog'
            confidence = 0.7
        elif any(word in message_lower for word in ['ko\'z', 'ko\'rish']):
            specialty = 'oftalmolog'
            confidence = 0.7
        elif any(word in message_lower for word in ['quloq', 'burun', 'tomoq']):
            specialty = 'lor'
            confidence = 0.7
        else:
            specialty = 'terapevt'
            confidence = 0.5

        return {
            'specialty': specialty,
            'confidence': confidence,
            'explanation': f'Kalit so\'zlar asosida {specialty} tavsiya qilinadi',
            'processing_time': 0.1,
            'model_used': 'fallback',
            'is_fallback': True,
            'symptoms_analysis': self.analyze_symptoms(user_message),
            'urgency_assessment': self.assess_urgency([], user_message)
        }

    def _get_fallback_advice(self, specialty):
        """Xatolik yuz berganda standart maslahat"""
        general_advice = {
            'stomatolog': 'Tish gigienasini saqlang va muntazam shifokorga ko\'rsating.',
            'kardiolog': 'Qon bosimingizni nazorat qiling va sog\'lom turmush tarzi olib boring.',
            'urolog': 'Ko\'p suv iching va shifokorga murojaat qiling.',
            'terapevt': 'Umumiy holatni yaxshilash uchun shifokorga murojaat qiling.',
            'ginekolog': 'Muntazam ginekologik ko\'rikdan o\'ting.',
            'pediatr': 'Bolangizni muntazam pediatrga ko\'rsating.',
            'dermatolog': 'Teri gigienasini saqlang va shifokorga murojaat qiling.',
            'nevrolog': 'Stress darajasini kamaytiring va shifokorga ko\'rsating.',
            'oftalmolog': 'Ko\'z gigienasini saqlang va vaqti-vaqti bilan ko\'rikdan o\'ting.',
            'lor': 'Quloq-burun-tomoq gigienasini saqlang.'
        }

        return {
            'advice': general_advice.get(specialty, 'Shifokor bilan maslahatlashing.'),
            'specialty': specialty,
            'processing_time': 0.1,
            'model_used': 'fallback',
            'is_fallback': True
        }

    def _get_urgency_recommendation(self, level):
        """Shoshilinchlik darajasiga qarab tavsiya"""
        recommendations = {
            'emergency': 'Zudlik bilan tez yordam chaqiring (103) yoki shifoxonaga boring!',
            'high': 'Bugun shifokorga ko\'rsating yoki klinikaga murojaat qiling.',
            'medium': 'Yaqin kunlarda shifokor bilan maslahatlashing.',
            'low': 'Vaqt bo\'lganda shifokorga ko\'rsating.'
        }
        return recommendations.get(level, 'Shifokor bilan maslahatlashing.')
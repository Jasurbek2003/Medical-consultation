import requests
import json
import logging
from typing import Dict, List, Optional
from django.core.cache import cache
from django.db import transaction
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranslationConfig:
    """Translation configuration class"""
    api_url: str = "https://websocket.tahrirchi.uz/translate-v2"
    api_key: str = "th_16434f38-c7da-4f3a-8210-3048b155e161"
    model: str = "tilmoch"
    timeout: int = 30
    cache_timeout: int = 3600  # 1 hour cache

    # Language codes mapping
    LANGUAGES = {
        'uzbek_latin': 'uzn_Latn',
        'uzbek_cyrillic': 'uzn_Cyrl',
        'russian': 'rus_Cyrl',
        'english': 'eng_Latn'
    }


class TahrirchiTranslationService:
    """Service for translating content using Tahrirchi API"""

    def __init__(self):
        self.config = TranslationConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.config.api_key,
            'Content-Type': 'application/json'
        })

    @staticmethod
    def _generate_cache_key(text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key for translation"""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"translation:{source_lang}:{target_lang}:{text_hash}"

    def _make_translation_request(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Make actual translation request to Tahrirchi API"""
        try:
            payload = {
                "text": text,
                "target_lang": target_lang,
                "model": self.config.model,
                "source_lang": source_lang
            }

            logger.info(f"Translating: {text[:50]}... from {source_lang} to {target_lang}")

            response = self.session.post(
                self.config.api_url,
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            if 'translated_text' in result:
                translated_text = result['translated_text']
                logger.info(f"Translation successful: {translated_text[:50]}...")
                return translated_text
            else:
                logger.error(f"No translated_text in response: {result}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Translation API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse translation response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during translation: {e}")
            return None

    def translate_text(self, text: str, source_lang: str, target_lang: str, use_cache: bool = True) -> Optional[str]:
        """
        Translate text from source language to target language

        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'uzn_Latn')
            target_lang: Target language code (e.g., 'rus_Cyrl')
            use_cache: Whether to use cache for translation

        Returns:
            Translated text or None if translation failed
        """
        if not text or not text.strip():
            return text

        # Check cache first
        if use_cache:
            cache_key = self._generate_cache_key(text, source_lang, target_lang)
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached translation for: {text[:50]}...")
                return cached_result

        # Make translation request
        translated_text = self._make_translation_request(text, source_lang, target_lang)

        # Cache the result
        if translated_text and use_cache:
            cache_key = self._generate_cache_key(text, source_lang, target_lang)
            cache.set(cache_key, translated_text, self.config.cache_timeout)

        return translated_text

    def translate_to_all_languages(self, text: str, source_lang: str = 'uzn_Latn') -> Dict[str, str]:
        """
        Translate text to all supported languages

        Args:
            text: Text to translate
            source_lang: Source language code

        Returns:
            Dictionary with language codes as keys and translations as values
        """
        translations = {source_lang: text}

        for lang_name, lang_code in self.config.LANGUAGES.items():
            translated = self.translate_text(text, source_lang, lang_code)
            if translated:
                translations[lang_code] = translated
            else:
                logger.warning(f"Failed to translate to {lang_code}: {text[:50]}...")
                translations[lang_code] = text  # Fallback to original text
            # if lang_code != source_lang:  # FIXED: Complete the condition
            #     translated = self.translate_text(text, source_lang, lang_code)
            #     if translated:
            #         translations[lang_code] = translated
            #     else:
            #         logger.warning(f"Failed to translate to {lang_code}: {text[:50]}...")
            #         translations[lang_code] = text  # Fallback to original text

        return translations

    def batch_translate(self, texts: List[str], source_lang: str, target_lang: str) -> List[Optional[str]]:
        """
        Translate multiple texts at once

        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            List of translated texts (same order as input)
        """
        results = []

        for text in texts:
            translated = self.translate_text(text, source_lang, target_lang)
            results.append(translated)

        return results


class DoctorTranslationService:
    """Service for translating doctor-related content"""

    def __init__(self):
        self.translator = TahrirchiTranslationService()

    def translate_doctor_profile(self, doctor, source_lang: str = 'uzn_Latn') -> Dict[str, Dict[str, str]]:
        """
        Translate all relevant fields of a doctor profile

        Args:
            doctor: Doctor model instance
            source_lang: Source language code

        Returns:
            Dictionary with field names and their translations
        """
        # Fields to translate
        translatable_fields = {
            'bio': doctor.bio or '',
            'education': doctor.education or '',
            'achievements': doctor.achievements or '',
            'workplace': doctor.workplace or '',
            'workplace_address': doctor.workplace_address or '',
            'specialty_display': doctor.get_specialty_display() or '',
        }

        # Also get user-related fields
        if doctor.user:
            user_fields = {
                'allergies': doctor.user.allergies or '',
                'chronic_diseases': doctor.user.chronic_diseases or '',
                'current_medications': doctor.user.current_medications or '',
                'address': doctor.user.address or '',  # FIXED: Complete the field
            }
            translatable_fields.update(user_fields)

        # Translate each field to all languages
        translations = {}

        for field_name, text in translatable_fields.items():
            if text and text.strip():
                field_translations = self.translator.translate_to_all_languages(text, source_lang)
                translations[field_name] = field_translations
            else:
                # Empty field - create empty translations
                translations[field_name] = {
                    lang_code: '' for lang_code in self.translator.config.LANGUAGES.values()
                }

        return translations

    @staticmethod
    def save_doctor_translations(doctor, translations: Dict[str, Dict[str, str]]):
        """
        Save translations to doctor's translation model

        Args:
            doctor: Doctor model instance
            translations: Dictionary with field translations
        """
        from apps.doctors.models import DoctorTranslation

        try:
            with transaction.atomic():
                # Get or create translation object
                doctor_translation, created = DoctorTranslation.objects.get_or_create(
                    doctor=doctor,
                    defaults={'translations': translations}
                )

                if not created:
                    # Update existing translations
                    doctor_translation.translations.update(translations)
                    doctor_translation.save()

                logger.info(f"Saved translations for doctor {doctor.id}")
                return doctor_translation

        except Exception as e:
            logger.error(f"Failed to save doctor translations: {e}")
            return None

    @staticmethod
    def get_doctor_translation(doctor, field_name: str, language: str) -> str:
        """
        Get specific field translation for doctor

        Args:
            doctor: Doctor model instance
            field_name: Field name to get translation for
            language: Language code

        Returns:
            Translated text or original text if translation not found
        """
        from apps.doctors.models import DoctorTranslation

        try:
            translation_obj = DoctorTranslation.objects.get(doctor=doctor)
            translations = translation_obj.translations

            if field_name in translations and language in translations[field_name]:
                return translations[field_name][language]

        except DoctorTranslation.DoesNotExist:
            logger.warning(f"No translations found for doctor {doctor.id}")
        except Exception as e:
            logger.error(f"Error getting doctor translation: {e}")

        # Fallback to original field value
        return getattr(doctor, field_name, '') or ''

    def translate_all_doctors(self, batch_size: int = 10):
        """
        Translate all doctors in the database

        Args:
            batch_size: Number of doctors to process at once
        """
        from apps.doctors.models import Doctor

        doctors = Doctor.objects.filter(user__is_approved_by_admin=True)
        total_doctors = doctors.count()

        logger.info(f"Starting translation of {total_doctors} doctors")

        for i in range(0, total_doctors, batch_size):
            batch = doctors[i:i + batch_size]

            for doctor in batch:
                try:
                    logger.info(f"Translating doctor {doctor.id} ({i + 1}/{total_doctors})")

                    # Get translations
                    translations = self.translate_doctor_profile(doctor)

                    # Save translations
                    self.save_doctor_translations(doctor, translations)

                except Exception as e:
                    logger.error(f"Failed to translate doctor {doctor.id}: {e}")
                    continue

        logger.info("Completed translation of all doctors")


class HospitalTranslationService:
    """Service for translating hospital-related content"""

    def __init__(self):
        self.translator = TahrirchiTranslationService()

    def translate_hospital_profile(self, hospital, source_lang: str = 'uzn_Latn') -> Dict[str, Dict[str, str]]:
        """
        Translate all relevant fields of a hospital profile

        Args:
            hospital: Hospital model instance
            source_lang: Source language code

        Returns:
            Dictionary with field names and their translations
        """
        # Fields to translate
        translatable_fields = {
            'name': hospital.name or '',
            'address': hospital.address or '',
            'description': hospital.description or '',
        }

        # Translate each field to all languages
        translations = {}

        for field_name, text in translatable_fields.items():
            if text and text.strip():
                field_translations = self.translator.translate_to_all_languages(text, source_lang)
                translations[field_name] = field_translations
            else:
                # Empty field - create empty translations
                translations[field_name] = {
                    lang_code: '' for lang_code in self.translator.config.LANGUAGES.values()
                }

        return translations

    @staticmethod
    def save_hospital_translations(hospital, translations: Dict[str, Dict[str, str]]):
        """
        Save translations to hospital's translation model

        Args:
            hospital: Hospital model instance
            translations: Dictionary with field translations
        """
        from apps.hospitals.models import HospitalTranslation

        try:
            with transaction.atomic():
                # Get or create translation object
                hospital_translation, created = HospitalTranslation.objects.get_or_create(
                    hospital=hospital,
                    defaults={'translations': translations}
                )

                if not created:
                    # Update existing translations
                    hospital_translation.translations.update(translations)
                    hospital_translation.save()

                logger.info(f"Saved translations for hospital {hospital.id}")
                return hospital_translation

        except Exception as e:
            logger.error(f"Failed to save hospital translations: {e}")
            return None

    @staticmethod
    def get_hospital_translation(hospital, field_name: str, language: str) -> str:
        """
        Get specific field translation for hospital

        Args:
            hospital: Hospital model instance
            field_name: Field name to get translation for
            language: Language code
        Returns:
            Translated text or original text if translation not found
        """

        from apps.hospitals.models import HospitalTranslation

        try:
            translation_obj = HospitalTranslation.objects.get(hospital=hospital)
            translations = translation_obj.translations
            if field_name in translations and language in translations[field_name]:
                return translations[field_name][language]
        except HospitalTranslation.DoesNotExist:
            logger.warning(f"No translations found for hospital {hospital.id}")
        except Exception as e:
            logger.error(f"Error getting hospital translation: {e}")
        # Fallback to original field value
        return getattr(hospital, field_name, '') or ''


# Usage example
def translate_doctor_example():
    """Example of how to use the translation service"""

    # Initialize service
    translation_service = DoctorTranslationService()

    # Get a doctor
    from apps.doctors.models import Doctor
    doctor = Doctor.objects.first()

    if doctor:
        # Translate doctor profile
        translations = translation_service.translate_doctor_profile(doctor)

        # Save translations
        translation_service.save_doctor_translations(doctor, translations)

        # Get specific translation
        bio_russian = translation_service.get_doctor_translation(
            doctor, 'bio', 'rus_Cyrl'
        )

        print(f"Russian bio: {bio_russian}")
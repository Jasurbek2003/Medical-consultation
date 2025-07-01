import re
import string
from typing import List


def clean_json_response(response_text: str) -> str:
    """
    AI javobini JSON formatiga keltirib tozalash
    """
    try:
        # Markdown kod bloklarini olib tashlash
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)

        # Ortiqcha bo'shliqlarni olib tashlash
        response_text = response_text.strip()

        # JSON qismini topish
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return response_text

    except Exception:
        return response_text


def extract_keywords(text: str) -> List[str]:
    """
    Matndan kalit so'zlarni ajratib olish
    """
    try:
        # Tinish belgilarini olib tashlash
        translator = str.maketrans('', '', string.punctuation)
        clean_text = text.translate(translator)

        # So'zlarni ajratish
        words = clean_text.lower().split()

        # Qisqa so'zlarni olib tashlash
        keywords = [word for word in words if len(word) > 2]

        # Takrorlanuvchi so'zlarni olib tashlash
        unique_keywords = list(set(keywords))

        return unique_keywords[:20]  # Maksimal 20 ta kalit so'z

    except Exception:
        return []


def sanitize_user_input(user_input: str) -> str:
    """
    Foydalanuvchi kiritgan ma'lumotni tozalash
    """
    try:
        # HTML teglarini olib tashlash
        clean_input = re.sub(r'<[^>]+>', '', user_input)

        # Ortiqcha bo'shliqlarni olib tashlash
        clean_input = re.sub(r'\s+', ' ', clean_input).strip()

        # Maksimal uzunlikni cheklash
        if len(clean_input) > 1000:
            clean_input = clean_input[:1000] + "..."

        return clean_input

    except Exception:
        return user_input[:500]  # Xatolik bo'lsa ham biror narsa qaytarish
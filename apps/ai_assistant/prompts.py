# AI uchun promptlar va kalit so'zlar

CLASSIFICATION_PROMPT = """
Siz tibbiy konsultatsiya tizimining AI yordamchisisiz. Bemorning shikoyatiga qarab, qaysi mutaxassis shifokor kerak ekanligini aniq aniqlashingiz kerak.

MAVJUD MUTAXASSISLAR:
- terapevt: umumiy kasalliklar, sovuq-shumuq, bosh og'riq, harorat, umumiy holsizlik
- stomatolog: tish og'riq, tish go'shti kasalliklari, og'iz bo'shlig'i muammolari
- kardiolog: yurak kasalliklari, qon bosimi, ko'krak og'rig'i, yurak urishi
- urolog: siydik yo'li kasalliklari, buyrak muammolari, erkaklar kasalliklari
- ginekolog: ayollar kasalliklari, homiladorlik, reproduktiv salomatlik
- pediatr: 18 yoshgacha bolalar kasalliklari
- dermatolog: teri kasalliklari, allergiya, eczema, psoriaz
- nevrolog: asab tizimi kasalliklari, migren, epilepsiya
- oftalmolog: ko'z kasalliklari, ko'rish muammolari
- lor: quloq-burun-tomoq kasalliklari
- ortoped: suyak va bo'g'im kasalliklari, jarohatlar
- psixiatr: ruhiy salomatlik, depressiya, tashvish
- endokrinolog: gormonlar, diabet, qalqonsimon bez
- gastroenterolog: oshqozon-ichak kasalliklari, jigar muammolari
- pulmonolog: o'pka kasalliklari, nafas olish muammolari

BEMORNING SHIKOYATI: "{user_message}"

FOYDALANUVCHI KONTEKSTI: {user_context}

QOIDALAR:
1. Faqat yuqorida ko'rsatilgan mutaxassislar ichidan tanlang
2. Ishonch darajasi 0.0 dan 1.0 gacha bo'lishi kerak
3. Tushuntirish aniq va qisqa bo'lsin
4. Agar aniq bo'lmasa, terapevtni tanlang

JAVOBNI FAQAT JSON FORMATIDA BERING:
{{
    "specialty": "mutaxassis_nomi",
    "confidence": 0.95,
    "explanation": "Nima uchun bu mutaxassisni tanlaganingizni tushuntiring",
    "detected_symptoms": ["simptom1", "simptom2"],
    "urgency_level": "normal"
}}
"""

ADVICE_PROMPT = """
Siz {specialty} bo'yicha umumiy maslahat beruvchi AI yordamchisisiz. 
Bemorga foydali, xavfsiz va umumiy ma'lumot bering, lekin diagnostika qo'ymang.

BEMORNING MUAMMOSI: "{user_message}"
ANIQLANGAN SIMPTOMLAR: {symptoms}

QOIDALAR:
1. Faqat umumiy maslahat bering, aniq diagnostika qo'ymang
2. Shifokorga murojaat qilish muhimligini ta'kidlang
3. Xavfsiz va foydali maslahatlar bering
4. O'zbek tilida, sodda va tushunarli tilda yozing
5. Pozitiv ohangda javob bering

JAVOBINGIZDA QO'SHING:
- Umumiy maslahat
- Oldini olish usullari
- Qachon shifokorga murojaat qilish kerakligi
- Nimalarga e'tibor berish kerak

Javobni o'zbek tilida, do'stona ohangda bering.
"""

# Simptomlar bo'yicha kalit so'zlar
SYMPTOM_KEYWORDS = {
    'terapevt': [
        'harorat', 'sovuq', 'gripp', 'bosh og\'rig\'i', 'holsizlik', 'charchoq',
        'umumiy og\'riq', 'shumuq', 'yo\'tal', 'burun oqishi', 'tomoq og\'rig\'i'
    ],

    'stomatolog': [
        'tish og\'rig\'i', 'tish', 'og\'iz', 'tish go\'shti', 'og\'iz hidsi',
        'tish parchalanishi', 'og\'iz yaras i', 'tish olib tashlash'
    ],

    'kardiolog': [
        'yurak og\'rig\'i', 'ko\'krak og\'rig\'i', 'qon bosimi', 'yurak urishi',
        'nafas qisilishi', 'chap qo\'l og\'rig\'i', 'yengillik', 'charchoq'
    ],

    'urolog': [
        'siydik', 'buyrak', 'siydik yo\'li', 'siydik qilishda og\'riq',
        'tez-tez siydik qilish', 'siydik ushlab turolmaslik', 'erkaklik kasalligi'
    ],

    'ginekolog': [
        'ayollik', 'homiladorlik', 'hayz', 'qin', 'ko\'krak', 'tuxumdon',
        'bachadon', 'ayol kasalligi', 'kontratseptiv'
    ],

    'pediatr': [
        'bola', 'chaqaloq', 'o\'smir', 'bolaning kasalligi', 'vaksinatsiya',
        'o\'sish', 'rivojlanish', 'maktab'
    ],

    'dermatolog': [
        'teri', 'qichish', 'to\'la', 'allergiya', 'ekzema', 'psoriaz',
        'teri dog\'i', 'teri kasalligi', 'soch to\'kilishi'
    ],

    'nevrolog': [
        'bosh og\'rig\'i', 'migren', 'epilepsiya', 'asab', 'titroq',
        'koordinatsiya', 'xotira', 'uyqu', 'stress'
    ],

    'oftalmolog': [
        'ko\'z', 'ko\'rish', 'ko\'z og\'rig\'i', 'ko\'z yoshlanishi',
        'ko\'rish buzilishi', 'ko\'z qichishi', 'binokular'
    ],

    'lor': [
        'quloq', 'burun', 'tomoq', 'eshitish', 'burun band bo\'lishi',
        'quloq og\'rig\'i', 'tomoq og\'rig\'i', 'ovoz'
    ],

    'ortoped': [
        'suyak', 'bo\'g\'im', 'jarohati', 'oyoq', 'qo\'l', 'bel',
        'bo\'g\'im og\'rig\'i', 'suyak sinishi', 'sport jarohati'
    ],

    'psixiatr': [
        'depressiya', 'tashvish', 'stress', 'ruhiy holat', 'uyqu buzilishi',
        'ishtaha yo\'qligi', 'kayfiyat', 'xotira', 'diqqat'
    ],

    'endokrinolog': [
        'diabet', 'qand', 'qalqonsimon bez', 'gormon', 'vazn',
        'metabolizm', 'insulin', 'tez charchaish'
    ],

    'gastroenterolog': [
        'oshqozon', 'ichak', 'jigar', 'oshqozon og\'rig\'i', 'diareya',
        'ich ketish', 'qayt qilish', 'ovqat hazm qilish'
    ],

    'pulmonolog': [
        'o\'pka', 'nafas', 'yo\'tal', 'nafas qisilishi', 'ko\'krak',
        'bronxit', 'astma', 'o\'pka kasalligi'
    ]
}

# Shoshilinch holatlar uchun kalit so'zlar
EMERGENCY_KEYWORDS = [
    'o\'limga yaqin', 'hush yo\'qotish', 'nafas olmayapman', 'yurak to\'xtash',
    'ko\'p qon ketish', 'keskin og\'riq', 'zeher', 'kuyish', 'jarohati'
]

# Yuqori prioritet kalit so'zlar
HIGH_PRIORITY_KEYWORDS = [
    'keskin og\'riq', 'yuqori harorat', 'qusish', 'bosh aylanishi',
    'ko\'krak og\'rig\'i', 'nafas qisilishi'
]

# Umumiy maslahatlar
GENERAL_ADVICE = {
    'terapevt': """
    **Umumiy maslahat:**
    - Ko'p suyuqlik iching (suv, issiq choy)
    - Yetarli dam oling va uyqu soatingizni saqlang
    - Vitamin C ga boy ovqatlar iste'mol qiling
    - Harorat ko'tarilsa, shifokorga murojaat qiling

    **Ehtiyot choralar:**
    - Boshqalarga yuqmasligi uchun niqob kiyib yuring
    - Qo'llaringizni tez-tez yuving
    - Issiq ovqat va ichimliklar qabul qiling

    **Shifokorga murojaat qiling, agar:**
    - Harorat 38.5°C dan yuqori ko'tarilsa
    - Kasallik 7 kundan ko'p davom etsa
    - Nafas olishda qiyinchilik paydo bo'lsa
    """,

    'stomatolog': """
    **Umumiy maslahat:**
    - Tishlaringizni kuniga 2 marta tozalang
    - Tish ipi ishlatib, tish orasini tozalang
    - Shakarli ovqatlarni kamroq iste'mol qiling
    - Muntazam stomatologga ko'rsating

    **Og'riq kamaytirish uchun:**
    - Issiq tuzli suv bilan chayqash
    - Sovuq kompres qo'ying
    - Og'riq qoldiruvchi dorilar (dozaga rioya qiling)

    **Tezkor stomatologga murojaat qiling, agar:**
    - Keskin tish og'rig'i bo'lsa
    - Yuz shishsa
    - Yuqori harorat ko'tarilsa
    """,

    'kardiolog': """
    **Yurak salomatlik uchun:**
    - Sog'lom ovqatlanish (kam tuz, kam yog')
    - Muntazam jismoniy mashqlar
    - Stressni kamaytiring
    - Chekishni to'xtating

    **Qon bosimini nazorat qiling:**
    - Kundalik qon bosimni o'lchang
    - Vazningizni nazorat qiling
    - Ko'p suv iching

    **Zudlik bilan shifokorga murojaat qiling, agar:**
    - Ko'krak qismida keskin og'riq
    - Nafas qisilishi
    - Chap qo'lga og'riq tarqalsa
    - Bosh aylanishi va hushni yo'qotish
    """,

    'urolog': """
    **Siydik yo'li salomatligi uchun:**
    - Kuniga 2-3 litr suv iching
    - Shaxsiy gigienani saqlang
    - Vitamin C qabul qiling
    - Kechiktirmay siydik qiling

    **Oldini olish:**
    - Tog' uzumidan foydalaning
    - Kofeinni kamroq iste'mol qiling
    - Kasal paytida ko'p dam oling

    **Shifokorga murojaat qiling, agar:**
    - Siydikda qon bo'lsa
    - Yuqori harorat ko'tarilsa
    - Keskin og'riq bo'lsa
    """,

    'ginekolog': """
    **Ayol salomatligi uchun:**
    - Muntazam ginekolog ko'rigi
    - Shaxsiy gigienani saqlang
    - Sog'lom ovqatlanish
    - Stress darajasini kamaytiring

    **E'tibor bering:**
    - Hayz tsiklini kuzatib boring
    - G'ayrioddiy belgilarni e'tiborga oling
    - O'z-o'zini tekshirishni o'rganing

    **Shifokorga murojaat qiling, agar:**
    - G'ayrioddiy qon ketish
    - Keskin og'riq
    - Harorat ko'tarilish
    """,

    'dermatolog': """
    **Teri salomatligi uchun:**
    - Terini namlantiring
    - Quyosh nuridan himoyalaning
    - Yumshoq terini parvarish vositalarini ishlating
    - Allergiya qo'zg'atuvchi moddalardan saqlaning

    **Parvarish qoidalari:**
    - Kundalik teri gigienasi
    - Tabiiy mahsulotlarni afzal ko'ring
    - Stress darajasini kamaytiring

    **Shifokorga murojaat qiling, agar:**
    - Yangi dog'lar paydo bo'lsa
    - Qichish kuchaysa
    - Teri rangi o'zgarsa
    """
}

# Tibbiy tanlov algoritmi uchun og'irlik koeffitsientlari
SPECIALTY_WEIGHTS = {
    'terapevt': {
        'keywords': ['harorat', 'sovuq', 'gripp', 'holsizlik'],
        'weight': 1.0,
        'default_confidence': 0.6
    },
    'stomatolog': {
        'keywords': ['tish', 'og\'iz', 'tish go\'shti'],
        'weight': 2.0,  # Aniq belgilar
        'default_confidence': 0.8
    },
    'kardiolog': {
        'keywords': ['yurak', 'ko\'krak og\'rig\'i', 'qon bosimi'],
        'weight': 1.8,
        'default_confidence': 0.7
    },
    'urolog': {
        'keywords': ['siydik', 'buyrak'],
        'weight': 1.9,
        'default_confidence': 0.8
    },
    'ginekolog': {
        'keywords': ['ayollik', 'homiladorlik', 'hayz'],
        'weight': 1.9,
        'default_confidence': 0.8
    }
}

# Chat javob shablonlari
CHAT_RESPONSE_TEMPLATES = {
    'greeting': """
    Salom! Men sizning tibbiy yordamchingizman. 

    Sizning salomatligingiz haqida qaysi masala bor? Quyidagilarni batafsil aytib bering:
    - Qanday belgilar bor?
    - Qachondan beri sezayapsiz?
    - Qaysi joyda og'riq bor?

    Men sizga mos shifokorni topishga yordam beraman! 🏥
    """,

    'classification_result': """
    Sizning shikoyatingizni tahlil qildim.

    **Tavsiya etilgan mutaxassis:** {specialty}
    **Ishonch darajasi:** {confidence}%
    **Sabab:** {explanation}

    Quyida shu sohada eng yaxshi shifokorlar ro'yxati:
    """,

    'no_classification': """
    Sizning muammoingizni aniq tushunish uchun qo'shimcha ma'lumot kerak.

    Iltimos, quyidagilarni batafsil aytib bering:
    - Aniq qaysi belgilar bor?
    - Qancha vaqtdan beri?
    - Og'riq darajasi qanday (1-10)?

    Bu ma'lumotlar asosida sizga eng mos shifokorni tavsiya qilaman.
    """,

    'emergency_warning': """
    ⚠️ **DIQQAT: Bu shoshilinch holat bo'lishi mumkin!**

    Sizning belgilaringiz jiddiy tibbiy yordam talab qilishi mumkin.

    **Zudlik bilan:**
    - Eng yaqin shifoxonaga boring
    - Tez yordam chaqiring: 103
    - Yoki shoshilinch tibbiy yordam olish uchun murojaat qiling

    Vaqtni yo'qotmang! 🚨
    """,

    'general_advice': """
    **Umumiy maslahatlar:**
    {advice}

    **Muhim eslatma:** Bu faqat umumiy ma'lumot. Aniq tashxis va davolash uchun albatta shifokor bilan maslahatlashing.
    """,

    'doctor_recommendation': """
    **Sizga mos shifokorlar:**

    {doctors_list}

    **Shifokor tanlashda e'tiborga oling:**
    - Tajriba va malaka
    - Joylashuv va qulaylik
    - Narx va to'lov imkoniyatlari
    - Boshqa bemorlar sharhlari

    Shifokor bilan bog'lanish uchun telefon qiling yoki online uchrashuvga yoziling.
    """,

    'feedback_request': """
    Sizga yordam bera olganimdan xursandman! 

    Agar xohlasangiz, fikr-mulohazangizni qoldiring:
    - Tavsiyalar foydali bo'ldimi?
    - Shifokor bilan bog'lana oldingizmi?
    - Tizimni yaxshilash uchun takliflaringiz?

    Salomatligingiz yaxshi bo'lsin! 💚
    """
}

# Xatolik xabarlari
ERROR_MESSAGES = {
    'ai_unavailable': """
    Uzr, AI xizmati hozir mavjud emas. 

    Shu paytda quyidagi shifokorlarni ko'rishingiz mumkin:
    - Terapevt - umumiy masalalar uchun
    - Shoshilinch yordam - 103

    Keyinroq qayta urinib ko'ring.
    """,

    'invalid_input': """
    Iltimos, o'z muammoingizni aniqroq tasvirlab bering.

    Masalan:
    - "Ikki kundan beri boshim og'riyapti"
    - "Tishim juda og'riyapti"
    - "Qon bosimim yuqori"

    Bu ma'lumot asosida sizga yordam beraman.
    """,

    'system_error': """
    Texnik xatolik yuz berdi. 

    Iltimos:
    - Sahifani yangilab ko'ring
    - Qayta urinib ko'ring
    - Yoki to'g'ridan-to'g'ri shifokorga murojaat qiling

    Noqulaylik uchun uzr so'raymiz.
    """
}

# Validatsiya qoidalari
VALIDATION_RULES = {
    'min_message_length': 5,
    'max_message_length': 1000,
    'required_keywords_count': 1,
    'min_confidence_threshold': 0.3,
    'max_response_time': 10.0  # soniya
}

# Tizim sozlamalari
SYSTEM_CONFIG = {
    'default_specialty': 'terapevt',
    'fallback_confidence': 0.5,
    'cache_duration': 300,  # 5 daqiqa
    'max_retries': 3,
    'response_timeout': 10.0
}
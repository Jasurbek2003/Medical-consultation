# AI uchun promptlar va kalit so'zlar

CLASSIFICATION_PROMPT_UZ = """
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

QOIDALAR:
1. Ishonch darajasi 0.0 dan 1.0 gacha bo'lishi kerak
2. Tushuntirish aniq va qisqa bo'lsin
3. Agar aniq bo'lmasa, Qo'shimcha ma'lumot so'rang

JAVOBNI FAQAT JSON FORMATIDA BERING:
{{
    "specialty": "mutaxassis_nomi",
    "confidence": 0.95,
    "explanation": "Nima uchun bu mutaxassisni tanlaganingizni tushuntiring",
}}
"""

CLASSIFICATION_PROMPT_RU = """
Вы AI-помощник системы медицинских консультаций. Основываясь на жалобах пациента, вам нужно точно определить, какой врач-специалист требуется.

ДОСТУПНЫЕ СПЕЦИАЛИСТЫ:
- terapevt: общие заболевания, простуда, головная боль, температура
- stomatolog: зубная боль, заболевания десен, проблемы полости рта
- kardiolog: болезни сердца, артериальное давление, боль в груди
- urolog: заболевания мочевыводящих путей, проблемы с почками
- ginekolog: женские болезни, беременность
- pediatr: детские болезни
- dermatolog: кожные заболевания, аллергия
- nevrolog: нервная система, мигрень, головная боль
- oftalmolog: глазные болезни
- lor: болезни уха-горла-носа

ЖАЛОБА ПАЦИЕНТА: "{user_message}"

ДАЙТЕ ОТВЕТ ТОЛЬКО В JSON ФОРМАТЕ:
{{
    "specialty": "название_специалиста",
    "confidence": 0.95,
    "explanation": "Объясните, почему выбрали этого специалиста"
}}
"""

CLASSIFICATION_PROMPT_EN = """
You are an AI assistant for a medical consultation system. Based on the patient's complaints, you need to accurately determine which specialist doctor is required.

AVAILABLE SPECIALISTS:
- terapevt: general diseases, cold, headache, fever
- stomatolog: dental pain, gum diseases, oral cavity problems
- kardiolog: heart diseases, blood pressure, chest pain
- urolog: urinary tract diseases, kidney problems
- ginekolog: women's diseases, pregnancy
- pediatr: children's diseases
- dermatolog: skin diseases, allergies
- nevrolog: nervous system, migraine, headache
- oftalmolog: eye diseases
- lor: ear-nose-throat diseases

PATIENT'S COMPLAINT: "{user_message}"

PROVIDE ANSWER ONLY IN JSON FORMAT:
{{
    "specialty": "specialist_name",
    "confidence": 0.95,
    "explanation": "Explain why you chose this specialist"
}}
"""


CLASSIFICATION_PROMPTS = {
    'uz': CLASSIFICATION_PROMPT_UZ,
    'ru': CLASSIFICATION_PROMPT_RU,
    'en': CLASSIFICATION_PROMPT_EN,
}

ADVICE_PROMPT_UZ = """
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

ADVICE_PROMPT_RU = """
Вы AI-помощник по общим медицинским советам для {specialty}.
На основе жалоб пациента предоставьте полезную, безопасную и общую информацию, но не ставьте диагноз.
ЖАЛОБА ПАЦИЕНТА: "{user_message}"
АНАЛИЗИРОВАННЫЕ СИМПТОМЫ: {symptoms}
ПРАВИЛА:
1. Дайте только общие советы, не ставьте диагноз
2. Подчеркните важность обращения к врачу
3. Дайте безопасные и полезные советы
4. Пишите на русском языке, простым и понятным языком
5. Используйте позитивный тон

В ВАШЕМ ОТВЕТЕ ВКЛЮЧИТЕ:
- Общие советы
- Методы профилактики
- Когда нужно обратиться к врачу
- На что обратить внимание
Ответьте на русском языке, дружелюбным тоном.
"""

ADVICE_PROMPT_EN = """
You are an AI assistant providing general medical advice for {specialty}.
Based on the patient's complaints, provide useful, safe, and general information, but do not make a diagnosis.
PATIENT'S COMPLAINT: "{user_message}"
ANALYZED SYMPTOMS: {symptoms}
RULES:
1. Give only general advice, do not make a diagnosis
2. Emphasize the importance of consulting a doctor
3. Provide safe and useful advice
4. Write in English, using simple and clear language
5. Use a positive tone
IN YOUR RESPONSE INCLUDE:
- General advice
- Prevention methods
- When to consult a doctor
- What to pay attention to
Respond in English, in a friendly tone.
"""
ADVICE_PROMPTS = {
    'uz': ADVICE_PROMPT_UZ,
    'ru': ADVICE_PROMPT_RU,
    'en': ADVICE_PROMPT_EN,
}

# Simptomlar bo'yicha kalit so'zlar
SYMPTOM_KEYWORDS_UZ = {
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

SYMPTOM_KEYWORDS_RU = {
    'terapevt': [
        'температура', 'простуда', 'грипп', 'головная боль', 'усталость',
        'общая боль', 'насморк', 'кашель', 'боль в горле'
    ],
    'stomatolog': [
        'зубная боль', 'зубы', 'десна', 'проблемы с зубами', 'запах изо рта',
        'кариес', 'язвы во рту', 'удаление зуба'
    ],
    'kardiolog': [
        'боль в сердце', 'боль в груди', 'артериальное давление', 'учащенное сердцебиение',
        'затрудненное дыхание', 'боль в левой руке', 'слабость', 'усталость'
    ],
    'urolog': [
        'моча', 'почки', 'мочевыводящие пути', 'боль при мочеиспускании',
        'частое мочеиспускание', 'недержание мочи', 'мужские заболевания'
    ],
    'ginekolog': [
        'женские болезни', 'беременность', 'менструация', 'вагина', 'грудь',
        'яичники', 'матка', 'гинекологические заболевания', 'контрацепция'
    ],
    'pediatr': [
        'ребенок', 'младенец', 'подросток', 'детские болезни', 'вакцинация',
        'рост', 'развитие', 'школа'
    ],
    'dermatolog': [
        'кожа', 'зуд', 'сыпь', 'аллергия', 'экзема', 'псориаз',
        'кожные пятна', 'кожные заболевания', 'выпадение волос'
    ],
    'nevrolog': [
        'головная боль', 'мигрень', 'эпилепсия', 'нервная система', 'тремор',
        'координация', 'память', 'сон', 'стресс'
    ],
    'oftalmolog': [
        'глаза', 'зрение', 'боль в глазах', 'слезотечение',
        'нарушение зрения', 'зуд в глазах', 'бинокулярное зрение'
    ],
    'lor': [
        'ухо', 'нос', 'горло', 'слух', 'заложенность носа',
        'боль в ухе', 'боль в горле', 'голос'
    ],
    'ortoped': [
        'кость', 'сустав', 'травма', 'нога', 'рука', 'спина',
        'боль в суставе', 'перелом кости', 'спортивная травма'
    ],
    'psixiatr': [
        'депрессия', 'тревога', 'стресс', 'психическое состояние', 'бессонница',
        'потеря аппетита', 'настроение', 'память', 'внимание'
    ],
    'endokrinolog': [
        'диабет', 'сахар', 'щитовидная железа', 'гормоны', 'вес',
        'метаболизм', 'инсулин', 'ускоренный обмен веществ'
    ],
    'gastroenterolog': [
        'желудок', 'кишечник', 'печень', 'боль в желудке', 'диарея',
        'расстройство кишечника', 'рвота', 'пищеварение'
    ],
    'pulmonolog': [
        'легкие', 'дыхание', 'кашель', 'затрудненное дыхание', 'грудная клетка',
        'бронхит', 'астма', 'болезни легких'
    ]
}

SYMPTOM_KEYWORDS_EN = {
    'terapevt': [
        'temperature', 'cold', 'flu', 'headache', 'fatigue',
        'general pain', 'runny nose', 'cough', 'sore throat'
    ],
    'stomatolog': [
        'toothache', 'teeth', 'gums', 'dental problems', 'bad breath',
        'cavity', 'mouth sores', 'tooth extraction'
    ],
    'kardiolog': [
        'heart pain', 'chest pain', 'blood pressure', 'rapid heartbeat',
        'shortness of breath', 'left arm pain', 'weakness', 'fatigue'
    ],
    'urolog': [
        'urine', 'kidneys', 'urinary tract', 'painful urination',
        'frequent urination', 'incontinence urination',
    ],
    'ginekolog': [
        'women\'s diseases', 'pregnancy', 'menstruation',
        'vagina', 'breast', 'ovaries', 'uterus',  'gynecological disease', 'contraception'
    ],
    'pediatr': [
        'child', 'infant', 'teenager', 'child illness', 'vaccination',
        'growth', 'development', 'school'
    ],
    'dermatolog': [
        'skin', 'itching', 'rash', 'allergy', 'eczema', 'psoriasis',
        'skin spots', 'skin disease', 'hair loss'
    ],
    'nevrolog': [
        'headache', 'migraine', 'epilepsy', 'nerves', 'tremor',
        'coordination', 'memory', 'sleep', 'stress'
    ],
    'oftalmolog': [
        'eye', 'vision', 'eye pain', 'tearing',
        'vision disorder', 'itchy eyes', 'binocular'
    ],
    'lor': [
        'ear', 'nose', 'throat', 'hearing', 'nasal congestion',
        'ear pain', 'sore throat', 'voice'
    ],
    'ortoped': [
        'bone', 'joint', 'injury', 'leg', 'arm', 'back',
        'joint pain', 'bone fracture', 'sports injury'
    ],
    'psixiatr': [
        'depression', 'anxiety', 'stress', 'mental state', 'insomnia',
        'loss of appetite', 'mood', 'memory', 'attention'
    ],
    'endokrinolog': [
        'diabetes', 'sugar', 'thyroid', 'hormones', 'weight',
        'metabolism', 'insulin', 'fast fatigue'
    ],
    'gastroenterolog': [
        'stomach', 'intestine', 'liver', 'stomach pain', 'diarrhea',
        'intestinal disorder', 'vomiting', 'digestion'
    ],
    'pulmonolog': [
        'lungs', 'breathing', 'cough', 'shortness of breath', 'chest',
        'bronchitis', 'asthma', 'lung disease'
    ]
}
SYMPTOM_KEYWORDS = {
    'uz': SYMPTOM_KEYWORDS_UZ,
    'ru': SYMPTOM_KEYWORDS_RU,
    'en': SYMPTOM_KEYWORDS_EN,
}



# Shoshilinch holatlar uchun kalit so'zlar
EMERGENCY_KEYWORDS_UZ = [
    'o\'limga yaqin', 'hush yo\'qotish', 'nafas olmayapman', 'yurak to\'xtash',
    'ko\'p qon ketish', 'keskin og\'riq', 'zeher', 'kuyish', 'jarohati'
]

EMERGENCY_KEYWORDS_RU = [
    'при смерти', 'потеря сознания', 'не могу дышать', 'остановка сердца',
    'кровотечение', 'острая боль', 'отравление', 'ожог', 'травма'
]

EMERGENCY_KEYWORDS_EN = [
    'near death', 'unconscious', 'can\'t breathe', 'heart attack',
    'bleeding', 'severe pain', 'poisoning', 'burn', 'injury'
]

EMERGENCY_KEYWORDS = {
    'uz': EMERGENCY_KEYWORDS_UZ,
    'ru': EMERGENCY_KEYWORDS_RU,
    'en': EMERGENCY_KEYWORDS_EN,
}


# Yuqori prioritet kalit so'zlar
HIGH_PRIORITY_KEYWORDS_UZ = [
    "keskin og'riq", 'yuqori harorat', 'qusish', 'bosh aylanishi',
    "ko'krak og'rig'i", 'nafas qisilishi'
]

HIGH_PRIORITY_KEYWORDS_RU = [
    "резкая боль",
    "высокая температура",
    "рвота",
    "головокружение",
    "боль в груди",
    "затрудненное дыхание"
]

HIGH_PRIORITY_KEYWORDS_EN = [
    "sharp pain",
    "high fever",
    "vomiting",
    "dizziness",
    "chest pain",
    "shortness of breath"
]


HIGH_PRIORITY_KEYWORDS = {
    'uz': HIGH_PRIORITY_KEYWORDS_UZ,
    'ru': HIGH_PRIORITY_KEYWORDS_RU,
    'en': HIGH_PRIORITY_KEYWORDS_EN,
}

# Umumiy maslahatlar
GENERAL_ADVICE_UZ = {
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

GENERAL_ADVICE_RU = {
    'terapevt': """
    **Общие советы:**
    - Пейте больше жидкости (вода, теплый чай)
    - Отдыхайте и соблюдайте режим сна
    - Употребляйте продукты, богатые витамином C
    - При повышении температуры обратитесь к врачу

    **Меры предосторожности:**
    - Носите маску, чтобы не заразить других
    - Чаще мойте руки
    - Употребляйте горячие блюда и напитки

    **Обратитесь к врачу, если:**
    - Температура превышает 38.5°C
    - Болезнь длится более 7 дней
    - Затруднено дыхание
    """,

    'stomatolog': """
    **Общие советы:**
    - Чистите зубы 2 раза в день
    - Используйте зубную нить для межзубных промежутков
    - Ограничьте потребление сладостей
    - Регулярно посещайте стоматолога

    **Для уменьшения боли:**
    - Полоскание рта теплой соленой водой
    - Приложите холодный компресс
    - Принимайте обезболивающие (соблюдая дозировку)

    **Срочно обратитесь к стоматологу, если:**
    - Острая зубная боль
    - Опухание лица
    - Повышенная температура
    """,

    'kardiolog': """
    **Для здоровья сердца:**
    - Правильное питание (меньше соли и жира)
    - Регулярные физические упражнения
    - Снижение стресса
    - Отказ от курения

    **Контроль давления:**
    - Измеряйте давление ежедневно
    - Контролируйте вес
    - Пейте достаточно воды

    **Срочно обратитесь к врачу, если:**
    - Острая боль в груди
    - Затрудненное дыхание
    - Боль отдает в левую руку
    - Головокружение или потеря сознания
    """,

    'urolog': """
    **Для здоровья мочевых путей:**
    - Пейте 2–3 литра воды в день
    - Соблюдайте личную гигиену
    - Принимайте витамин C
    - Не задерживайте мочеиспускание

    **Профилактика:**
    - Употребляйте клюкву
    - Ограничьте кофеин
    - Больше отдыхайте при недомогании

    **Обратитесь к врачу, если:**
    - Кровь в моче
    - Повышенная температура
    - Острая боль
    """,

    'ginekolog': """
    **Для женского здоровья:**
    - Регулярные осмотры у гинеколога
    - Соблюдение личной гигиены
    - Здоровое питание
    - Снижение уровня стресса

    **Обратите внимание:**
    - Следите за менструальным циклом
    - Не игнорируйте необычные симптомы
    - Проводите самообследование

    **Обратитесь к врачу, если:**
    - Необычные кровотечения
    - Острая боль
    - Повышенная температура
    """,

    'dermatolog': """
    **Для здоровья кожи:**
    - Увлажняйте кожу
    - Защищайте кожу от солнца
    - Используйте мягкие уходовые средства
    - Избегайте аллергенов

    **Правила ухода:**
    - Соблюдайте гигиену кожи
    - Отдавайте предпочтение натуральной косметике
    - Снижайте уровень стресса

    **Обратитесь к врачу, если:**
    - Появились новые пятна
    - Усилился зуд
    - Изменилась пигментация кожи
    """
}

GENERAL_ADVICE_EN = {
    'terapevt': """
    **General advice:**
    - Drink plenty of fluids (water, warm tea)
    - Get enough rest and sleep
    - Eat foods rich in Vitamin C
    - If fever rises, consult a doctor

    **Precautions:**
    - Wear a mask to avoid infecting others
    - Wash your hands frequently
    - Consume warm food and drinks

    **See a doctor if:**
    - Temperature goes above 38.5°C
    - Illness lasts more than 7 days
    - Breathing becomes difficult
    """,

    'stomatolog': """
    **General advice:**
    - Brush your teeth twice a day
    - Use dental floss to clean between teeth
    - Limit sugary foods
    - Visit a dentist regularly

    **For pain relief:**
    - Rinse with warm salt water
    - Apply a cold compress
    - Take painkillers (follow dosage instructions)

    **Seek a dentist immediately if:**
    - Severe toothache
    - Facial swelling
    - High fever
    """,

    'kardiolog': """
    **For heart health:**
    - Eat healthy (low salt, low fat)
    - Exercise regularly
    - Reduce stress
    - Stop smoking

    **Blood pressure control:**
    - Monitor your blood pressure daily
    - Maintain a healthy weight
    - Stay hydrated

    **Seek medical help if:**
    - Sharp chest pain occurs
    - Shortness of breath
    - Pain radiates to left arm
    - Dizziness or fainting
    """,

    'urolog': """
    **For urinary health:**
    - Drink 2–3 liters of water daily
    - Maintain personal hygiene
    - Take Vitamin C
    - Don’t delay urination

    **Prevention tips:**
    - Eat cranberries
    - Limit caffeine intake
    - Rest well during illness

    **See a doctor if:**
    - Blood in urine
    - High fever
    - Sudden pain
    """,

    'ginekolog': """
    **For women's health:**
    - Have regular gynecological checkups
    - Maintain proper hygiene
    - Eat healthy
    - Reduce stress levels

    **Pay attention to:**
    - Track your menstrual cycle
    - Note unusual symptoms
    - Learn self-examination

    **See a doctor if:**
    - Unusual bleeding
    - Severe pain
    - Fever occurs
    """,

    'dermatolog': """
    **For skin health:**
    - Moisturize your skin
    - Protect from sun exposure
    - Use gentle skincare products
    - Avoid allergens

    **Skincare tips:**
    - Follow daily skin hygiene
    - Prefer natural products
    - Reduce stress

    **Consult a dermatologist if:**
    - New spots appear
    - Itching worsens
    - Skin color changes
    """
}

GENERAL_ADVICE = {
    'uz': GENERAL_ADVICE_UZ,
    'ru': GENERAL_ADVICE_RU,
    'en': GENERAL_ADVICE_EN,
}


# Chat javob shablonlari
CHAT_RESPONSE_TEMPLATES_UZ = {
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

CHAT_RESPONSE_TEMPLATES_RU = {
    'greeting': """
    Здравствуйте! Я ваш медицинский помощник.

    Расскажите, что вас беспокоит. Уточните, пожалуйста:
    - Какие симптомы вы ощущаете?
    - Сколько времени это продолжается?
    - Где именно болит?

    Я помогу вам подобрать подходящего врача! 🏥
    """,

    'classification_result': """
    Я проанализировал ваше обращение.

    **Рекомендуемый специалист:** {specialty}
    **Уровень уверенности:** {confidence}%
    **Причина:** {explanation}

    Вот список лучших специалистов в этой области:
    """,

    'no_classification': """
    Для более точной рекомендации мне нужно больше информации.

    Пожалуйста, уточните:
    - Какие именно симптомы вы испытываете?
    - Как долго это продолжается?
    - Уровень боли по шкале от 1 до 10?

    Это поможет мне порекомендовать нужного врача.
    """,

    'emergency_warning': """
    ⚠️ **ВНИМАНИЕ: Это может быть экстренный случай!**

    Ваши симптомы требуют срочной медицинской помощи.

    **Немедленно:**
    - Обратитесь в ближайшую больницу
    - Вызовите скорую помощь: 103
    - Или немедленно проконсультируйтесь с врачом

    Не теряйте время! 🚨
    """,

    'general_advice': """
    **Общие рекомендации:**
    {advice}

    **Важно:** Это только общая информация. Для точного диагноза и лечения обязательно обратитесь к врачу.
    """,

    'doctor_recommendation': """
    **Рекомендуемые врачи:**

    {doctors_list}

    **Обратите внимание при выборе врача:**
    - Опыт и квалификация
    - Удобное местоположение
    - Стоимость и условия оплаты
    - Отзывы других пациентов

    Свяжитесь с врачом по телефону или запишитесь онлайн.
    """,

    'feedback_request': """
    Рад, что смог помочь!

    Пожалуйста, оставьте отзыв:
    - Были ли рекомендации полезны?
    - Смогли ли вы связаться с врачом?
    - Ваши предложения по улучшению сервиса?

    Крепкого здоровья! 💚
    """
}

CHAT_RESPONSE_TEMPLATES_EN = {
    'greeting': """
    Hello! I am your medical assistant.

    Please tell me what’s bothering you. Share the following details:
    - What symptoms do you have?
    - How long have you had them?
    - Where exactly is the pain?

    I’ll help you find the right specialist! 🏥
    """,

    'classification_result': """
    I’ve analyzed your complaint.

    **Recommended specialist:** {specialty}
    **Confidence level:** {confidence}%
    **Reason:** {explanation}

    Here is a list of top doctors in this field:
    """,

    'no_classification': """
    I need more information to understand your issue better.

    Please tell me:
    - What specific symptoms are you experiencing?
    - How long have they lasted?
    - What is the pain level (1 to 10)?

    Based on this, I’ll recommend the most suitable doctor.
    """,

    'emergency_warning': """
    ⚠️ **WARNING: This may be an emergency!**

    Your symptoms could require urgent medical attention.

    **Please:**
    - Go to the nearest hospitals immediately
    - Call emergency services: 103
    - Or seek urgent care from a doctor

    Don’t delay! 🚨
    """,

    'general_advice': """
    **General recommendations:**
    {advice}

    **Note:** This is general information only. Always consult a doctor for a proper diagnosis and treatment.
    """,

    'doctor_recommendation': """
    **Recommended doctors:**

    {doctors_list}

    **Things to consider when choosing a doctor:**
    - Experience and qualifications
    - Location and convenience
    - Cost and payment options
    - Reviews from other patients

    Call the doctor or schedule an appointment online.
    """,

    'feedback_request': """
    I’m glad I could help!

    Feel free to leave feedback:
    - Was the advice helpful?
    - Were you able to contact a doctor?
    - Any suggestions to improve the service?

    Stay healthy! 💚
    """
}

CHAT_RESPONSE_TEMPLATES = {
    'uz': CHAT_RESPONSE_TEMPLATES_UZ,
    'ru': CHAT_RESPONSE_TEMPLATES_RU,
    'en': CHAT_RESPONSE_TEMPLATES_EN,
}


# Xatolik xabarlari
ERROR_MESSAGES_UZ = {
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

ERROR_MESSAGES_RU = {
    'ai_unavailable': """
    Извините, в данный момент сервис недоступен.

    Пока вы можете обратиться к следующим специалистам:
    - Терапевт — для общих проблем
    - Скорая помощь — 103

    Пожалуйста, попробуйте позже.
    """,

    'invalid_input': """
    Пожалуйста, опишите вашу проблему более точно.

    Например:
    - "Голова болит уже два дня"
    - "Сильно болит зуб"
    - "Повышенное давление"

    Это поможет мне вам лучше помочь.
    """,

    'system_error': """
    Произошла техническая ошибка.

    Пожалуйста:
    - Обновите страницу
    - Попробуйте снова
    - Или обратитесь напрямую к врачу

    Приносим извинения за неудобства.
    """
}

ERROR_MESSAGES_EN = {
    'ai_unavailable': """
    Sorry, the AI service is currently unavailable.

    In the meantime, you can consult:
    - A general practitioner (therapist) for common issues
    - Emergency services: 103

    Please try again later.
    """,

    'invalid_input': """
    Please describe your issue more clearly.

    For example:
    - "I have had a headache for two days"
    - "My tooth hurts badly"
    - "My blood pressure is high"

    This will help me assist you better.
    """,

    'system_error': """
    A technical error has occurred.

    Please:
    - Refresh the page
    - Try again
    - Or contact a doctor directly

    Sorry for the inconvenience.
    """
}

ERROR_MESSAGES = {
    'uz': ERROR_MESSAGES_UZ,
    'ru': ERROR_MESSAGES_RU,
    'en': ERROR_MESSAGES_EN,
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


def get_prompt(prompt_type, language='uz', **kwargs):
    """Tilga mos keladigan promptni olish"""
    prompts = {
        'classification': CLASSIFICATION_PROMPTS,
        'advice': ADVICE_PROMPTS,
        'chat_templates': CHAT_RESPONSE_TEMPLATES,
        'error_messages': ERROR_MESSAGES,
    }

    prompt_dict = prompts.get(prompt_type, {})
    return prompt_dict.get(language, prompt_dict.get('uz', ''))



def get_symptom_keywords(language='uz'):
    """Tilga mos keladigan simptom kalit so'zlarini olish"""
    return SYMPTOM_KEYWORDS.get(language, SYMPTOM_KEYWORDS['uz'])


def get_emergency_keywords(language='uz'):
    """Tilga mos keladigan shoshilinch kalit so'zlarini olish"""
    return EMERGENCY_KEYWORDS.get(language, EMERGENCY_KEYWORDS['uz'])


def get_general_advice(specialty, language='uz'):
    """Tilga mos keladigan umumiy maslahatni olish"""
    advice_dict = GENERAL_ADVICE.get(language, GENERAL_ADVICE['uz'])
    return advice_dict.get(specialty, '')

def get_high_priority_keywords(language='uz'):
    """Tilga mos keladigan yuqori prioritet kalit so'zlarini olish"""
    return HIGH_PRIORITY_KEYWORDS.get(language, HIGH_PRIORITY_KEYWORDS['uz'])

def get_chat_response_template(template_name, language='uz'):
    """Tilga mos keladigan chat javob shablonini olish"""
    templates = CHAT_RESPONSE_TEMPLATES.get(language, CHAT_RESPONSE_TEMPLATES['uz'])
    return templates.get(template_name, '')

def get_error_message(error_code, language='uz'):
    """Tilga mos keladigan xatolik xabarini olish"""
    messages = ERROR_MESSAGES.get(language, ERROR_MESSAGES['uz'])
    return messages.get(error_code, 'Xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.')
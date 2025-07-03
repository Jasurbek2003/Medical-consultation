from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.doctors.models import Doctor
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Doctor modeli uchun test ma\'lumotlarini yaratish'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Yaratilishi kerak bo\'lgan shifokorlar soni'
        )

    def handle(self, *args, **options):
        count = options['count']

        # Test ma'lumotlari
        first_names = [
            'Azim', 'Dilshod', 'Karim', 'Nodir', 'Otabek', 'Rustam', 'Sanjar', 'Umid',
            'Fatima', 'Gulnora', 'Malika', 'Nodira', 'Oybek', 'Sabina', 'Sevara', 'Zarina'
        ]

        last_names = [
            'Abdullayev', 'Karimov', 'Toshmatov', 'Umarov', 'Rahimov', 'Saidov',
            'Yusupov', 'Aminov', 'Nazarov', 'Sultonov', 'Boboyev', 'Ismoilov'
        ]

        middle_names = [
            'Akramovich', 'Botirovich', 'Dilshodovich', 'Karimovich', 'Nodirbek',
            'Otabekovich', 'Rustamovich', 'Sanjarovich', 'Umidovich', 'Azimovich'
        ]

        regions = [
            'Toshkent', 'Samarqand', 'Buxoro', 'Andijon', 'Farg\'ona', 'Namangan',
            'Qashqadaryo', 'Surxondaryo', 'Jizzax', 'Sirdaryo', 'Navoiy', 'Xorazm'
        ]

        districts = [
            'Chilonzor', 'Yunusobod', 'Mirzo Ulug\'bek', 'Shayxontohur', 'Olmazor',
            'Bektemir', 'Uchtepa', 'Sergeli', 'Yakkasaroy', 'Mirobod'
        ]

        workplaces = [
            'Respublika Shifoxonasi', 'Markaziy Poliklinika', 'Shahar Shifoxonasi',
            'Oilaviy Poliklinika', 'Maxsus Tibbiyot Markazi', 'Xususiy Klinika',
            'Bolalar Shifoxonasi', 'Ayollar Konsultatsiyasi', 'Diagnostika Markazi'
        ]

        educations = [
            'Toshkent Tibbiyot Akademiyasi, 2010-yil',
            'Samarqand Tibbiyot Instituti, 2012-yil',
            'Andijon Tibbiyot Instituti, 2015-yil',
            'Toshkent Pediatriya Instituti, 2008-yil',
            'Rossiya Tibbiyot Universiteti, 2014-yil'
        ]

        achievements = [
            'Eng yaxshi shifokor mukofoti (2020)',
            'Tibbiyot sohasidagi xizmatlari uchun faxriy yorliq',
            'Malaka oshirish kurslari (2021)',
            'Xalqaro konferensiya ishtirokchisi',
            'Ilmiy maqolalar muallifi (10+ maqola)'
        ]

        bio_templates = [
            'Yuqori malakali shifokor, ko\'p yillik tajribaga ega.',
            'Bemorlar bilan ishlaganda individual yondashuvni qo\'llaydi.',
            'Zamonaviy tibbiyot usullaridan foydalanadi.',
            'Doimiy malaka oshirish va yangi texnologiyalarni o\'rganish bilan shug\'ullanadi.',
            'Bemorlarning sog\'ligi va farovonligi uchun mas\'ul.'
        ]

        created_count = 0

        for i in range(count):
            try:
                # Tasodifiy ma'lumotlar tanlash
                specialty = random.choice(Doctor.SPECIALTIES)[0]
                degree = random.choice(Doctor.DEGREES)[0]
                language = random.choice(Doctor.LANGUAGES)[0]

                doctor = Doctor.objects.create(
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    middle_name=random.choice(middle_names),
                    specialty=specialty,
                    degree=degree,
                    experience=random.randint(1, 25),
                    license_number=f'LIC{random.randint(100000, 999999)}',
                    phone=f'+998{random.randint(90, 99)}{random.randint(1000000, 9999999)}',
                    email=f'doctor{i + 1}@example.com',
                    region=random.choice(regions),
                    district=random.choice(districts),
                    address=f'{random.choice(districts)} tumani, {random.randint(1, 50)}-uy',
                    workplace=random.choice(workplaces),
                    workplace_address=f'{random.choice(districts)}, {random.randint(1, 100)}-uy',
                    languages=language,
                    bio=random.choice(bio_templates),
                    education=random.choice(educations),
                    achievements=random.choice(achievements),
                    consultation_price=Decimal(str(random.randint(50000, 500000))),
                    is_available=random.choice([True, True, True, False]),  # 75% mavjud
                    is_online_consultation=random.choice([True, False]),
                    rating=Decimal(str(round(random.uniform(3.5, 5.0), 2))),
                    total_reviews=random.randint(0, 50),
                    work_start_time=f'{random.randint(8, 10)}:00',
                    work_end_time=f'{random.randint(17, 19)}:00',
                    work_days='1,2,3,4,5,6'  # Dushanba-Shanba
                )

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {doctor.get_short_name()} yaratildi')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Shifokor yaratishda xato: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Jami {created_count} ta shifokor muvaffaqiyatli yaratildi!')
        )

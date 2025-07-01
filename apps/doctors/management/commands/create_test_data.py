from django.core.management.base import BaseCommand
from apps.doctors.models import Doctor
from datetime import time
import random


class Command(BaseCommand):
    help = "Test ma\'lumotlar yaratish"

    def handle(self, *args, **options):
        # Test shifokorlar yaratish
        doctors_data = [
            {
                "first_name": "Ahmadjon", "last_name": "Karimov",
                "specialty": "terapevt", "experience": 15,
                "license_number": "DOC001", "phone": "+998901234567",
                "region": "Toshkent", "district": "Chilonzor",
                "address": "Chilonzor tumani, 5-mavze",
                "workplace": "1-son poliklinika",
                "workplace_address": "Bunyodkor kochasi 10",
                "consultation_price": 150000,
                "work_start_time": time(8, 0),
                "work_end_time": time(18, 0),
                "bio": "15 yillik tajribaga ega malakali terapevt"
            },
            {
                "first_name": "Mohira", "last_name": "Abdullayeva",
                "specialty": "stomatolog", "experience": 8,
                "license_number": "DOC002", "phone": "+998902345678",
                "region": "Toshkent", "district": "Yashnobod",
                "address": "Yashnobod tumani, 3-mavze",
                "workplace": "Smile Stomatologiya",
                "workplace_address": "Amir Temur kochasi 25",
                "consultation_price": 200000,
                "work_start_time": time(9, 0),
                "work_end_time": time(19, 0),
                "bio": "Zamonaviy stomatologiya usullarini qollovchi mutaxassis"
            }
        ]

        for data in doctors_data:
            doctor, created = Doctor.objects.get_or_create(
                license_number=data["license_number"],
                defaults=data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created doctor: {doctor.get_full_name()}")
                )

                # Rating qoshish
                doctor.rating = round(random.uniform(4.0, 5.0), 2)
                doctor.total_reviews = random.randint(10, 50)
                doctor.save()

        self.stdout.write(self.style.SUCCESS("Test data created successfully!"))
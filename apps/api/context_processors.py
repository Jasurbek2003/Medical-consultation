from django.db.models import Count, Sum, Avg
from apps.doctors.models import Doctor
from apps.users.models import User
from apps.consultations.models import Consultation
from apps.chat.models import ChatSession


def admin_stats(request):
    """Admin panel uchun statistika"""
    if request.path.startswith('/admin/'):
        try:
            # Asosiy statistikalar
            total_doctors = Doctor.objects.count()
            available_doctors = Doctor.objects.filter(is_available=True).count()
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            total_consultations = Consultation.objects.count()
            completed_consultations = Consultation.objects.filter(status='completed').count()
            total_chats = ChatSession.objects.count()
            active_chats = ChatSession.objects.filter(status='active').count()

            # Qo'shimcha statistikalar
            avg_doctor_rating = Doctor.objects.filter(
                is_available=True
            ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

            total_revenue = Consultation.objects.filter(
                is_paid=True
            ).aggregate(total=Sum('final_amount'))['total'] or 0

            # Eng ko'p ishlatiladigan mutaxassisliklar
            top_specialties = Doctor.objects.values('specialty').annotate(
                count=Count('id')
            ).order_by('-count')[:5]

            return {
                'total_doctors': total_doctors,
                'available_doctors': available_doctors,
                'total_users': total_users,
                'active_users': active_users,
                'total_consultations': total_consultations,
                'completed_consultations': completed_consultations,
                'total_chats': total_chats,
                'active_chats': active_chats,
                'avg_doctor_rating': round(avg_doctor_rating, 1),
                'total_revenue': total_revenue,
                'top_specialties': list(top_specialties),
            }
        except Exception as e:
            # Xatolik bo'lsa, bo'sh statistika qaytarish
            return {
                'total_doctors': 0,
                'total_users': 0,
                'total_consultations': 0,
                'total_chats': 0,
            }
    return {}

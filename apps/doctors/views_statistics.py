
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChargeLog
from .serializers import DoctorStatisticsOverviewSerializer


class DoctorStatisticsOverviewView(APIView):
    """
    Comprehensive statistics overview for doctors to see their own profile metrics
    GET /api/doctors/statistics-overview/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get comprehensive statistics for authenticated doctor"""
        if request.user.user_type != 'doctor':
            return Response(
                {'error': 'Only doctors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        doctor = request.user.doctor_profile

        # Calculate date ranges
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get all-time charge statistics
        all_time_charges = ChargeLog.objects.filter(doctor=doctor).aggregate(
            total_searches=Count('id', filter=Q(charge_type='search')),
            total_card_views=Count('id', filter=Q(charge_type='view_card')),
            total_phone_views=Count('id', filter=Q(charge_type='view_phone')),
            total_charges=Count('id'),
            total_charge_amount=Sum('amount')
        )

        # Get this month's charge statistics
        monthly_charges = ChargeLog.objects.filter(
            doctor=doctor,
            created_at__gte=this_month_start
        ).aggregate(
            searches_this_month=Count('id', filter=Q(charge_type='search')),
            card_views_this_month=Count('id', filter=Q(charge_type='view_card')),
            phone_views_this_month=Count('id', filter=Q(charge_type='view_phone')),
            charges_this_month=Count('id'),
            charge_amount_this_month=Sum('amount')
        )

        # Get consultation statistics for this month
        from apps.consultations.models import Consultation
        consultations_this_month = Consultation.objects.filter(
            doctor=doctor,
            created_at__gte=this_month_start
        ).count()

        # Get reviews this month
        from apps.consultations.models import Review
        reviews_this_month = Review.objects.filter(
            doctor=doctor,
            created_at__gte=this_month_start
        ).count()

        # Calculate success rate
        success_rate = 0
        if doctor.total_consultations > 0:
            success_rate = round(
                (doctor.successful_consultations / doctor.total_consultations) * 100, 2
            )

        # Get wallet information
        wallet_balance = None
        wallet_total_spent = None
        wallet_total_topped_up = None
        if hasattr(doctor.user, 'wallet'):
            wallet = doctor.user.wallet
            wallet_balance = float(wallet.balance)
            wallet_total_spent = float(wallet.total_spent)
            wallet_total_topped_up = float(wallet.total_topped_up)

        # Prepare comprehensive statistics
        stats = {
            # Doctor basic info
            'doctor_id': doctor.id,
            'doctor_name': doctor.user.get_full_name(),
            'specialty': doctor.specialty,
            'specialty_display': doctor.get_specialty_display(),
            'hospital_name': doctor.hospital.name if doctor.hospital else None,
            'is_blocked': doctor.is_blocked,
            'is_available': doctor.is_available,
            'verification_status': doctor.verification_status,

            # View statistics
            'total_profile_views': doctor.profile_views,
            'weekly_views': doctor.weekly_views,
            'monthly_views': doctor.monthly_views,

            # Contact statistics (from ChargeLog)
            'total_searches': all_time_charges['total_searches'] or 0,
            'total_card_views': all_time_charges['total_card_views'] or 0,
            'total_phone_views': all_time_charges['total_phone_views'] or 0,
            'searches_this_month': monthly_charges['searches_this_month'] or 0,
            'card_views_this_month': monthly_charges['card_views_this_month'] or 0,
            'phone_views_this_month': monthly_charges['phone_views_this_month'] or 0,

            # Consultation statistics
            'total_consultations': doctor.total_consultations,
            'successful_consultations': doctor.successful_consultations,
            'success_rate': success_rate,
            'consultations_this_month': consultations_this_month,

            # Rating statistics
            'rating': doctor.rating,
            'total_reviews': doctor.total_reviews,
            'reviews_this_month': reviews_this_month,

            # Financial statistics
            'total_charges': all_time_charges['total_charges'] or 0,
            'total_charge_amount': all_time_charges['total_charge_amount'] or 0,
            'charges_this_month': monthly_charges['charges_this_month'] or 0,
            'charge_amount_this_month': monthly_charges['charge_amount_this_month'] or 0,

            # Wallet information
            'wallet_balance': wallet_balance,
            'wallet_total_spent': wallet_total_spent,
            'wallet_total_topped_up': wallet_total_topped_up,

            # Recent activity
            'last_activity': doctor.last_activity,
            'created_at': doctor.created_at
        }

        serializer = DoctorStatisticsOverviewSerializer(stats)
        return Response(serializer.data)

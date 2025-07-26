from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import timedelta

from .filters import DoctorFilter
from .models import Doctor, DoctorSchedule, DoctorViewStatistics, DoctorSpecialization, DoctorTranslation
from .serializers import (
    DoctorSerializer, DoctorDetailSerializer, DoctorScheduleSerializer,
    DoctorStatisticsSerializer, DoctorUpdateSerializer, DoctorSpecializationSerializer, DoctorTranslationSerializer
)
from .services.translation_service import DoctorTranslationService, TahrirchiTranslationService


class DoctorSpecializationViewSet(viewsets.ModelViewSet):
    """Doctor specialization management"""

    serializer_class = DoctorSpecializationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_admin():
            return DoctorSpecialization.objects.all()
        elif user.is_hospital_admin():
            return DoctorSpecialization.objects.filter(
                doctor__hospital=user.managed_hospital
            )
        elif user.is_doctor():
            return DoctorSpecialization.objects.filter(doctor__user=user)
        else:
            # Patients can view all specializations for available doctors
            return DoctorSpecialization.objects.filter(
                doctor__verification_status='approved',
                doctor__is_available=True
            )

    def perform_create(self, serializer):
        # Only doctor can create their own specializations
        if self.request.user.is_doctor():
            serializer.save(doctor=self.request.user.doctor_profile)
        else:
            raise PermissionError("Faqat shifokorlar mutaxassislik qo'sha oladi")

    @action(detail=False, methods=['get'])
    def my_specializations(self, request):
        """Get current doctor's specializations"""
        if not request.user.is_doctor():
            return Response({
                'error': 'Faqat shifokorlar ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        specializations = DoctorSpecialization.objects.filter(
            doctor=request.user.doctor_profile
        )

        serializer = DoctorSpecializationSerializer(specializations, many=True)
        return Response(serializer.data)

class DoctorViewSet(viewsets.ModelViewSet):
    """Doctor API with role-based access and statistics"""

    queryset = Doctor.objects.select_related('user', 'hospital').prefetch_related('schedules')
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DoctorFilter
    search_fields = ['user__first_name', 'user__last_name', 'specialty', 'workplace']
    ordering_fields = ['rating', 'experience', 'consultation_price', 'created_at']
    ordering = ['-rating', '-total_reviews']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DoctorDetailSerializer
        elif self.action == 'update_profile':
            return DoctorUpdateSerializer
        elif self.action == 'statistics':
            return DoctorStatisticsSerializer
        return DoctorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_admin():
            # Admin can see all doctors
            return queryset
        elif user.is_hospital_admin():
            # Hospital admin can only see doctors in their hospital
            return queryset.filter(hospital=user.managed_hospital)
        elif user.is_doctor():
            # Doctors can see all verified doctors + their own profile
            return queryset.filter(
                Q(verification_status='approved', user__is_active=True) |
                Q(user=user)
            )
        else:
            # Patients can only see verified, available doctors
            return queryset.filter(
                verification_status='approved',
                user__is_active=True,
                is_available=True
            )

    def retrieve(self, request, *args, **kwargs):
        """Get doctor detail and increment view count"""
        doctor = self.get_object()

        # Increment view statistics (only for non-doctor users viewing other doctors)
        if not request.user.is_doctor() or request.user.doctor_profile != doctor:
            doctor.increment_profile_views()

            # Record daily statistics
            today = timezone.now().date()
            stats, created = DoctorViewStatistics.objects.get_or_create(
                doctor=doctor,
                date=today,
                defaults={'daily_views': 0, 'unique_visitors': 0}
            )
            stats.daily_views += 1

            # Track unique visitors (simple implementation)
            if not hasattr(request, '_doctor_views_today'):
                request._doctor_views_today = set()

            if doctor.id not in request._doctor_views_today:
                stats.unique_visitors += 1
                request._doctor_views_today.add(doctor.id)

            stats.save()

        serializer = self.get_serializer(doctor)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current doctor's profile"""
        if not request.user.is_doctor():
            return Response({
                'error': 'Faqat shifokorlar ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = request.user.doctor_profile
            serializer = DoctorDetailSerializer(doctor)
            return Response(serializer.data)
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Shifokor profili topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def update_my_profile(self, request):
        """Update current doctor's profile"""
        if not request.user.is_doctor():
            return Response({
                'error': 'Faqat shifokorlar o\'zgartira oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = request.user.doctor_profile
            serializer = DoctorUpdateSerializer(doctor, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Profil muvaffaqiyatli yangilandi',
                    'doctor': DoctorDetailSerializer(doctor).data
                })

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Doctor.DoesNotExist:
            return Response({
                'error': 'Shifokor profili topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get doctor statistics"""
        doctor = self.get_object()

        # Check permissions
        if not self.can_view_statistics(request.user, doctor):
            return Response({
                'error': 'Statistikalarni ko\'rish uchun ruxsat yo\'q'
            }, status=status.HTTP_403_FORBIDDEN)

        # Calculate statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # View statistics
        view_stats = {
            'total_views': doctor.profile_views,
            'weekly_views': doctor.weekly_views,
            'monthly_views': doctor.monthly_views,
            'daily_stats': []
        }

        # Get daily view statistics for the last 30 days
        daily_stats = DoctorViewStatistics.objects.filter(
            doctor=doctor,
            date__gte=month_ago
        ).order_by('date')

        for stat in daily_stats:
            view_stats['daily_stats'].append({
                'date': stat.date,
                'views.py': stat.daily_views,
                'unique_visitors': stat.unique_visitors
            })

        # Consultation statistics
        from apps.consultations.models import Consultation
        consultations = Consultation.objects.filter(doctor=doctor)

        consultation_stats = {
            'total': doctor.total_consultations,
            'successful': doctor.successful_consultations,
            'success_rate': doctor.success_rate,
            'this_week': consultations.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            'this_month': consultations.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'by_status': {}
        }

        # Group consultations by status
        status_counts = consultations.values('status').annotate(count=Count('id'))
        for item in status_counts:
            consultation_stats['by_status'][item['status']] = item['count']

        # Rating and review statistics
        rating_stats = {
            'average_rating': doctor.rating,
            'total_reviews': doctor.total_reviews,
            'rating_distribution': {}
        }

        # Get rating distribution
        from apps.consultations.models import Review
        rating_dist = Review.objects.filter(
            doctor=doctor,
            is_active=True
        ).values('rating').annotate(count=Count('id'))

        for item in rating_dist:
            rating_stats['rating_distribution'][item['rating']] = item['count']

        # Revenue statistics (if needed)
        revenue_stats = {
            'total_potential': doctor.total_consultations * doctor.consultation_price,
            'this_month_potential': consultation_stats['this_month'] * doctor.consultation_price
        }

        response_data = {
            'doctor_id': doctor.id,
            'doctor_name': doctor.full_name,
            'view_statistics': view_stats,
            'consultation_statistics': consultation_stats,
            'rating_statistics': rating_stats,
            'revenue_statistics': revenue_stats,
            'last_updated': timezone.now()
        }

        return Response(response_data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def admin_statistics(self, request):
        """Get overall doctor statistics for admin"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        # Overall statistics
        total_doctors = Doctor.objects.count()
        verified_doctors = Doctor.objects.filter(verification_status='approved').count()
        pending_doctors = Doctor.objects.filter(verification_status='pending').count()
        active_doctors = Doctor.objects.filter(
            verification_status='approved',
            is_available=True,
            user__is_active=True
        ).count()

        # Specialty distribution
        specialty_stats = Doctor.objects.values('specialty').annotate(
            count=Count('id')
        ).order_by('-count')

        # Top rated doctors
        top_doctors = Doctor.objects.filter(
            verification_status='approved'
        ).order_by('-rating', '-total_reviews')[:10]

        # Most viewed doctors
        most_viewed = Doctor.objects.filter(
            verification_status='approved'
        ).order_by('-profile_views')[:10]

        response_data = {
            'overview': {
                'total_doctors': total_doctors,
                'verified_doctors': verified_doctors,
                'pending_doctors': pending_doctors,
                'active_doctors': active_doctors,
                'verification_rate': round((verified_doctors / total_doctors * 100), 2) if total_doctors > 0 else 0
            },
            'specialty_distribution': list(specialty_stats),
            'top_rated_doctors': DoctorSerializer(top_doctors, many=True).data,
            'most_viewed_doctors': DoctorSerializer(most_viewed, many=True).data
        }

        return Response(response_data)

    @action(detail=False, methods=['get'])
    def hospital_statistics(self, request):
        """Get doctor statistics for hospital admin"""
        if not request.user.is_hospital_admin():
            return Response({
                'error': 'Faqat shifoxona adminlari ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        hospital = request.user.managed_hospital
        if not hospital:
            return Response({
                'error': 'Shifoxona tayinlanmagan'
            }, status=status.HTTP_400_BAD_REQUEST)

        doctors = Doctor.objects.filter(hospital=hospital)

        # Hospital doctor statistics
        stats = {
            'total_doctors': doctors.count(),
            'active_doctors': doctors.filter(
                is_available=True,
                verification_status='approved'
            ).count(),
            'pending_approval': doctors.filter(
                verification_status='pending'
            ).count(),
            'average_rating': doctors.filter(
                verification_status='approved'
            ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
            'total_consultations': sum(d.total_consultations for d in doctors),
            'total_views': sum(d.profile_views for d in doctors),
            'doctors_list': DoctorSerializer(doctors, many=True).data
        }

        return Response(stats)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve doctor (Admin only)"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar tasdiqlashi mumkin'
            }, status=status.HTTP_403_FORBIDDEN)

        doctor = self.get_object()
        doctor.approve(request.user)

        return Response({
            'message': 'Shifokor muvaffaqiyatli tasdiqlandi',
            'doctor': DoctorSerializer(doctor).data
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Reject doctor (Admin only)"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar rad etishi mumkin'
            }, status=status.HTTP_403_FORBIDDEN)

        doctor = self.get_object()
        reason = request.data.get('reason', '')

        doctor.reject(reason)

        return Response({
            'message': 'Shifokor rad etildi',
            'reason': reason
        })

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle doctor availability"""
        doctor = self.get_object()

        # Check permissions
        if not (request.user.is_admin() or
                (request.user.is_doctor() and request.user.doctor_profile == doctor)):
            return Response({
                'error': 'Ruxsat berilmagan'
            }, status=status.HTTP_403_FORBIDDEN)

        doctor.is_available = not doctor.is_available
        doctor.save()

        return Response({
            'message': f'Mavjudlik {"yoqildi" if doctor.is_available else "o\'chirildi"}',
            'is_available': doctor.is_available
        })

    def can_view_statistics(self, user, doctor):
        """Check if user can view doctor statistics"""
        if user.is_admin():
            return True
        elif user.is_hospital_admin():
            return doctor.hospital == user.managed_hospital
        elif user.is_doctor():
            return user.doctor_profile == doctor
        else:
            return False

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def translate_profile(self, request, pk=None):
        """Translate doctor profile to all languages"""
        doctor = self.get_object()

        # Check permissions - only doctor themselves or admin can translate
        if request.user != doctor.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        source_lang = request.data.get('source_language', 'uzn_Latn')

        try:
            translation_service = DoctorTranslationService()

            # Get translations
            translations = translation_service.translate_doctor_profile(doctor, source_lang)

            # Save translations
            translation_obj = translation_service.save_doctor_translations(doctor, translations)

            if translation_obj:
                serializer = DoctorTranslationSerializer(translation_obj)
                return Response({
                    'message': 'Profile translated successfully',
                    'translations': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Failed to save translations'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            return Response(
                {'error': f'Translation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def get_translations(self, request, pk=None):
        """Get doctor profile translations"""
        doctor = self.get_object()
        language = request.query_params.get('language')

        try:
            translation_obj = doctor.translations

            if language:
                # Get specific language translations
                translated_data = {}
                for field_name in ['bio', 'education', 'achievements', 'workplace', 'workplace_address']:
                    translated_data[field_name] = translation_obj.get_translation(
                        field_name, language, getattr(doctor, field_name, '')
                    )

                return Response({
                    'language': language,
                    'translations': translated_data
                })
            else:
                # Get all translations
                serializer = DoctorTranslationSerializer(translation_obj)
                return Response(serializer.data)

        except DoctorTranslation.DoesNotExist:
            return Response(
                {'error': 'No translations found for this doctor'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def update_translation(self, request, pk=None):
        """Update specific translation for doctor"""
        doctor = self.get_object()

        # Check permissions
        if request.user != doctor.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        field_name = request.data.get('field_name')
        language = request.data.get('language')
        translation = request.data.get('translation')

        if not all([field_name, language, translation]):
            return Response(
                {'error': 'field_name, language, and translation are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            translation_obj, created = DoctorTranslation.objects.get_or_create(
                doctor=doctor,
                defaults={'translations': {}}
            )

            # Update specific translation
            translation_obj.set_translation(field_name, language, translation)
            translation_obj.is_auto_translated = False  # Mark as manually edited
            translation_obj.save()

            return Response({
                'message': 'Translation updated successfully',
                'field_name': field_name,
                'language': language,
                'translation': translation
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to update translation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DoctorScheduleViewSet(viewsets.ModelViewSet):
    """Doctor schedule management"""

    serializer_class = DoctorScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_admin():
            return DoctorSchedule.objects.all()
        elif user.is_hospital_admin():
            return DoctorSchedule.objects.filter(
                doctor__hospital=user.managed_hospital
            )
        elif user.is_doctor():
            return DoctorSchedule.objects.filter(doctor__user=user)
        else:
            # Patients can view all schedules for available doctors
            return DoctorSchedule.objects.filter(
                doctor__verification_status='approved',
                doctor__is_available=True,
                is_available=True
            )

    def perform_create(self, serializer):
        # Only doctor can create their own schedule
        if self.request.user.is_doctor():
            serializer.save(doctor=self.request.user.doctor_profile)
        else:
            raise PermissionError("Faqat shifokorlar jadval yarata oladi")

    @action(detail=False, methods=['get'])
    def my_schedule(self, request):
        """Get current doctor's schedule"""
        if not request.user.is_doctor():
            return Response({
                'error': 'Faqat shifokorlar ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        schedules = DoctorSchedule.objects.filter(
            doctor=request.user.doctor_profile
        ).order_by('weekday')

        serializer = DoctorScheduleSerializer(schedules, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def batch_translate_api(request):
    """API endpoint for batch translating multiple texts"""

    texts = request.data.get('texts', [])
    source_lang = request.data.get('source_lang', 'uzn_Latn')
    target_lang = request.data.get('target_lang', 'rus_Cyrl')

    if not texts or not isinstance(texts, list):
        return Response(
            {'error': 'texts must be a non-empty list'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(texts) > 100:  # Limit batch size
        return Response(
            {'error': 'Maximum 100 texts allowed per batch'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        translator = TahrirchiTranslationService()
        translated_texts = translator.batch_translate(texts, source_lang, target_lang)

        results = []
        for i, (original, translated) in enumerate(zip(texts, translated_texts)):
            results.append({
                'index': i,
                'original_text': original,
                'translated_text': translated or original,  # Fallback to original
                'success': translated is not None
            })

        return Response({
            'results': results,
            'source_language': source_lang,
            'target_language': target_lang,
            'total_count': len(texts),
            'success_count': sum(1 for result in results if result['success'])
        })

    except Exception as e:
        return Response(
            {'error': f'Batch translation error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def translate_all_doctors_api(request):
    """API endpoint for translating all doctors (admin only)"""

    batch_size = request.data.get('batch_size', 10)

    if batch_size > 50:  # Limit batch size
        batch_size = 50

    try:
        translation_service = DoctorTranslationService()

        # Run translation in background (you might want to use Celery for this)
        translation_service.translate_all_doctors(batch_size)

        return Response({
            'message': 'Translation of all doctors started successfully',
            'batch_size': batch_size
        })

    except Exception as e:
        return Response(
            {'error': f'Failed to start translation: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_translation_languages(request):
    """Get list of supported translation languages"""

    from .services.translation_service import TranslationConfig

    config = TranslationConfig()

    return Response({
        'supported_languages': config.LANGUAGES,
        'default_source': 'uzn_Latn',
        'available_targets': list(config.LANGUAGES.values())
    })
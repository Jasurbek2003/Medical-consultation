from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Q, Avg
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Doctor
from .serializers import DoctorSerializer, DoctorDetailSerializer, DoctorScheduleSerializer


# Web Views
class DoctorListView(ListView):
    """Shifokorlar ro'yxati sahifasi"""
    model = Doctor
    template_name = 'doctors/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 12

    def get_queryset(self):
        queryset = Doctor.objects.filter(is_available=True).order_by('-rating', 'last_name')

        # Filterlash
        specialty = self.request.GET.get('specialty')
        region = self.request.GET.get('region')
        max_price = self.request.GET.get('max_price')
        search = self.request.GET.get('search')

        if specialty:
            queryset = queryset.filter(specialty=specialty)

        if region:
            queryset = queryset.filter(region=region)

        if max_price:
            try:
                queryset = queryset.filter(consultation_price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(workplace__icontains=search) |
                Q(bio__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter uchun ma'lumotlar
        context['specialties'] = Doctor.SPECIALTIES
        context['regions'] = Doctor.objects.values_list('region', flat=True).distinct()
        context['current_filters'] = {
            'specialty': self.request.GET.get('specialty', ''),
            'region': self.request.GET.get('region', ''),
            'max_price': self.request.GET.get('max_price', ''),
            'search': self.request.GET.get('search', ''),
        }

        return context


class DoctorDetailView(DetailView):
    """Shifokor detali sahifasi"""
    model = Doctor
    template_name = 'doctors/doctor_detail.html'
    context_object_name = 'doctor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object

        # Ish jadvali
        context['schedules'] = doctor.schedules.filter(is_available=True).order_by('weekday')

        # Qo'shimcha mutaxassisliklar
        context['specializations'] = doctor.specializations.all()

        # Sharhlar
        context['reviews'] = doctor.reviews.filter(is_active=True, is_verified=True).order_by('-created_at')[:5]
        context['reviews_count'] = doctor.reviews.filter(is_active=True).count()

        # Reyting statistikasi
        if context['reviews_count'] > 0:
            context['rating_stats'] = {
                'avg_professionalism': doctor.reviews.filter(is_active=True).aggregate(
                    avg=Avg('professionalism_rating'))['avg'] or 0,
                'avg_communication': doctor.reviews.filter(is_active=True).aggregate(
                    avg=Avg('communication_rating'))['avg'] or 0,
                'avg_punctuality': doctor.reviews.filter(is_active=True).aggregate(
                    avg=Avg('punctuality_rating'))['avg'] or 0,
            }

        return context


class DoctorSearchView(ListView):
    """Shifokor qidirish sahifasi"""
    model = Doctor
    template_name = 'doctors/doctor_search.html'
    context_object_name = 'doctors'

    def get_queryset(self):
        return Doctor.objects.none()  # AJAX orqali yuklanadi


# API ViewSets
class DoctorViewSet(viewsets.ModelViewSet):
    """Shifokorlar API ViewSet"""
    queryset = Doctor.objects.filter(is_available=True)
    serializer_class = DoctorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['specialty', 'region', 'district', 'is_online_consultation']
    search_fields = ['first_name', 'last_name', 'workplace', 'bio']
    ordering_fields = ['rating', 'experience', 'consultation_price', 'created_at']
    ordering = ['-rating', 'consultation_price']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DoctorDetailSerializer
        return DoctorSerializer

    @action(detail=False, methods=['get'])
    def all(self, request):
        doctors = self.get_queryset()
        serializer = self.get_serializer(doctors, many=True)
        return Response({
            'count': doctors.count(),
            'doctors': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_specialty(self, request):
        """Mutaxassislik bo'yicha shifokorlar"""
        specialty = request.query_params.get('specialty')
        if not specialty:
            return Response(
                {'error': 'specialty parametri talab qilinadi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        doctors = self.get_queryset().filter(specialty=specialty)
        serializer = self.get_serializer(doctors, many=True)

        return Response({
            'specialty': specialty,
            'specialty_display': dict(Doctor.SPECIALTIES).get(specialty, specialty),
            'count': doctors.count(),
            'doctors': serializer.data
        })

    @action(detail=False, methods=['get'])
    def search_by_location(self, request):
        """Joylashuv bo'yicha qidirish"""
        region = request.query_params.get('region')
        district = request.query_params.get('district')

        doctors = self.get_queryset()

        if region:
            doctors = doctors.filter(region__icontains=region)
        if district:
            doctors = doctors.filter(district__icontains=district)

        serializer = self.get_serializer(doctors, many=True)

        return Response({
            'region': region,
            'district': district,
            'count': doctors.count(),
            'doctors': serializer.data
        })

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Eng yuqori reytingli shifokorlar"""
        limit = int(request.query_params.get('limit', 10))

        doctors = self.get_queryset().filter(
            rating__gte=4.0,
            total_reviews__gte=5
        ).order_by('-rating', '-total_reviews')[:limit]

        serializer = self.get_serializer(doctors, many=True)

        return Response({
            'message': f'Top {limit} shifokor',
            'doctors': serializer.data
        })

    @action(detail=False, methods=['get'])
    def available_now(self, request):
        """Hozir mavjud shifokorlar"""
        from datetime import datetime, time

        current_time = datetime.now().time()
        current_weekday = datetime.now().isoweekday()  # 1=Monday, 7=Sunday

        # Hozirgi vaqtda ishlayotgan shifokorlar
        available_doctors = []
        for doctor in self.get_queryset():
            if (doctor.work_start_time <= current_time <= doctor.work_end_time and
                    str(current_weekday) in doctor.work_days.split(',')):
                available_doctors.append(doctor)

        serializer = self.get_serializer(available_doctors, many=True)

        return Response({
            'current_time': current_time.strftime('%H:%M'),
            'count': len(available_doctors),
            'doctors': serializer.data
        })

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Shifokor ish jadvali"""
        doctor = self.get_object()
        schedules = doctor.schedules.filter(is_available=True).order_by('weekday')
        serializer = DoctorScheduleSerializer(schedules, many=True)

        return Response({
            'doctor': doctor.get_short_name(),
            'schedules': serializer.data
        })

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Shifokor sharhlari"""
        doctor = self.get_object()
        reviews = doctor.reviews.filter(is_active=True, is_verified=True).order_by('-created_at')

        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 10))
        start = (page - 1) * per_page
        end = start + per_page

        paginated_reviews = reviews[start:end]

        reviews_data = []
        for review in paginated_reviews:
            reviews_data.append({
                'id': review.id,
                'patient_name': review.patient.get_full_name() or 'Anonim',
                'overall_rating': review.overall_rating,
                'professionalism_rating': review.professionalism_rating,
                'communication_rating': review.communication_rating,
                'punctuality_rating': review.punctuality_rating,
                'title': review.title,
                'comment': review.comment,
                'would_recommend': review.would_recommend,
                'created_at': review.created_at.strftime('%d.%m.%Y')
            })

        return Response({
            'doctor': doctor.get_short_name(),
            'total_reviews': reviews.count(),
            'page': page,
            'per_page': per_page,
            'reviews': reviews_data,
            'rating_summary': {
                'overall_rating': doctor.rating,
                'total_reviews': doctor.total_reviews,
                'avg_professionalism': reviews.aggregate(avg=Avg('professionalism_rating'))['avg'] or 0,
                'avg_communication': reviews.aggregate(avg=Avg('communication_rating'))['avg'] or 0,
                'avg_punctuality': reviews.aggregate(avg=Avg('punctuality_rating'))['avg'] or 0,
            }
        })


# AJAX Views
def doctor_search_ajax(request):
    """AJAX orqali shifokor qidirish"""
    if request.method == 'GET':
        specialty = request.GET.get('specialty')
        region = request.GET.get('region')
        max_price = request.GET.get('max_price')
        search = request.GET.get('search')

        doctors = Doctor.objects.filter(is_available=True)

        if specialty:
            doctors = doctors.filter(specialty=specialty)
        if region:
            doctors = doctors.filter(region=region)
        if max_price:
            try:
                doctors = doctors.filter(consultation_price__lte=float(max_price))
            except (ValueError, TypeError):
                pass
        if search:
            doctors = doctors.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(workplace__icontains=search)
            )

        # Natijalarni JSON formatda qaytarish
        results = []
        for doctor in doctors.order_by('-rating')[:20]:
            results.append({
                'id': doctor.id,
                'name': doctor.get_short_name(),
                'specialty': doctor.get_specialty_display(),
                'experience': doctor.experience,
                'rating': float(doctor.rating),
                'price': float(doctor.consultation_price),
                'workplace': doctor.workplace,
                'region': doctor.region,
                'phone': doctor.phone,
                'is_online': doctor.is_online_consultation,
                'photo_url': doctor.photo.url if doctor.photo else None,
                'detail_url': f'/doctors/{doctor.id}/'
            })

        return JsonResponse({
            'success': True,
            'count': len(results),
            'doctors': results
        })

    return JsonResponse({'success': False, 'error': 'GET method required'})


def get_doctors_by_specialty(request):
    """Mutaxassislik bo'yicha shifokorlar (AJAX)"""
    specialty = request.GET.get('specialty')

    if not specialty:
        return JsonResponse({
            'success': False,
            'error': 'Mutaxassislik ko\'rsatilmagan'
        })

    doctors = Doctor.objects.filter(
        specialty=specialty,
        is_available=True
    ).order_by('-rating', 'consultation_price')

    doctors_data = []
    for doctor in doctors:
        doctors_data.append({
            'id': doctor.id,
            'name': doctor.get_short_name(),
            'experience': doctor.experience,
            'rating': float(doctor.rating),
            'total_reviews': doctor.total_reviews,
            'price': float(doctor.consultation_price),
            'workplace': doctor.workplace,
            'region': doctor.region,
            'district': doctor.district,
            'phone': doctor.phone,
            'is_online': doctor.is_online_consultation,
            'photo_url': doctor.photo.url if doctor.photo else None,
            'bio': doctor.bio or '',
            'work_hours': f"{doctor.work_start_time.strftime('%H:%M')} - {doctor.work_end_time.strftime('%H:%M')}",
            'detail_url': f'/doctors/{doctor.id}/',
            'languages': doctor.get_languages_display()
        })

    return JsonResponse({
        'success': True,
        'specialty': specialty,
        'specialty_display': dict(Doctor.SPECIALTIES).get(specialty, specialty),
        'count': len(doctors_data),
        'doctors': doctors_data
    })


def get_specialties_list(request):
    """Barcha mutaxassisliklar ro'yxati"""
    specialties = []
    for code, name in Doctor.SPECIALTIES:
        count = Doctor.objects.filter(specialty=code, is_available=True).count()
        specialties.append({
            'code': code,
            'name': name,
            'count': count
        })

    return JsonResponse({
        'success': True,
        'specialties': specialties
    })
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from apps.doctors.models import Doctor
from apps.doctors.services.translation_service import DoctorTranslationService, HospitalTranslationService
from apps.hospitals.models import HospitalService, Regions, Districts, Hospital, HospitalTranslation
from apps.billing.models import UserWallet, BillingSettings, DoctorViewCharge
from apps.billing.services import BillingService
from apps.payments.models import Payment, PaymentGateway
from apps.doctors.serializers import DoctorSerializer


class HospitalAdminRequiredPermission(permissions.BasePermission):
    """Custom permission to check if user is hospital admin"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if not request.user.is_hospital_admin():
            return False
        if not request.user.managed_hospital:
            return False
        return True

class HospitalProfileAPIView(APIView):
    """Hospital admin dashboard API"""
    permission_classes = [HospitalAdminRequiredPermission]

    @staticmethod
    def get(request):
        """Get hospital profile data"""
        hospital = request.user.managed_hospital

        if not hospital:
            return Response({
                'success': False,
                'error': 'Hospital not found'
            }, status=status.HTTP_404_NOT_FOUND)
        try:
            translates = HospitalTranslation.objects.get(hospital=hospital).__dict__['translations']
        except HospitalTranslation.DoesNotExist:
            translates = {}


        return Response({
            'success': True,
            'hospital': {
                'id': hospital.id,
                'name': hospital.name,
                'type': hospital.hospital_type,
                'address': hospital.address,
                'phone': hospital.phone,
                'email': hospital.email,
                'founded_year': hospital.founded_year,
                'region_id': hospital.region.id,
                'region_name': hospital.region.name,
                'district_id': hospital.district.id,
                'district_name': hospital.district.name,
                'description': hospital.description,
                'working_hours': hospital.working_hours,
                'working_days': hospital.working_days,
                'logo': hospital.logo.url if hospital.logo else None,
                'website': hospital.website,
                'latitude': hospital.latitude,
                'longitude': hospital.longitude,
                'translations': translates,
                'created_at': hospital.created_at.isoformat(),
                'updated_at': hospital.updated_at.isoformat()
            }
        })

    def put(self, request):
        """Update hospital profile data"""
        hospital = request.user.managed_hospital

        if not hospital:
            return Response({
                'success': False,
                'error': 'Hospital not found'
            }, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', hospital.name)
        address = request.data.get('address', hospital.address)
        phone = request.data.get('phone', hospital.phone)
        email = request.data.get('email', hospital.email)
        founded_year = request.data.get('founded_year', hospital.founded_year)
        region = Regions.objects.get(id=request.data.get('region', hospital.region))
        district = Districts.objects.get(id=request.data.get('district', hospital.district))
        description = request.data.get('description', hospital.description)
        working_hours = request.data.get('working_hours', hospital.working_hours)
        working_days = request.data.get('working_days', hospital.working_days)
        website = request.data.get('website', hospital.website)
        latitude = request.data.get('latitude', hospital.latitude)
        longitude = request.data.get('longitude', hospital.longitude)


        # Update fields
        hospital.name = name
        hospital.address = address
        hospital.phone = phone
        hospital.email = email
        hospital.founded_year = founded_year
        hospital.region = region
        hospital.district = district
        hospital.description = description
        hospital.working_hours = working_hours
        hospital.working_days = working_days
        hospital.website = website
        hospital.latitude = latitude
        hospital.longitude = longitude

        # Save changes
        hospital.save()

        return Response({
            'success': True,
            'hospital': {
                'id': hospital.id,
                'name': hospital.name,
                'type': hospital.hospital_type,
                'address': hospital.address,
                'phone': hospital.phone,
                'email': hospital.email,
                'founded_year': hospital.founded_year,
                'region_id': hospital.region.id,
                'region_name': hospital.region.name,
                'district_id': hospital.district.id,
                'district_name': hospital.district.name,
                'description': hospital.description,
                'working_hours': hospital.working_hours,
                'working_days': hospital.working_days,
                'logo': hospital.logo.url if hospital.logo else None,
                'website': hospital.website,
                'latitude': hospital.latitude,
                'longitude': hospital.longitude,
                'created_at': hospital.created_at.isoformat(),
                'updated_at': hospital.updated_at.isoformat()
            }
        })

class HospitalProfileTranslationAPIView(APIView):
    """Translate hospital profile details (NEW in v3)"""
    permission_classes = [HospitalAdminRequiredPermission]

    @staticmethod
    def get(request):
        """Translate hospital profile details to specified language"""
        hospital = request.user.managed_hospital
        if not hospital:
            return Response({
                'success': False,
                'error': 'Hospital not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            service = HospitalTranslationService()
            translations = service.translate_hospital_profile(hospital)
            service.save_hospital_translations(hospital, translations)
            return Response({
                'success': True,
                'message': 'Hospital profile translated successfully',
                'translations': translations
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error translating hospital profile: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HospitalDashboardAPIView(APIView):
    """Hospital admin dashboard API"""
    permission_classes = [HospitalAdminRequiredPermission]

    @staticmethod
    def get(request):
        """Get hospital dashboard data"""
        hospital = request.user.managed_hospital

        # Get hospital statistics
        total_doctors = Doctor.objects.filter(hospital=hospital).count()
        active_doctors = Doctor.objects.filter(
            hospital=hospital,
            is_available=True,
            verification_status='approved'
        ).count()
        pending_doctors = Doctor.objects.filter(
            hospital=hospital,
            verification_status='pending'
        ).count()

        # Get top doctors by rating
        top_doctors = Doctor.objects.filter(
            hospital=hospital,
            verification_status='approved'
        ).order_by('-rating')[:5]

        return Response({
            'success': True,
            'hospital': {
                'id': hospital.id,
                'name': hospital.name,
                'type': hospital.hospital_type
            },
            'statistics': {
                'total_doctors': total_doctors,
                'active_doctors': active_doctors,
                'pending_doctors': pending_doctors,
                "total_services": HospitalService.objects.filter(hospital=hospital).count(),
                "founded_year": hospital.founded_year,
                'specialization': len(hospital.specialization.split(",")) if hospital.specialization else 0,
            },
            'top_doctors': DoctorSerializer(top_doctors, many=True).data,
        })


class HospitalDoctorsListAPIView(APIView):
    """Hospital doctors list with filters API"""
    permission_classes = [HospitalAdminRequiredPermission]

    @staticmethod
    def get(request):
        """Get hospital doctors with filters"""
        hospital = request.user.managed_hospital

        # Filter parameters
        status_filter = request.GET.get('status', 'all')
        specialty_filter = request.GET.get('specialty', 'all')
        search_query = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 15))

        # Base queryset
        doctors = Doctor.objects.filter(hospital=hospital).select_related('user')

        # Apply filters
        if status_filter == 'active':
            doctors = doctors.filter(is_available=True, verification_status='approved')
        elif status_filter == 'inactive':
            doctors = doctors.filter(is_available=False)
        elif status_filter == 'pending':
            doctors = doctors.filter(verification_status='pending')
        elif status_filter == 'approved':
            doctors = doctors.filter(verification_status='approved')

        if specialty_filter != 'all':
            doctors = doctors.filter(specialty=specialty_filter)

        if search_query:
            doctors = doctors.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__phone__icontains=search_query) |
                Q(license_number__icontains=search_query)
            )

        # Pagination
        paginator = Paginator(doctors, per_page)
        doctors_page = paginator.get_page(page)

        # Get filter options
        specialties = Doctor.SPECIALTIES if hasattr(Doctor, 'SPECIALTIES') else []

        return Response({
            'success': True,
            'doctors': DoctorSerializer(doctors_page, many=True).data,
            'pagination': {
                'current_page': doctors_page.number,
                'total_pages': doctors_page.paginator.num_pages,
                'has_next': doctors_page.has_next(),
                'has_previous': doctors_page.has_previous(),
                'total_items': doctors_page.paginator.count,
            },
            'filters': {
                'specialties': dict(specialties),
                'current_status': status_filter,
                'current_specialty': specialty_filter,
                'search_query': search_query,
            }
        })

class DoctorTranslationAPIView(APIView):
    """Translate doctor details (NEW in v3)"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request, doctor_id):
        """Translate doctor details to specified language"""
        try:
            doctor = get_object_or_404(Doctor, id=doctor_id, verification_status='approved')
            service = DoctorTranslationService()
            if doctor:
                translations = service.translate_doctor_profile(doctor)
                service.save_doctor_translations(doctor, translations)
                return Response({
                    'success': True,
                    'message': 'Doctor profile translated successfully',
                    'translations': translations
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Doctor not found or not approved'
                }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error translating doctor profile: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class DoctorDetailWithBillingAPIView(APIView):
    """Doctor detail view with billing integration (NEW in v3)"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request, doctor_id):
        """Get doctor details with billing check"""
        try:
            doctor = get_object_or_404(Doctor, id=doctor_id, verification_status='approved')

            # Check if billing is enabled
            settings = BillingSettings.get_settings()

            # If user is hospital admin viewing their own doctor, no charge
            if (hasattr(request.user, 'managed_hospital') and
                    request.user.managed_hospital and
                    doctor.hospital == request.user.managed_hospital):
                return Response({
                    'success': True,
                    'doctor': DoctorSerializer(doctor).data,
                    'charged': False,
                    'message': 'Hospital admin access - no charge'
                })

            if not settings.enable_billing:
                # Return doctor data without charging
                return Response({
                    'success': True,
                    'doctor': DoctorSerializer(doctor).data,
                    'charged': False,
                    'message': 'Billing disabled - free access'
                })

            # Check if user has already viewed this doctor today
            today = timezone.now().date()
            already_viewed = DoctorViewCharge.objects.filter(
                user=request.user,
                doctor=doctor,
                created_at__date=today
            ).exists()

            if already_viewed:
                return Response({
                    'success': True,
                    'doctor': DoctorSerializer(doctor).data,
                    'charged': False,
                    'message': 'Already viewed today - free access'
                })

            # Check free views
            free_views_used = BillingService.get_daily_free_views_used(request.user)
            if free_views_used < settings.free_views_per_day:
                # Free view available
                return Response({
                    'success': True,
                    'doctor': DoctorSerializer(doctor).data,
                    'charged': False,
                    'free_view_used': True,
                    'free_views_remaining': settings.free_views_per_day - free_views_used - 1,
                    'message': 'Free view used'
                })

            # Need to charge for view
            try:
                charge_result = BillingService.charge_for_doctor_view(request.user, doctor)

                return Response({
                    'success': True,
                    'doctor': DoctorSerializer(doctor).data,
                    'charged': True,
                    'amount_charged': charge_result['amount_charged'],
                    'new_balance': charge_result['new_balance'],
                    'message': 'Successfully charged for doctor view'
                })

            except ValueError as e:
                return Response({
                    'success': False,
                    'error': str(e),
                    'requires_payment': True
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error retrieving doctor: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoctorViewAccessCheckAPIView(APIView):
    """Check if user can access doctor without charging (NEW in v3)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, doctor_id):
        """Check access without charging"""
        try:
            doctor = get_object_or_404(Doctor, id=doctor_id, verification_status='approved')

            # Check billing settings
            settings = BillingSettings.get_settings()

            if not settings.enable_billing:
                return Response({
                    'has_access': True,
                    'reason': 'billing_disabled',
                    'charge_required': False
                })

            # Check if already viewed today
            today = timezone.now().date()
            already_viewed = DoctorViewCharge.objects.filter(
                user=request.user,
                doctor=doctor,
                created_at__date=today
            ).exists()

            if already_viewed:
                return Response({
                    'has_access': True,
                    'reason': 'already_viewed_today',
                    'charge_required': False
                })

            # Check free views
            free_views_used = BillingService.get_daily_free_views_used(request.user)
            if free_views_used < settings.free_views_per_day:
                return Response({
                    'has_access': True,
                    'reason': 'free_view_available',
                    'charge_required': False,
                    'free_views_remaining': settings.free_views_per_day - free_views_used
                })

            # Check wallet balance
            wallet, created = UserWallet.objects.get_or_create(user=request.user)
            billing_rule = settings.get_billing_rule('doctor_view')

            if billing_rule and wallet.balance >= billing_rule.amount:
                return Response({
                    'has_access': True,
                    'reason': 'sufficient_balance',
                    'charge_required': True,
                    'charge_amount': float(billing_rule.amount),
                    'current_balance': float(wallet.balance)
                })

            return Response({
                'has_access': False,
                'reason': 'insufficient_balance',
                'charge_required': True,
                'charge_amount': float(billing_rule.amount) if billing_rule else 0,
                'current_balance': float(wallet.balance),
                'required_top_up': float(billing_rule.amount - wallet.balance) if billing_rule else 0
            })

        except Exception as e:
            return Response({
                'has_access': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentIntegrationAPIView(APIView):
    """Payment integration for wallet top-up (NEW in v3)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get available payment gateways"""
        gateways = PaymentGateway.objects.filter(is_active=True)

        return Response({
            'success': True,
            'gateways': [
                {
                    'id': g.id,
                    'name': g.name,
                    'display_name': g.display_name,
                    'description': g.description,
                    'min_amount': float(g.min_amount),
                    'max_amount': float(g.max_amount),
                    'supported_currencies': g.supported_currencies,
                    'default_currency': g.default_currency
                } for g in gateways
            ]
        })

    def post(self, request):
        """Create payment for wallet top-up"""
        try:
            gateway_id = request.data.get('gateway_id')
            amount = Decimal(str(request.data.get('amount', 0)))
            currency = request.data.get('currency', 'UZS')

            gateway = get_object_or_404(PaymentGateway, id=gateway_id, is_active=True)

            # Validate amount
            if not gateway.is_amount_valid(amount):
                return Response({
                    'success': False,
                    'error': f'Amount must be between {gateway.min_amount} and {gateway.max_amount}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create payment
            payment = Payment.objects.create(
                user=request.user,
                gateway=gateway,
                payment_type='wallet_topup',
                amount=amount,
                currency=currency,
                total_amount=gateway.get_total_amount(amount),
                commission=gateway.calculate_commission(amount)
            )

            # Generate payment URL based on gateway
            if gateway.name == 'click':
                payment_url = self._generate_click_url(payment)
            elif gateway.name == 'payme':
                payment_url = self._generate_payme_url(payment)
            else:
                payment_url = f"/payments/{payment.id}/redirect/"

            return Response({
                'success': True,
                'payment': {
                    'id': str(payment.id),
                    'amount': float(payment.amount),
                    'total_amount': float(payment.total_amount),
                    'commission': float(payment.commission),
                    'currency': payment.currency,
                    'status': payment.status,
                    'payment_url': payment_url,
                    'gateway': gateway.display_name
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_click_url(self, payment):
        """Generate Click payment URL"""
        from urllib.parse import urlencode

        base_url = "https://my.click.uz/services/pay"
        params = {
            'service_id': payment.gateway.service_id,
            'merchant_id': payment.gateway.merchant_id,
            'amount': int(payment.total_amount),
            'transaction_param': str(payment.id),
            # 'return_url': f"{request.build_absolute_uri('/')}/payments/success/",
            # 'cancel_url': f"{request.build_absolute_uri('/')}/payments/cancel/"
        }

        return f"{base_url}?{urlencode(params)}"

    def _generate_payme_url(self, payment):
        """Generate Payme payment URL"""
        import base64

        # Payme merchant and account info
        merchant_id = payment.gateway.merchant_id
        account = {
            'payment_id': str(payment.id)
        }

        # Encode account info
        account_encoded = base64.b64encode(
            str(account).encode('utf-8')
        ).decode('utf-8')

        return f"https://checkout.paycom.uz/{merchant_id}?a={account_encoded}&ac.payment_id={payment.id}&l=uz"


class HospitalRevenueAnalyticsAPIView(APIView):
    """Hospital revenue analytics (NEW in v3)"""
    permission_classes = [HospitalAdminRequiredPermission]

    @staticmethod
    def get(request):
        """Get hospital revenue analytics"""
        hospital = request.user.managed_hospital
        days = int(request.GET.get('days', 30))

        # Date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Revenue from doctor views
        view_charges = DoctorViewCharge.objects.filter(
            doctor__hospital=hospital,
            created_at__date__range=[start_date, end_date]
        )

        # Daily revenue
        daily_revenue = view_charges.extra(
            {'date': 'date(created_at)'}
        ).values('date').annotate(
            total=Sum('amount_charged'),
            views=Count('id')
        ).order_by('date')

        # Top doctors by revenue
        top_doctors = view_charges.values(
            'doctor__id',
            'doctor__user__first_name',
            'doctor__user__last_name',
            'doctor__specialty'
        ).annotate(
            total_revenue=Sum('amount_charged'),
            view_count=Count('id')
        ).order_by('-total_revenue')[:10]

        # Total statistics
        total_revenue = view_charges.aggregate(
            total=Sum('amount_charged')
        )['total'] or Decimal('0.00')

        total_views = view_charges.count()

        return Response({
            'success': True,
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'totals': {
                'revenue': float(total_revenue),
                'views': total_views,
                'average_per_view': float(total_revenue / total_views) if total_views > 0 else 0
            },
            'daily_revenue': [
                {
                    'date': item['date'],
                    'revenue': float(item['total']),
                    'views': item['views']
                } for item in daily_revenue
            ],
            'top_doctors': [
                {
                    'doctor_id': item['doctor__id'],
                    'name': f"{item['doctor__user__first_name']} {item['doctor__user__last_name']}",
                    'specialty': item['doctor__specialty'],
                    'revenue': float(item['total_revenue']),
                    'views': item['view_count']
                } for item in top_doctors
            ]
        })

class ServiceAPIView(APIView):
    """List hospital services (NEW in v3)"""
    permission_classes = [HospitalAdminRequiredPermission]

    @staticmethod
    def get(request, service_id=None):
        """Get list of hospital services"""
        hospital = request.user.managed_hospital
        if service_id:
            # Get specific service
            service = get_object_or_404(HospitalService, id=service_id, hospital=hospital)
            return Response({
                'success': True,
                'service': {
                    'id': service.id,
                    'name': service.name,
                    'description': service.description,
                    'price': float(service.price),
                    'duration': service.duration,
                    'is_active': service.is_active
                }
            })
        services = HospitalService.objects.filter(hospital=hospital).order_by('name')

        return Response({
            'success': True,
            'services': [
                {
                    'id': service.id,
                    'name': service.name,
                    'description': service.description,
                    'price': float(service.price),
                    'duration': service.duration,
                    'is_active': service.is_active
                } for service in services
            ]
        })

    def post(self, request):
        """Create a new hospital service"""
        hospital = request.user.managed_hospital

        name = request.data.get('name')
        description = request.data.get('description', '')
        price = Decimal(str(request.data.get('price', 0.00)))
        duration = Decimal(str(request.data.get('duration', 0.00)))

        if not name or not price:
            return Response({
                'success': False,
                'error': 'Name and price are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        if price < 0:
            return Response({
                'success': False,
                'error': 'Price cannot be negative'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if service with this name already exists
        if HospitalService.objects.filter(hospital=hospital, name=name).exists():
            return Response({
                'success': False,
                'error': 'Service with this name already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        service = HospitalService.objects.create(
            hospital=hospital,
            name=name,
            description=description,
            price=price,
            duration=duration,
        )

        return Response({
            'success': True,
            'service': {
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'price': float(service.price),
                'is_active': service.is_active,
                'duration': service.duration,
            }
        })


    def put(self, request, service_id):
        """Update an existing hospital service"""
        hospital = request.user.managed_hospital

        service = get_object_or_404(HospitalService, id=service_id, hospital=hospital)

        name = request.data.get('name', service.name)
        description = request.data.get('description', service.description)
        price = Decimal(str(request.data.get('price', service.price)))
        duration = Decimal(str(request.data.get('duration', service.duration)))

        if not name or not price:
            return Response({
                'success': False,
                'error': 'Name and price are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        service.name = name
        service.description = description
        service.price = price
        service.duration = duration
        service.save()

        return Response({
            'success': True,
            'service': {
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'price': float(service.price),
                'is_active': service.is_active,
                'duration': service.duration,
            }
        })

    def delete(self, request, service_id):
        """Delete a hospital service"""
        hospital = request.user.managed_hospital

        service = get_object_or_404(HospitalService, id=service_id, hospital=hospital)

        service.delete()

        return Response({
            'success': True,
            'message': 'Service deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class RegionsListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def get(request):
        """Get list of regions"""

        regions = Regions.objects.all().order_by('name')

        return Response({
            'success': True,
            'regions': [
                {
                    'id': region.id,
                    'name': region.name,
                    'name_en': region.name_en,
                    'name_ru': region.name_ru,
                    'name_kr': region.name_kr
                } for region in regions
            ]
        })

class DistrictsListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def get(request, region_id=None):
        """Get list of districts, optionally filtered by region"""

        if region_id:
            districts = Regions.objects.filter(id=region_id).first().districts.all().order_by('name')
        else:
            districts = Districts.objects.all().order_by('name')

        return Response({
            'success': True,
            'districts': [
                {
                    'id': district.id,
                    'name': district.name,
                    'name_en': district.name_en,
                    'name_ru': district.name_ru,
                    'name_kr': district.name_kr,
                    'region_id': district.region.id,
                    'region_name': district.region.name
                } for district in districts
            ]
        })

class HospitalListAPIView(APIView):
    """List all hospitals (NEW in v3)"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def get(request):
        """Get list of hospitals with basic info"""
        hospitals = Hospital.objects.filter(is_active=True).order_by('name')

        if "search" in request.GET:
            search_query = request.GET.get("search", "")
            hospitals = hospitals.filter(
                Q(name__icontains=search_query) |
                Q(address__icontains=search_query)
            )

        return Response({
            'success': True,
            'hospitals': [
                {
                    'id': hospital.id,
                    'name': hospital.name,
                    'type': hospital.hospital_type,
                    'address': hospital.address,
                    'phone': hospital.phone,
                    'email': hospital.email,
                    'region': {
                        "uz": hospital.region.name,
                        "ru": hospital.region.name_ru,
                        "en": hospital.region.name_en,
                        "kr": hospital.region.name_kr,
                    },
                    # 'district': hospital.district,
                    'district': {
                        "uz": hospital.district.name,
                        "ru": hospital.district.name_ru,
                        "en": hospital.district.name_en,
                        "kr": hospital.district.name_kr,
                    },
                    'logo': hospital.logo.url if hospital.logo else None,
                    'website': hospital.website
                } for hospital in hospitals
            ]
        })


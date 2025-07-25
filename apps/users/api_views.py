from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView

from .models import UserMedicalHistory, UserPreferences
from .serializers import (
    UserSerializer, UserProfileSerializer, DoctorRegistrationSerializer,
    UserMedicalHistorySerializer, UserPreferencesSerializer,
    LoginSerializer, RegisterSerializer, UserProfileUpdateSerializer, UserRegistrationSerializer,
    ChangePasswordSerializer
)

User = get_user_model()


class CustomAuthToken(ObtainAuthToken):
    """Custom authentication token with user data"""

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Create or get token
        token, created = Token.objects.get_or_create(user=user)

        # Update last login IP
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login_ip'])

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'user_type': user.user_type,
            'user': UserSerializer(user).data
        })

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserViewSet(viewsets.ModelViewSet):
    """Enhanced User API ViewSet with role-based access"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserProfileSerializer
        elif self.action == 'register_doctor':
            return DoctorRegistrationSerializer
        elif self.action == 'login':
            return LoginSerializer
        elif self.action == 'register':
            return RegisterSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Admin can see all users
        if user.is_admin():
            return queryset.filter(is_active=True)

        # Hospital admin can see doctors in their hospital
        elif user.is_hospital_admin():
            return queryset.filter(
                Q(user_type='doctor', doctor_profile__hospital=user.managed_hospital) |
                Q(id=user.id)
            )

        # Regular users can only see their own profile
        else:
            return queryset.filter(id=user.id)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """User registration"""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Create token
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Foydalanuvchi muvaffaqiyatli ro\'yxatdan o\'tdi'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """User login"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(request, username=username, password=password)

            if user:
                if not user.is_active:
                    return Response({
                        'error': 'Foydalanuvchi hisobi faol emas'
                    }, status=status.HTTP_401_UNAUTHORIZED)

                # Update last login IP
                user.last_login_ip = self.get_client_ip(request)
                user.save(update_fields=['last_login_ip'])

                # Create or get token
                token, created = Token.objects.get_or_create(user=user)

                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'Muvaffaqiyatli kirildi'
                })
            else:
                return Response({
                    'error': 'Telefon raqam yoki parol noto\'g\'ri'
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """User logout"""
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response({
                'message': 'Muvaffaqiyatli chiqildi'
            })
        except:
            return Response({
                'error': 'Xatolik yuz berdi'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register_doctor(self, request):
        """Doctor registration (requires admin approval)"""
        serializer = DoctorRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            return Response({
                'user': UserSerializer(user).data,
                'message': 'Shifokor ro\'yxati muvaffaqiyatli yuborildi. Admin tasdiqlashini kuting.'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Get user profile"""
        user = self.get_object()

        # Check permissions
        if not self.can_access_user(request.user, user):
            return Response({
                'error': 'Ruxsat berilmagan'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_profile(self, request, pk=None):
        """Update user profile"""
        user = self.get_object()

        # Check permissions
        if not self.can_modify_user(request.user, user):
            return Response({
                'error': 'Ruxsat berilmagan'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user.check_profile_completeness()
            return Response({
                'user': UserProfileSerializer(user).data,
                'message': 'Profil muvaffaqiyatli yangilandi'
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def pending_doctors(self, request):
        """Get doctors pending approval (Admin only)"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        pending_doctors = User.objects.filter(
            user_type='doctor',
            is_approved_by_admin=False,
            is_active=True
        ).select_related('doctor_profile')

        serializer = UserSerializer(pending_doctors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve_doctor(self, request, pk=None):
        """Approve doctor (Admin only)"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar tasdiqlashi mumkin'
            }, status=status.HTTP_403_FORBIDDEN)

        doctor_user = self.get_object()

        if doctor_user.user_type != 'doctor':
            return Response({
                'error': 'Bu foydalanuvchi shifokor emas'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Approve the doctor
        doctor_user.is_approved_by_admin = True
        doctor_user.is_verified = True
        doctor_user.approval_date = timezone.now()
        doctor_user.approved_by = request.user
        doctor_user.save()

        # Also approve the doctor profile if exists
        if hasattr(doctor_user, 'doctor_profile'):
            doctor_user.doctor_profile.approve(request.user)

        return Response({
            'message': 'Shifokor muvaffaqiyatli tasdiqlandi',
            'user': UserSerializer(doctor_user).data
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject_doctor(self, request, pk=None):
        """Reject doctor (Admin only)"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar rad etishi mumkin'
            }, status=status.HTTP_403_FORBIDDEN)

        doctor_user = self.get_object()
        reason = request.data.get('reason', '')

        if doctor_user.user_type != 'doctor':
            return Response({
                'error': 'Bu foydalanuvchi shifokor emas'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reject the doctor
        doctor_user.is_active = False  # Deactivate account
        doctor_user.save()

        # Also reject the doctor profile if exists
        if hasattr(doctor_user, 'doctor_profile'):
            doctor_user.doctor_profile.reject(reason)

        return Response({
            'message': 'Shifokor rad etildi',
            'reason': reason
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def statistics(self, request):
        """Get user statistics (Admin only)"""
        if not request.user.is_admin():
            return Response({
                'error': 'Faqat adminlar ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'patients': User.objects.filter(user_type='patient').count(),
            'doctors': User.objects.filter(user_type='doctor').count(),
            'approved_doctors': User.objects.filter(
                user_type='doctor',
                is_approved_by_admin=True
            ).count(),
            'pending_doctors': User.objects.filter(
                user_type='doctor',
                is_approved_by_admin=False
            ).count(),
            'hospital_admins': User.objects.filter(user_type='hospital_admin').count(),
            'new_users_this_month': User.objects.filter(
                created_at__month=timezone.now().month,
                created_at__year=timezone.now().year
            ).count()
        }

        return Response(stats)

    @action(detail=False, methods=['get'])
    def my_hospital_doctors(self, request):
        """Get doctors in my hospital (Hospital admin only)"""
        if not request.user.is_hospital_admin():
            return Response({
                'error': 'Faqat shifoxona adminlari ko\'ra oladi'
            }, status=status.HTTP_403_FORBIDDEN)

        if not request.user.managed_hospital:
            return Response({
                'error': 'Shifoxona tayinlanmagan'
            }, status=status.HTTP_400_BAD_REQUEST)

        doctors = User.objects.filter(
            user_type='doctor',
            doctor_profile__hospital=request.user.managed_hospital,
            is_active=True
        ).select_related('doctor_profile')

        serializer = UserSerializer(doctors, many=True)
        return Response(serializer.data)

    def can_access_user(self, current_user, target_user):
        """Check if current user can access target user's data"""
        if current_user.is_admin():
            return True
        elif current_user.is_hospital_admin():
            return (
                    target_user == current_user or
                    (target_user.user_type == 'doctor' and
                     hasattr(target_user, 'doctor_profile') and
                     target_user.doctor_profile.hospital == current_user.managed_hospital)
            )
        else:
            return target_user == current_user

    def can_modify_user(self, current_user, target_user):
        """Check if current user can modify target user's data"""
        if current_user.is_admin():
            return True
        elif current_user.is_hospital_admin():
            # Hospital admin can't modify doctor's personal data, only their own
            return target_user == current_user
        else:
            return target_user == current_user

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserMedicalHistoryViewSet(viewsets.ModelViewSet):
    """User Medical History API"""
    serializer_class = UserMedicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return UserMedicalHistory.objects.all()
        else:
            return UserMedicalHistory.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserPreferencesViewSet(viewsets.ModelViewSet):
    """User Preferences API"""
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserPreferences.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserRegistrationAPIView(generics.CreateAPIView):
    """
    User Registration API

    POST /api/v1/users/register/
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user
        user = serializer.save()

        # Create auth token
        token, created = Token.objects.get_or_create(user=user)

        # Prepare response data
        response_data = {
            'success': True,
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'token': token.key
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    Get and Update User Profile

    GET /api/v1/users/profile/
    PUT/PATCH /api/v1/users/profile/
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """Get detailed user profile"""
        user = self.get_object()
        serializer = UserProfileSerializer(user)
        return Response({
            'success': True,
            'user': serializer.data
        })

    def update(self, request, *args, **kwargs):
        """Update user profile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'user': serializer.data
        })


class ChangePasswordAPIView(APIView):
    """
    Change User Password

    POST /api/v1/users/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            # Update password
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # Update token
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)

            return Response({
                'success': True,
                'message': 'Password changed successfully',
                'token': token.key
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DeleteAccountAPIView(APIView):
    """
    Delete User Account

    DELETE /api/v1/users/delete-account/
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user

        # Soft delete - just deactivate
        user.is_active = False
        user.save()

        return Response({
            'success': True,
            'message': 'Account deactivated successfully'
        })


class UploadAvatarAPIView(APIView):
    """
    Upload User Avatar

    POST /api/v1/users/upload-avatar/
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No avatar file provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = request.FILES['avatar']
        user.save()

        return Response({
            'success': True,
            'message': 'Avatar uploaded successfully',
            'avatar_url': user.avatar.url if user.avatar else None
        })


# Quick API endpoints for easy integration
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def quick_register(request):
    """
    Quick registration endpoint
    Required: Username, password, first_name, last_name
    Optional: email, birth_date, gender, etc.
    """
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'token': token.key,
            'user_id': user.id,
            'user_type': user.user_type,
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def quick_login(request):
    """
    Quick login endpoint
    Required: Username, password
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'success': False,
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Authenticate user
    user = authenticate(username=username, password=password)

    if user and user.is_active:
        # Update last login info
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])

        # Get or create token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'token': token.key,
            'user_id': user.id,
            'user_type': user.user_type,
            'profile_complete': user.is_profile_complete,
            'message': 'Login successful'
        })

    return Response({
        'success': False,
        'error': 'Invalid credentials or inactive account'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_my_profile(request):
    """
    Get current user's profile
    """
    serializer = UserProfileSerializer(request.user)
    return Response({
        'success': True,
        'user': serializer.data
    })


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_my_profile(request):
    """
    Update current user's profile
    """
    serializer = UserProfileUpdateSerializer(
        request.user,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'user': serializer.data
        })

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
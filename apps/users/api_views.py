from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import UserMedicalHistory, UserPreferences
from .serializers import (
    UserSerializer, UserProfileSerializer,
    UserMedicalHistorySerializer, UserPreferencesSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """User API ViewSet"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # Hozircha ochiq

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserProfileSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Faqat faol foydalanuvchilar
        queryset = queryset.filter(is_active=True)

        # Agar authenticated bo'lsa, faqat o'z ma'lumotlarini ko'rishi
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            queryset = queryset.filter(id=self.request.user.id)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Foydalanuvchi profili"""
        user = self.get_object()
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_profile(self, request, pk=None):
        """Profilni yangilash"""
        user = self.get_object()

        # Faqat o'z profilini yangilash
        if request.user != user and not request.user.is_staff:
            return Response(
                {'error': 'Ruxsat berilmagan'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Profil to'liqligini tekshirish
            user.check_profile_completeness()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def medical_history(self, request, pk=None):
        """Tibbiy tarix"""
        user = self.get_object()

        # Faqat o'z tarixini ko'rish
        if request.user != user and not request.user.is_staff:
            return Response(
                {'error': 'Ruxsat berilmagan'},
                status=status.HTTP_403_FORBIDDEN
            )

        history = user.medical_history.filter(is_active=True).order_by('-date_recorded')

        page = self.paginate_queryset(history)
        if page is not None:
            serializer = UserMedicalHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = UserMedicalHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_medical_record(self, request, pk=None):
        """Tibbiy yozuv qo'shish"""
        user = self.get_object()

        # Faqat o'z yozuvini qo'shish
        if request.user != user and not request.user.is_staff:
            return Response(
                {'error': 'Ruxsat berilmagan'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        data['user'] = user.id

        serializer = UserMedicalHistorySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def preferences(self, request, pk=None):
        """Foydalanuvchi parametrlari"""
        user = self.get_object()

        # Faqat o'z parametrlarini ko'rish/yangilash
        if request.user != user and not request.user.is_staff:
            return Response(
                {'error': 'Ruxsat berilmagan'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'GET':
            try:
                preferences = user.preferences
                serializer = UserPreferencesSerializer(preferences)
                return Response(serializer.data)
            except UserPreferences.DoesNotExist:
                return Response({})

        elif request.method == 'POST':
            try:
                preferences = user.preferences
                serializer = UserPreferencesSerializer(preferences, data=request.data, partial=True)
            except UserPreferences.DoesNotExist:
                data = request.data.copy()
                data['user'] = user.id
                serializer = UserPreferencesSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Foydalanuvchilar statistikasi"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Faqat admin uchun'},
                status=status.HTTP_403_FORBIDDEN
            )

        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'users_with_complete_profile': User.objects.filter(is_profile_complete=True).count(),
            'users_by_gender': dict(
                User.objects.values('gender').annotate(count=Count('id'))
            ),
            'users_by_region': dict(
                User.objects.exclude(region__isnull=True).values('region').annotate(count=Count('id'))
            ),
            'medical_records_count': UserMedicalHistory.objects.filter(is_active=True).count(),
        }

        return Response(stats)


class UserMedicalHistoryViewSet(viewsets.ModelViewSet):
    """User Medical History API ViewSet"""
    queryset = UserMedicalHistory.objects.filter(is_active=True)
    serializer_class = UserMedicalHistorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by record type
        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        return queryset.order_by('-date_recorded')

    @action(detail=False, methods=['get'])
    def record_types(self, request):
        """Yozuv turlari ro'yxati"""
        return Response(dict(UserMedicalHistory.RECORD_TYPES))


class UserPreferencesViewSet(viewsets.ModelViewSet):
    """User Preferences API ViewSet"""
    queryset = UserPreferences.objects.all()
    serializer_class = UserPreferencesSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset
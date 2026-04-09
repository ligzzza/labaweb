from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from .models import MasterClass, Category, Booking, Review, Favorite, Notification
from .serializers import (
    MasterClassSerializer, CategorySerializer, BookingSerializer,
    ReviewSerializer, FavoriteSerializer, UserSerializer
)

User = get_user_model()


# ============================================================
# VIEWSETS ДЛЯ МАСТЕР-КЛАССОВ
# ============================================================

class MasterClassViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с мастер-классами"""
    queryset = MasterClass.objects.all()
    serializer_class = MasterClassSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Фильтрация мастер-классов"""
        queryset = super().get_queryset()

        # Фильтрация по городу
        city = self.request.query_params.get('city', None)
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Фильтрация по категории
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)

        # Фильтрация по статусу (только одобренные для обычных пользователей)
        if not self.request.user.is_admin and not self.request.user.is_organizer:
            queryset = queryset.filter(status='approved')

        return queryset

    def perform_create(self, serializer):
        """При создании устанавливаем текущего пользователя как организатора"""
        serializer.save(organizer=self.request.user)


# ============================================================
# VIEWSETS ДЛЯ КАТЕГОРИЙ
# ============================================================

class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с категориями"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# ============================================================
# VIEWSETS ДЛЯ БРОНИРОВАНИЙ
# ============================================================

class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с бронированиями"""
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Пользователь видит только свои бронирования"""
        user = self.request.user
        if user.is_admin:
            return Booking.objects.all()
        return Booking.objects.filter(participant=user)


# ============================================================
# VIEWSETS ДЛЯ ОТЗЫВОВ
# ============================================================

class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с отзывами"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Только одобренные отзывы для всех, все отзывы для админа"""
        if self.request.user.is_admin:
            return Review.objects.all()
        return Review.objects.filter(status='approved')


# ============================================================
# VIEWSETS ДЛЯ ИЗБРАННОГО
# ============================================================

class FavoriteViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с избранным"""
    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Пользователь видит только своё избранное"""
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """При создании устанавливаем текущего пользователя"""
        serializer.save(user=self.request.user)


# ============================================================
# ПРОСТЫЕ GENERIC VIEWS
# ============================================================

class UserListView(generics.ListAPIView):
    """Список пользователей (только для админа)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
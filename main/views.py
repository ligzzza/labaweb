from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model

from .forms import CustomUserCreationForm
from .models import MasterClass, Category, Booking, Review, Favorite, Notification
from .serializers import (
    MasterClassSerializer, CategorySerializer, BookingSerializer,
    ReviewSerializer, FavoriteSerializer, UserSerializer
)
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

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

from django.shortcuts import render

# ============================================================
# ФРОНТЕНД (HTML-СТРАНИЦЫ)
# ============================================================

def home(request):
    """Главная страница"""
    return render(request, 'main/home.html')


def catalog(request):
    """Каталог мастер-классов"""
    return render(request, 'main/catalog.html')


def masterclass_detail(request, pk):
    """Детальная страница мастер-класса"""
    return render(request, 'main/masterclass_detail.html')


def category_detail(request, slug):
    """Страница категории"""
    return render(request, 'main/category_detail.html')


def register(request):
    """Регистрация"""
    return render(request, 'registration/register.html')


def user_login(request):
    """Вход"""
    return render(request, 'registration/login.html')


def profile(request):
    """Личный кабинет"""
    return render(request, 'main/profile.html')


def add_review(request, masterclass_pk):
    """Добавление отзыва"""
    return render(request, 'main/add_review.html')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})
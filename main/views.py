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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from .models import MasterClass, Category, Booking, Image
from .forms import MasterClassForm, ReviewForm

User = get_user_model()

from django.contrib.auth.decorators import login_required
from .models import MasterClass, Favorite

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


# Страница избранного
@login_required
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('masterclass')
    return render(request, 'main/favorites.html', {'favorites': favorites})


# Переключение избранного с перезагрузкой страницы
@login_required
def toggle_favorite(request, pk):
    masterclass = get_object_or_404(MasterClass, pk=pk)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        masterclass=masterclass
    )

    if not created:
        favorite.delete()

    return redirect('masterclass_detail', pk=pk)


# API для AJAX
@login_required
def toggle_favorite_api(request, pk):
    masterclass = get_object_or_404(MasterClass, pk=pk)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        masterclass=masterclass
    )

    if not created:
        favorite.delete()
        is_favorite = False
    else:
        is_favorite = True

    return JsonResponse({'is_favorite': is_favorite})


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
    masterclass = get_object_or_404(MasterClass, pk=pk, status='approved')
    reviews = masterclass.reviews.filter(status='approved').order_by('-created_at')

    user_has_booking = False
    user_review = None
    if request.user.is_authenticated:
        user_has_booking = Booking.objects.filter(
            participant=request.user,
            masterclass=masterclass,
            status__in=['confirmed', 'completed']
        ).exists()
        if user_has_booking:
            user_review = Review.objects.filter(author=request.user, masterclass=masterclass).first()

    context = {
        'masterclass': masterclass,
        'reviews': reviews,
        'user_has_booking': user_has_booking,
        'user_review': user_review,
    }
    return render(request, 'main/masterclass_detail.html', context)


def category_detail(request, slug):
    """Страница категории"""
    return render(request, 'main/category_detail.html')


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


# ===== СОЗДАНИЕ МАСТЕР-КЛАССА =====
@login_required
def create_masterclass(request):
    if request.user.role not in ['organizer', 'admin']:
        return redirect('home')

    if request.method == 'POST':
        form = MasterClassForm(request.POST, request.FILES)
        if form.is_valid():
            masterclass = form.save(commit=False)
            masterclass.organizer = request.user
            masterclass.save()  # commit=True здесь
            # Сохраняем загруженные изображения
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                Image.objects.create(
                    masterclass=masterclass,
                    image=image,
                    is_main=(i == 0)  # первое фото — главное
                )
            return redirect('masterclass_detail', pk=masterclass.pk)
    else:
        form = MasterClassForm()

    return render(request, 'main/masterclass_form.html', {'form': form, 'title': 'Создание мастер-класса'})


# ===== РЕДАКТИРОВАНИЕ МАСТЕР-КЛАССА =====
@login_required
def edit_masterclass(request, pk):
    masterclass = get_object_or_404(MasterClass, pk=pk)

    if request.user != masterclass.organizer and not request.user.is_admin:
        return redirect('home')

    if request.method == 'POST':
        form = MasterClassForm(request.POST, request.FILES, instance=masterclass)  # ← request.FILES
        if form.is_valid():
            masterclass = form.save()

            # Сохраняем новые изображения (если загружены)
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                Image.objects.create(
                    masterclass=masterclass,
                    image=image,
                    is_main=(i == 0 and not masterclass.images.exists())
                )

            return redirect('masterclass_detail', pk=masterclass.pk)
    else:
        form = MasterClassForm(instance=masterclass)

    return render(request, 'main/masterclass_form.html', {'form': form, 'title': 'Редактирование мастер-класса'})

# ===== УДАЛЕНИЕ МАСТЕР-КЛАССА =====
@login_required
def delete_masterclass(request, pk):
    masterclass = get_object_or_404(MasterClass, pk=pk)

    if request.user != masterclass.organizer and not request.user.is_admin:
        return redirect('home')

    if request.method == 'POST':
        masterclass.delete()
        return redirect('catalog')

    return render(request, 'main/masterclass_confirm_delete.html', {'masterclass': masterclass})

# ===== ДЕМОНСТРАЦИЯ select_related И prefetch_related =====
def catalog_optimized(request):
    # select_related — для ForeignKey (один SQL-запрос вместо N+1)
    masterclasses = MasterClass.objects.select_related('category', 'organizer').all()

    # prefetch_related — для обратных связей (ManyToOne, ManyToMany)
    categories = Category.objects.prefetch_related(
        Prefetch('masterclasses', queryset=MasterClass.objects.filter(status='approved'))
    ).all()

    # Ещё пример с prefetch_related
    masterclasses_with_images = MasterClass.objects.prefetch_related('images').filter(status='approved')

    return render(request, 'main/catalog.html', {
        'masterclasses': masterclasses,
        'categories': categories,
    })
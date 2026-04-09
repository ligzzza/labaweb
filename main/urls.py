from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.contrib.auth import views as auth_views

router = DefaultRouter()
router.register(r'masterclasses', views.MasterClassViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'bookings', views.BookingViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'favorites', views.FavoriteViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # ===== НОВЫЕ МАРШРУТЫ ДЛЯ ФРОНТЕНДА (HTML-СТРАНИЦЫ) =====
    path('home/', views.home, name='home'),  # ← добавил home/ чтобы не конфликтовало с API
    path('catalog/', views.catalog, name='catalog'),
    path('masterclass/<int:pk>/', views.masterclass_detail, name='masterclass_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),

    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # Профиль
    path('profile/', views.profile, name='profile'),
    path('masterclass/<int:masterclass_pk>/review/', views.add_review, name='add_review'),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'masterclasses', views.MasterClassViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'bookings', views.BookingViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'favorites', views.FavoriteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
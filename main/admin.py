from django.contrib import admin
from .models import User, Category, MasterClass, Image, Booking, Review, Favorite, Notification

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(MasterClass)
class MasterClassAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'city', 'start_datetime', 'status', 'current_participants', 'max_participants']
    list_filter = ['status', 'city', 'format', 'category']
    search_fields = ['title', 'description']

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['masterclass', 'is_main', 'uploaded_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'masterclass', 'status', 'payment_status', 'total_price']
    list_filter = ['status', 'payment_status']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['author', 'masterclass', 'rating', 'status', 'created_at']
    list_filter = ['rating', 'status']

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'masterclass', 'created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']
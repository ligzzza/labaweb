from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import MasterClass, Category, Booking, Review, Favorite, Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'avatar']


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image']


class MasterClassSerializer(serializers.ModelSerializer):
    """Сериализатор для мастер-классов"""
    organizer_name = serializers.ReadOnlyField(source='organizer.username')
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = MasterClass
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'organizer', 'organizer_name', 'city', 'address', 'format',
            'price', 'max_participants', 'current_participants',
            'start_datetime', 'end_datetime', 'status', 'created_at'
        ]
        read_only_fields = ['organizer', 'current_participants', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    """Сериализатор для бронирований"""
    participant_name = serializers.ReadOnlyField(source='participant.username')
    masterclass_title = serializers.ReadOnlyField(source='masterclass.title')

    class Meta:
        model = Booking
        fields = [
            'id', 'participant', 'participant_name', 'masterclass', 'masterclass_title',
            'status', 'payment_status', 'participants_count', 'total_price', 'created_at'
        ]
        read_only_fields = ['participant', 'total_price', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для отзывов"""
    author_name = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Review
        fields = ['id', 'author', 'author_name', 'masterclass', 'booking', 'rating', 'text', 'status', 'created_at']
        read_only_fields = ['author', 'created_at']


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного"""

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'masterclass', 'created_at']
        read_only_fields = ['user', 'created_at']
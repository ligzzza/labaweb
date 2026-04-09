from django import template
from django.db.models import Count
from ..models import MasterClass, Category

register = template.Library()


# ============================================================
# 1. ПРОСТОЙ ШАБЛОННЫЙ ТЕГ
# ============================================================
@register.simple_tag
def get_categories_count():
    """Возвращает количество категорий"""
    return Category.objects.count()


# ============================================================
# 2. ШАБЛОННЫЙ ТЕГ, ВОЗВРАЩАЮЩИЙ НАБОР ЗАПРОСОВ (QUERYSET)
# ============================================================
@register.simple_tag
def get_upcoming_masterclasses(limit=6):
    """Возвращает queryset предстоящих мастер-классов"""
    return MasterClass.approved_objects.all()[:limit]


# ============================================================
# 3. ШАБЛОННЫЙ ТЕГ С КОНТЕКСТНЫМИ ПЕРЕМЕННЫМИ (INCLUSION TAG)
# ============================================================
@register.inclusion_tag('includes/popular_masterclasses.html')
def show_popular_masterclasses(limit=3):
    """Показывает популярные мастер-классы"""
    popular = MasterClass.approved_objects.annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')[:limit]

    return {
        'popular_masterclasses': popular,
        'title': 'Популярные мастер-классы'
    }


# ============================================================
# 4. ШАБЛОННЫЕ ФИЛЬТРЫ (2 ШТУКИ)
# ============================================================
@register.filter
def rupluralize(value, variants):
    """
    Склонение существительных по числу
    Пример: {{ count|rupluralize:"мастер-класс,мастер-класса,мастер-классов" }}
    """
    variants = variants.split(',')
    value = abs(int(value))

    if value % 10 == 1 and value % 100 != 11:
        return variants[0]
    elif 2 <= value % 10 <= 4 and (value % 100 < 10 or value % 100 >= 20):
        return variants[1]
    else:
        return variants[2]


@register.filter
def rating_stars(value):
    """
    Преобразует число в звёздочки
    Пример: {{ review.rating|rating_stars }}
    """
    try:
        value = int(value)
        return '★' * value + '☆' * (5 - value)
    except (ValueError, TypeError):
        return '☆☆☆☆☆'
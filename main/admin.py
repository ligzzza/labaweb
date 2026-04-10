from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from .models import (
    User, Category, MasterClass, Image,
    Booking, Review, Favorite, Notification
)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.http import HttpResponse
import io
import os

# ============================================================
# 1. ПОЛЬЗОВАТЕЛЬ
# ============================================================

class UserAdmin(admin.ModelAdmin):
    """Настройка отображения пользователей в админке"""

    # === list_display: какие колонки показывать в таблице ===
    # short_description через @admin.display
    list_display = [
        'id',
        'username',
        'email',
        'get_full_name',  # стандартный метод
        'get_role_with_icon',  # кастомный метод с декоратором
        'get_bookings_count',  # кастомный метод
        'is_active',
        'date_joined',
    ]

    # === list_display_links: какие колонки сделать ссылками на редактирование ===
    list_display_links = ['id', 'username', 'email']

    # === list_filter: фильтры справа ===
    list_filter = [
        'role',  # фильтр по роли
        'is_active',  # активен/заблокирован
        'date_joined',  # фильтр по дате регистрации (автоматически по годам/месяцам)
    ]

    # === search_fields: по каким полям искать ===
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'organization_name']

    # === filter_horizontal: удобный виджет для ManyToMany (если бы были) ===
    # filter_horizontal = ['groups', 'user_permissions']

    # === raw_id_fields: вместо выпадающего списка — поле с ID (для ForeignKey с большим кол-вом записей) ===
    # Пока не применяем, но показываю как выглядит
    # raw_id_fields = ['organizer']  # если бы тут был ForeignKey

    # === readonly_fields: поля только для чтения при редактировании ===
    readonly_fields = ['date_joined', 'last_login', 'get_bookings_count_display']

    # === fieldsets: группировка полей на странице редактирования ===
    fieldsets = (
        ('Основная информация', {
            'fields': ('username', 'email', 'password')
        }),
        ('Персональные данные', {
            'fields': ('first_name', 'last_name', 'phone', 'avatar')
        }),
        ('Роль и статус', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Для организатора', {
            'fields': ('organization_name', 'organization_description'),
            'classes': ('collapse',)  # сворачиваемый блок
        }),
        ('Статистика', {
            'fields': ('date_joined', 'last_login', 'get_bookings_count_display'),
        }),
        ('Права доступа', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
    )

    # === Кастомный метод с декоратором @admin.display ===
    @admin.display(
        description="Роль",
        ordering='role'  # можно сортировать по этому полю
    )
    def get_role_with_icon(self, obj):
        """Добавляем иконку к роли"""
        icons = {
            'admin': '👑',
            'organizer': '📋',
            'participant': '👤'
        }
        return f"{icons.get(obj.role, '')} {obj.get_role_display()}"

    @admin.display(
        description="📊 Бронирований",
    )
    def get_bookings_count(self, obj):
        """Количество бронирований пользователя"""
        count = obj.bookings.count()
        return count

    # Для readonly_fields нужен метод без декоратора, возвращающий строку
    def get_bookings_count_display(self, obj):
        return f"Всего бронирований: {obj.bookings.count()}"

    get_bookings_count_display.short_description = "Статистика бронирований"


# ============================================================
# 2. INLINE ДЛЯ ИЗОБРАЖЕНИЙ (встраивается в MasterClass)
# ============================================================

class ImageInline(admin.TabularInline):  # TabularInline — табличный вид, StackedInline — блочный
    """Встроенный редактор изображений прямо на странице мастер-класса"""
    model = Image
    extra = 1  # количество пустых форм для добавления
    fields = ['image', 'is_main', 'uploaded_at']
    readonly_fields = ['uploaded_at']

    # === Кастомный метод для отображения превью ===
    @admin.display(description="Превью")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "Нет фото"


# ============================================================
# 3. INLINE ДЛЯ БРОНИРОВАНИЙ (встраивается в MasterClass)
# ============================================================

class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0  # не показывать пустые формы
    fields = ['participant', 'participants_count', 'total_price', 'status', 'payment_status', 'created_at']
    readonly_fields = ['total_price', 'created_at']
    can_delete = False
    show_change_link = True  # ссылка на полное редактирование

    # Не даем добавлять новые через inline (только просмотр)
    def has_add_permission(self, request, obj):
        return False


# ============================================================
# 4. INLINE ДЛЯ ОТЗЫВОВ (встраивается в MasterClass)
# ============================================================

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ['author', 'rating', 'status', 'created_at']
    readonly_fields = ['author', 'rating', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj):
        return False



@admin.action(description="📄 Сгенерировать PDF-отчёт")
def generate_pdf_report(modeladmin, request, queryset):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Подключаем шрифт DejaVu (лежит в main/fonts/)
    font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSans.ttf')

    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
        font_name = 'DejaVu'
    else:
        font_name = 'Helvetica'

    # Заголовок
    p.setFont(font_name, 18)
    p.drawString(50, height - 50, "Отчёт по мастер-классам")

    p.setFont(font_name, 11)
    p.drawString(50, height - 70, f"Дата: {timezone.now().strftime('%d.%m.%Y %H:%M')}")

    p.line(50, height - 80, width - 50, height - 80)

    # Заголовки таблицы
    y = height - 110
    p.setFont(font_name, 12)
    p.drawString(50, y, "Название")
    p.drawString(250, y, "Город")
    p.drawString(370, y, "Цена")
    p.drawString(460, y, "Участники")

    y -= 25
    p.setFont(font_name, 10)

    total_price = 0
    total_participants = 0

    for mk in queryset:
        if y < 60:
            p.showPage()
            y = height - 50
            p.setFont(font_name, 10)

        title = mk.title[:25] + '...' if len(mk.title) > 25 else mk.title
        p.drawString(50, y, title)
        p.drawString(250, y, mk.city or '—')
        p.drawString(370, y, f"{mk.price} ₽")
        p.drawString(460, y, f"{mk.current_participants}/{mk.max_participants}")

        total_price += float(mk.price or 0)
        total_participants += mk.current_participants or 0
        y -= 20

    # Итоги
    y -= 30
    p.line(50, y, width - 50, y)
    y -= 25
    p.setFont(font_name, 12)
    p.drawString(50, y, f"Всего мастер-классов: {queryset.count()}")
    p.drawString(250, y, f"Стоимость: {total_price:.0f} ₽")
    p.drawString(460, y, f"Участников: {total_participants}")

    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="masterclasses_report.pdf"'
    return response

# ============================================================
# 5. МАСТЕР-КЛАСС (главная модель с максимальными настройками)
# ============================================================

class MasterClassAdmin(admin.ModelAdmin):
    """Расширенная настройка админки для мастер-классов"""

    # === list_display с кастомными методами ===
    list_display = [
        'id',
        'title',
        'category',
        'organizer',
        'city',
        'format',
        'price_display',  # кастомный метод с рублями
        'participants_progress',  # кастомный метод с прогрессом
        'get_status_badge',  # кастомный метод с цветным значком
        'start_datetime',
        'is_upcoming',
    ]

    # === list_display_links ===
    list_display_links = ['id', 'title']

    # === list_filter: фильтры справа ===
    list_filter = [
        'status',
        'format',
        'category',
        'city',
        ('start_datetime', admin.DateFieldListFilter),  # фильтр по дате с выбором "Сегодня/Неделя/Месяц"
    ]

    # === date_hierarchy: навигация по датам сверху (ДЛЯ ЭТОГО И НУЖНО) ===
    date_hierarchy = 'start_datetime'

    # === search_fields ===
    search_fields = ['title', 'description', 'city', 'address', 'organizer__username', 'organizer__email']

    # === filter_horizontal: удобный выбор ManyToMany (если добавите теги потом) ===
    # filter_horizontal = ['tags']

    # === raw_id_fields: для ForeignKey с большим количеством записей ===
    raw_id_fields = ['organizer']  # вместо выпадающего списка всех пользователей

    # === readonly_fields ===
    readonly_fields = [
        'created_at',
        'updated_at',
        'current_participants',
        'free_places_display',
        'total_revenue_display',
        'average_rating_display',
    ]

    # === fieldsets: группировка полей ===
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'category', 'organizer', 'program_file')
        }),
        ('Место и формат', {
            'fields': ('city', 'address', 'format', 'online_link')
        }),
        ('Цена и места', {
            'fields': ('price', 'max_participants', 'current_participants', 'free_places_display')
        }),
        ('Даты', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Модерация', {
            'fields': ('status', 'moderation_comment'),
            'classes': ('wide',)
        }),
        ('Статистика', {
            'fields': ('total_revenue_display', 'average_rating_display', 'created_at', 'updated_at'),
        }),
    )

    # === inlines: встроенные редакторы ===
    inlines = [ImageInline, BookingInline, ReviewInline]

    # === actions: массовые действия ===
    actions = ['approve_masterclasses', 'reject_masterclasses', generate_pdf_report]

    # ===== КАСТОМНЫЕ МЕТОДЫ ДЛЯ list_display =====

    @admin.display(
        description="💰 Цена",
        ordering='price'
    )
    def price_display(self, obj):
        """Форматированный вывод цены"""
        return f"{obj.price:,.0f} ₽".replace(',', ' ')

    @admin.display(
        description="👥 Места",
    )
    def participants_progress(self, obj):
        """Визуальный прогресс-бар заполнения мест"""
        if obj.max_participants and obj.max_participants > 0:
            percent = int((obj.current_participants / obj.max_participants) * 100)
        else:
            percent = 0

        if percent < 70:
            color = 'green'
        elif percent < 90:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<div style="width:100px; background:#eee; border-radius:10px;">'
            '<div style="width:{}%; background:{}; height:10px; border-radius:10px;"></div>'
            '</div>'
            '<small>{}/{} ({}%)</small>',
            str(percent), color, obj.current_participants, obj.max_participants, str(percent)
        )

    @admin.display(
        description="📌 Статус",
        ordering='status'
    )
    def get_status_badge(self, obj):
        """Цветной бейдж статуса"""
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'completed': 'blue',
            'cancelled': 'gray',
        }
        return format_html(
            '<span style="background:{}; color:white; padding:4px 8px; border-radius:12px; font-size:12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )

    # ===== МЕТОДЫ ДЛЯ readonly_fields =====

    def free_places_display(self, obj):
        """Свободные места (для страницы редактирования)"""
        if obj.pk is None:  # новый объект
            return "—"
        free = (obj.max_participants or 0) - (obj.current_participants or 0)
        if free > 0:
            return format_html('<span style="color:green; font-weight:bold;">{} мест</span>', free)
        return format_html('<span style="color:red;">Мест нет</span>')

    free_places_display.short_description = "Свободных мест"

    def total_revenue_display(self, obj):
        """Общая выручка с мастер-класса"""
        if obj.pk is None:
            return "—"
        total = obj.bookings.filter(payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0
        return f"{total:,.0f} ₽".replace(',', ' ')

    total_revenue_display.short_description = "💰 Выручка"

    def average_rating_display(self, obj):
        """Средний рейтинг"""
        if obj.pk is None:
            return "—"
        avg = obj.reviews.filter(status='approved').aggregate(Avg('rating'))['rating__avg']
        if avg:
            stars = '★' * int(avg) + '☆' * (5 - int(avg))
            return f"{stars} ({avg:.1f})"
        return "Нет оценок"

    average_rating_display.short_description = "⭐ Рейтинг"

    # ===== МАССОВЫЕ ДЕЙСТВИЯ (actions) =====

    @admin.action(description="✅ Одобрить выбранные мастер-классы")
    def approve_masterclasses(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"Одобрено мастер-классов: {updated}")

    @admin.action(description="❌ Отклонить выбранные мастер-классы")
    def reject_masterclasses(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"Отклонено мастер-классов: {updated}", level='WARNING')


# ============================================================
# 6. КАТЕГОРИЯ
# ============================================================

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug', 'get_masterclasses_count', 'created_at']
    list_display_links = ['id', 'name']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}  # автозаполнение slug из name
    readonly_fields = ['created_at', 'get_masterclasses_count_display']

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Медиа', {
            'fields': ('image',)
        }),
        ('Статистика', {
            'fields': ('created_at', 'get_masterclasses_count_display')
        }),
    )

    @admin.display(
        description="МК",
        ordering='masterclasses_count'
    )
    def get_masterclasses_count(self, obj):
        # Аннотация для сортировки
        return obj.masterclasses.count()

    def get_masterclasses_count_display(self, obj):
        return f"Мастер-классов в категории: {obj.masterclasses.count()}"

    get_masterclasses_count_display.short_description = "Количество МК"

    # Переопределяем queryset для поддержки сортировки по количеству
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            masterclasses_count=Count('masterclasses')
        )


# ============================================================
# 7. БРОНИРОВАНИЕ
# ============================================================

class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'participant',
        'masterclass_link',  # ссылка на мастер-класс
        'participants_count',
        'total_price_display',
        'status_badge',
        'payment_status_badge',
        'booking_date',
    ]
    list_display_links = ['id', 'participant']
    list_filter = [
        'status',
        'payment_status',
        ('booking_date', admin.DateFieldListFilter),
        'masterclass__category',
    ]
    date_hierarchy = 'booking_date'
    search_fields = ['participant__username', 'participant__email', 'masterclass__title']
    raw_id_fields = ['participant', 'masterclass']
    readonly_fields = ['total_price', 'booking_date', 'created_at']

    fieldsets = (
        ('Информация о бронировании', {
            'fields': ('participant', 'masterclass', 'participants_count')
        }),
        ('Статусы', {
            'fields': ('status', 'payment_status')
        }),
        ('Финансы', {
            'fields': ('total_price',)
        }),
        ('Даты', {
            'fields': ('booking_date', 'created_at')
        }),
    )

    @admin.display(description="МК")
    def masterclass_link(self, obj):
        """Кликабельная ссылка на мастер-класс"""
        from django.urls import reverse
        url = reverse('admin:%s_%s_change' % (obj.masterclass._meta.app_label, obj.masterclass._meta.model_name),
                      args=[obj.masterclass.id])
        return format_html('<a href="{}">{}</a>', url, obj.masterclass.title)

    @admin.display(description="Сумма")
    def total_price_display(self, obj):
        return f"{obj.total_price:,.0f} ₽".replace(',', ' ')

    @admin.display(description="Статус")
    def status_badge(self, obj):
        colors = {'pending': 'gray', 'confirmed': 'green', 'cancelled': 'red', 'completed': 'blue'}
        return format_html(
            '<span style="color:{};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )

    @admin.display(description="Оплата")
    def payment_status_badge(self, obj):
        colors = {'pending': 'orange', 'paid': 'green', 'refunded': 'purple'}
        return format_html(
            '<span style="color:{};">{}</span>',
            colors.get(obj.payment_status, 'black'),
            obj.get_payment_status_display()
        )


# ============================================================
# 8. ОТЗЫВ
# ============================================================

class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'author',
        'masterclass',
        'rating_stars',
        'text_preview',
        'status_badge',
        'created_at',
    ]
    list_display_links = ['id', 'author']
    list_filter = ['status', 'rating', ('created_at', admin.DateFieldListFilter)]
    date_hierarchy = 'created_at'
    search_fields = ['author__username', 'masterclass__title', 'text']
    raw_id_fields = ['author', 'masterclass', 'booking']
    readonly_fields = ['created_at']

    actions = ['approve_reviews', 'reject_reviews']

    fieldsets = (
        (None, {
            'fields': ('author', 'masterclass', 'booking')
        }),
        ('Содержание', {
            'fields': ('rating', 'text')
        }),
        ('Модерация', {
            'fields': ('status', 'created_at')
        }),
    )

    @admin.display(description="⭐ Оценка")
    def rating_stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)

    @admin.display(description="Текст")
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text

    @admin.display(description="Статус")
    def status_badge(self, obj):
        colors = {'pending': 'orange', 'approved': 'green', 'rejected': 'red'}
        return format_html(
            '<span style="color:{};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )

    @admin.action(description="✅ Одобрить выбранные отзывы")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"Одобрено отзывов: {updated}")

    @admin.action(description="❌ Отклонить выбранные отзывы")
    def reject_reviews(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"Отклонено отзывов: {updated}", level='WARNING')


# ============================================================
# 9. ИЗБРАННОЕ
# ============================================================

class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'masterclass', 'created_at']
    list_display_links = ['id', 'user']
    list_filter = ['created_at']
    search_fields = ['user__username', 'masterclass__title']
    raw_id_fields = ['user', 'masterclass']
    readonly_fields = ['created_at']


# ============================================================
# 10. УВЕДОМЛЕНИЕ
# ============================================================

class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'type_icon',
        'title',
        'is_read_badge',
        'created_at',
    ]
    list_display_links = ['id', 'title']
    list_filter = ['type', 'is_read', ('created_at', admin.DateFieldListFilter)]
    date_hierarchy = 'created_at'
    search_fields = ['user__username', 'title', 'message']
    raw_id_fields = ['user']
    readonly_fields = ['created_at']

    actions = ['mark_as_read', 'mark_as_unread']

    @admin.display(description="Тип")
    def type_icon(self, obj):
        icons = {
            'booking_confirmed': '✅',
            'booking_cancelled': '❌',
            'moderation_result': '📋',
            'new_booking': '🆕',
            'reminder': '⏰',
        }
        return f"{icons.get(obj.type, '📌')} {obj.get_type_display()}"

    @admin.display(description="Прочитано")
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:green;">✅ Да</span>')
        return format_html('<span style="color:red;">📌 Нет</span>')

    @admin.action(description="✅ Отметить как прочитанные")
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"Отмечено прочитанными: {updated}")

    @admin.action(description="📌 Отметить как непрочитанные")
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"Отмечено непрочитанными: {updated}")




# ============================================================
# РЕГИСТРАЦИЯ ВСЕХ МОДЕЛЕЙ
# ============================================================

admin.site.register(User, UserAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(MasterClass, MasterClassAdmin)
admin.site.register(Image)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Notification, NotificationAdmin)
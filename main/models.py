from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse

class ApprovedMasterClassManager(models.Manager):
    """Менеджер для получения только одобренных и предстоящих мастер-классов"""

    def get_queryset(self):
        return super().get_queryset().filter(
            status='approved',
            start_datetime__gte=timezone.now()  # ← ДЕМОНСТРАЦИЯ __ (lookup) и timezone
        )

    def by_category(self, category_slug):
        """Метод менеджера: фильтр по категории"""
        return self.filter(category__slug=category_slug)  # ← ДЕМОНСТРАЦИЯ __ (связанная таблица)

    def popular(self, limit=5):
        """Популярные МК (по количеству бронирований)"""
        return self.annotate(
            booking_count=models.Count('bookings')
        ).order_by('-booking_count')[:limit]


# ============================================================
# 1. ПОЛЬЗОВАТЕЛЬ (расширенная модель пользователя Django)
# ============================================================

class User(AbstractUser):
    """Модель пользователя с ролями Участник/Организатор/Администратор"""

    ROLE_CHOICES = [
        ('participant', 'Участник'),
        ('organizer', 'Организатор'),
        ('admin', 'Администратор'),
    ]

    email = models.EmailField(unique=True, verbose_name="Email (логин)")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant', verbose_name="Роль")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")
    is_active = models.BooleanField(default=True, verbose_name="Активен (не заблокирован)")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    last_login = models.DateTimeField(blank=True, null=True, verbose_name="Последний вход")

    # Дополнительные поля для организатора
    organization_name = models.CharField(max_length=200, blank=True, verbose_name="Название студии/организации")
    organization_description = models.TextField(blank=True, verbose_name="Описание студии")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        swappable = 'AUTH_USER_MODEL'  # 👈 ЭТА СТРОКА ВАЖНА! Указывает, что это кастомная модель

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_organizer(self):
        return self.role == 'organizer'

    @property
    def is_participant(self):
        return self.role == 'participant'


# ============================================================
# 2. КАТЕГОРИЯ
# ============================================================

class Category(models.Model):
    """Категория мастер-классов (Кулинария, Творчество и т.д.)"""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-имя")
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Изображение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """← ДЕМОНСТРАЦИЯ get_absolute_url и reverse"""
        return reverse('category_detail', kwargs={'slug': self.slug})


# ============================================================
# 3. МАСТЕР-КЛАСС
# ============================================================

class MasterClass(models.Model):
    """Мастер-класс (мероприятие)"""

    FORMAT_CHOICES = [
        ('online', 'Онлайн'),
        ('offline', 'Офлайн'),
    ]

    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='masterclasses',
                                 verbose_name="Категория")
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='masterclasses',
                                  limit_choices_to={'role': 'organizer'}, verbose_name="Организатор")

    city = models.CharField(max_length=100, verbose_name="Город")
    address = models.CharField(max_length=255, blank=True, verbose_name="Адрес")
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='offline', verbose_name="Формат")

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                verbose_name="Цена (руб)")
    max_participants = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                                   verbose_name="Максимум участников")
    current_participants = models.PositiveIntegerField(default=0, verbose_name="Текущее количество записавшихся")

    start_datetime = models.DateTimeField(verbose_name="Дата и время начала")
    end_datetime = models.DateTimeField(verbose_name="Дата и время окончания")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    moderation_comment = models.TextField(blank=True, verbose_name="Комментарий модератора")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    online_link = models.URLField(
        blank=True,
        null=True,
        verbose_name="Ссылка на трансляцию"
    )

    objects = models.Manager()  # стандартный менеджер
    approved_objects = ApprovedMasterClassManager()

    # ManyToMany через Booking (уже существующую модель)
    participants = models.ManyToManyField(
        User,
        through='Booking',
        through_fields=('masterclass', 'participant'),
        related_name='joined_masterclasses',
        verbose_name="Участники"
    )

    class Meta:
        verbose_name = "Мастер-класс"
        verbose_name_plural = "Мастер-классы"
        ordering = ['-start_datetime']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['start_datetime']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.city} ({self.start_datetime.strftime('%d.%m.%Y')})"

    @property
    def is_upcoming(self):
        """Проверка, что мероприятие еще не началось"""
        return self.start_datetime > timezone.now()

    @property
    def has_free_places(self):
        """Есть ли свободные места"""
        return self.current_participants < self.max_participants

    @property
    def free_places(self):
        """Количество свободных мест"""
        return self.max_participants - self.current_participants

    def get_absolute_url(self):
        """← ДЕМОНСТРАЦИЯ get_absolute_url и reverse"""
        return reverse('masterclass_detail', kwargs={'pk': self.pk})

    # ДОБАВЬТЕ ЭТОТ МЕТОД:
    def is_full(self):
        """Проверка заполненности"""
        return self.current_participants >= self.max_participants


# ============================================================
# 4. ИЗОБРАЖЕНИЕ
# ============================================================

class Image(models.Model):
    """Изображения для мастер-класса"""

    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='images',
                                    verbose_name="Мастер-класс")
    image = models.ImageField(upload_to='masterclasses/', verbose_name="Изображение")
    is_main = models.BooleanField(default=False, verbose_name="Главное фото")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"

    def __str__(self):
        return f"Фото для {self.masterclass.title}"


# ============================================================
# 5. БРОНИРОВАНИЕ
# ============================================================

class Booking(models.Model):
    """Бронирование места на мастер-класс"""

    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
        ('completed', 'Завершено'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('refunded', 'Возврат'),
    ]

    participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings',
                                    limit_choices_to={'role': 'participant'}, verbose_name="Участник")
    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='bookings',
                                    verbose_name="Мастер-класс")
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата бронирования")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending',
                                      verbose_name="Статус оплаты")
    participants_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)],
                                                     verbose_name="Количество мест")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент бронирования")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ['-created_at']
        unique_together = ['participant', 'masterclass']  # Запрет повторной записи на одно мероприятие

    def __str__(self):
        return f"{self.participant.get_full_name()} → {self.masterclass.title}"

    def save(self, *args, **kwargs):
        # Автоматически считаем общую цену
        if not self.total_price:
            self.total_price = self.masterclass.price * self.participants_count

        # При подтверждении бронирования увеличиваем счётчик участников
        if self.pk is None and self.status == 'confirmed':
            self.masterclass.current_participants += self.participants_count
            self.masterclass.save()

        super().save(*args, **kwargs)


# ============================================================
# 6. ОТЗЫВ
# ============================================================

class Review(models.Model):
    """Отзыв на мастер-класс"""

    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name="Автор")
    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='reviews',
                                    verbose_name="Мастер-класс")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review',
                                   verbose_name="Бронирование")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
                                              verbose_name="Оценка (1-5)")
    text = models.TextField(verbose_name="Текст отзыва")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв от {self.author.get_full_name()} на {self.masterclass.title} (оценка: {self.rating})"


# ============================================================
# 7. ИЗБРАННОЕ
# ============================================================

class Favorite(models.Model):
    """Избранные мастер-классы пользователя"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name="Пользователь")
    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='favorited_by',
                                    verbose_name="Мастер-класс")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        unique_together = ['user', 'masterclass']  # Нельзя добавить одно и то же дважды

    def __str__(self):
        return f"{self.user.get_full_name()} → {self.masterclass.title}"


# ============================================================
# 8. УВЕДОМЛЕНИЕ
# ============================================================

class Notification(models.Model):
    """Уведомления пользователей"""

    TYPE_CHOICES = [
        ('booking_confirmed', 'Бронирование подтверждено'),
        ('booking_cancelled', 'Бронирование отменено'),
        ('moderation_result', 'Результат модерации'),
        ('new_booking', 'Новое бронирование'),
        ('reminder', 'Напоминание'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Пользователь")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Тип")
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Текст")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} для {self.user.get_full_name()}"



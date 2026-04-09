from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import EmailValidator
from .models import User
from .models import MasterClass, Category, Review


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@gmail.com',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #FFD1DC; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    username = forms.CharField(
        label="Имя пользователя",
        widget=forms.TextInput(attrs={
            'placeholder': 'username',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #FFD1DC; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Не менее 8 символов',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #FFD1DC; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите пароль',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #FFD1DC; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    # ===== ВЫБОР РОЛИ =====
    role = forms.ChoiceField(
        choices=[('participant', 'Участник'), ('organizer', 'Организатор')],
        label="Я хочу",
        widget=forms.Select(attrs={
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #FFD1DC; border-radius: 12px; font-family: "Jost", sans-serif; background: white;'
        }),
        initial='participant'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']  # ← сохраняем выбранную роль
        if commit:
            user.save()
        return user


class MasterClassForm(forms.ModelForm):
    class Meta:
        model = MasterClass
        fields = ['title', 'description', 'category', 'city', 'address',
                  'format', 'price', 'max_participants', 'start_datetime', 'end_datetime']

        # ===== Meta widgets =====
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название мастер-класса'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробное описание'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Город'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Адрес'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 100
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'max_participants': 'Максимум участников',
        }


    # ===== clean_<fieldname>() =====
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price < 100:
            raise forms.ValidationError("Цена не может быть меньше 100 ₽")
        return price

    def clean_max_participants(self):
        max_parts = self.cleaned_data.get('max_participants')
        if max_parts and max_parts < 2:
            raise forms.ValidationError("Минимум 2 участника")
        return max_parts

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_datetime')
        end = cleaned_data.get('end_datetime')

        if start and end and start >= end:
            raise forms.ValidationError("Дата окончания должна быть позже даты начала")

        return cleaned_data

    # ===== save с commit=True =====
    def save(self, commit=True):
        instance = super().save(commit=False)

        # Дополнительная логика перед сохранением
        if not instance.pk:  # новый объект
            instance.status = 'pending'  # на модерацию

        if commit:
            instance.save()
            self.save_m2m()  # сохраняем many-to-many связи если есть

        return instance


# ===== ФОРМА ДЛЯ ОТЗЫВА =====
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(choices=[(i, f"{'★' * i}") for i in range(1, 6)], attrs={
                'class': 'form-control'
            }),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ваш отзыв...'
            }),
        }

    def clean_text(self):
        text = self.cleaned_data.get('text')
        if len(text) < 10:
            raise forms.ValidationError("Отзыв должен содержать минимум 10 символов")
        return text

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status = 'pending'  # на модерацию

        if commit:
            instance.save()

        return instance
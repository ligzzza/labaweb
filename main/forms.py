from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import EmailValidator
from .models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        validators=[EmailValidator(message="Введите корректный email адрес")],
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@gmail.com',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #ddd; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    username = forms.CharField(
        label="Имя пользователя",
        widget=forms.TextInput(attrs={
            'placeholder': 'username',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #ddd; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Не менее 8 символов',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #ddd; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите пароль',
            'style': 'width: 100%; padding: 0.8rem; border: 1px solid #ddd; border-radius: 12px; font-family: "Jost", sans-serif;'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Проверяем, что email не занят
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = 'participant'
        if commit:
            user.save()
        return user
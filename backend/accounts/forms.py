from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    """Django 기본 User + 이메일 입력."""

    email = forms.EmailField(required=False, label="이메일")

    class Meta:
        model = User
        fields = ("username", "email")

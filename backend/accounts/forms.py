from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label="Пароль", strip=False, widget=forms.PasswordInput, min_length=8
    )

    class Meta:
        model = User
        fields = ["username"]

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""
        password_validation.validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


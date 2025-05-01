# interview/forms.py

from django import forms
from .models import UserAccount

class UserAccountForm(forms.ModelForm):
    class Meta:
        model = UserAccount
        fields = ['full_name', 'email', 'password']  # Adjust as needed
        widgets = {
            'password': forms.PasswordInput(),  # To hide password input
        }

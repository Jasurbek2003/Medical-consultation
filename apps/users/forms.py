from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """User registration form"""
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ('phone', 'first_name', 'last_name', 'email', 'password1', 'password2')


class UserLoginForm(forms.Form):
    """User login form"""
    phone = forms.CharField(max_length=13)
    password = forms.CharField(widget=forms.PasswordInput)


class UserProfileForm(forms.ModelForm):
    """User profile edit form"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'birth_date', 'gender',
            'blood_type', 'height', 'weight', 'region', 'district',
            'address', 'avatar', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relation'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
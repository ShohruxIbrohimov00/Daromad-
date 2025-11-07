from django import forms
from .models import Transaction, Category, RecurringSchedule
from django.db import models
from django.db.models import Q
# Sanani tekshirish uchun kerakli modullarni import qilish
from django.utils import timezone
import datetime 
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from .models import CustomUser
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import re

# Tailwind CSS klasslarini form maydonlariga qo'shish uchun bazaviy klass
TAILWIND_INPUT_CLASS = "mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
TAILWIND_INPUT="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"


# === 1. USER UPDATE (Ism, Familiya, Telefon) ===
class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Ism",
        widget=forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Ali'})
    )
    last_name = forms.CharField(
        label="Familiya",
        widget=forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Valiyev'})
    )
    phone = forms.CharField(
        label="Telefon",
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full',
            'placeholder': '+998901234567',
            'inputmode': 'tel'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            if not phone.startswith('+998'):
                raise ValidationError("Telefon +998 bilan boshlanishi kerak.")
            if len(phone) != 13:
                raise ValidationError("Telefon formati: +998901234567")
            if CustomUser.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
                raise ValidationError("Bu telefon allaqachon ishlatilgan.")
        return phone

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Foydalanuvchi nomi",
        widget=forms.TextInput(attrs={'class': 'form-input w-full'})
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={'class': 'form-input w-full'})
    )

class CustomRegisterForm(UserCreationForm):
    first_name = forms.CharField(
        label=_("Ism"),
        widget=forms.TextInput(attrs={'placeholder': 'Ali'})
    )
    last_name = forms.CharField(
        label=_("Familiya"),
        widget=forms.TextInput(attrs={'placeholder': 'Valiyev'})
    )
    phone = forms.CharField(
        label=_("Telefon"),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+998901234567'}),
        validators=[
            RegexValidator(
                regex=r'^\+998\d{9}$',
                message=_("Telefon raqam formati: +998901234567 bo‘lishi kerak"),
                code='invalid_phone'
            )
        ]
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'phone', 'password1', 'password2']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            # Format validator bilan oldin tekshirildi, endi unikal bo‘lishi tekshirilsin
            qs = CustomUser.objects.filter(phone=phone)
            if qs.exists():
                raise forms.ValidationError(_("Bu telefon raqam allaqachon ro‘yxatdan o‘tgan."), code='unique')
        return phone

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise forms.ValidationError(_("Ism kiritish majburiy."), code='required')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise forms.ValidationError(_("Familiya kiritish majburiy."), code='required')
        return last_name

class TransactionForm(forms.ModelForm):
    """
    Yangi Daromad yoki Xarajatni kiritish uchun ModelForm.
    """
    transaction_type = forms.CharField(widget=forms.HiddenInput(), initial='EXPENSE', required=False)

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        widget=forms.HiddenInput(),
        required=True
    )


    class Meta:
        model = Transaction
        fields = ['amount', 'category', 'date', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'w-full text-4xl font-extrabold text-center border-none focus:ring-0 placeholder-gray-300',
                'placeholder': '0.00'
            }),
            'date': forms.DateInput(attrs={
                'class': TAILWIND_INPUT_CLASS + " text-lg", # Katta shrift uchun o'zgartirish
                'type': 'date' 
            }),
            'description': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Qisqa izoh...'
            }),
        }

    def __init__(self, *args, user=None, transaction_type='EXPENSE', **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['transaction_type'].initial = transaction_type.upper()
        
        if user:
            # Kategoriyalarni filtrlash: faqat joriy foydalanuvchi yoki global (user=None) kategoriyalar
            self.fields['category'].queryset = Category.objects.filter(
                models.Q(user=user) | models.Q(user__isnull=True),
                is_active=True
            )

    # 🔥 ASOSIY TUZATISH LOGIKASI: Sanaga cheklovni olib tashlash yoki o'zgartirish
    def clean_date(self):
        """
        Sana maydoni uchun maxsus validatsiya. 
        Agar tizimingizda kelajak sanasiga cheklov bo'lsa, u shu yerda bo'ladi.
        """
        date = self.cleaned_data.get('date')

        if date:
            # Bugungi sanani olish (faqat sanani)
            today = timezone.localdate() 
            
            # Agar siz KELAJAK SANASIGA RUXSAT BERMOQCHI BO'LSANGIZ:
            # Hech qanday cheklov qo'ymang. Agar bu qism muammoni hal qilsa, demak cheklov bo'lgan.
            # Shuning uchun bu yerga faqat sanani qaytarishni qoldiramiz.

            # Agar siz faqat o'tmish sanalariga ruxsat bermoqchi bo'lsangiz, bu yerda cheklashingiz mumkin:
            # if date > today:
            #     raise forms.ValidationError("Kelajak sanasini kiritish mumkin emas.")
            
            # Biz hech qanday cheklov qo'ymaymiz.
            pass
            
        return date

class RecurringScheduleForm(forms.ModelForm):
    class Meta:
        model = RecurringSchedule
        fields = ['category', 'amount', 'day_of_month', 'start_date', 'end_date', 'note']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
            }),
            'note': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200',
                'placeholder': 'Masalan: Oylik ijara...'
            }),
        }

    # amount — input text, lekin Decimal bo‘ladi
    amount = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'hidden',  # Biz HTML da o‘zimiz chiqaramiz
            'inputmode': 'numeric'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True),
                is_active=True
            ).select_related('parent').order_by('type', 'name')

        self.fields['day_of_month'] = forms.IntegerField(
            min_value=1,
            max_value=30,
            initial=1,
            widget=forms.NumberInput(attrs={'class': 'hidden'})
        )

    def clean_amount(self):
        value = self.cleaned_data.get('amount', '').strip()
        if not value:
            raise ValidationError("Miqdor kiritilishi shart.")
        
        # Bo‘sh joylarni olib tashlash
        value = value.replace(' ', '')
        
        try:
            decimal_value = Decimal(value)
            if decimal_value <= 0:
                raise ValidationError("Miqdor musbat bo‘lishi kerak.")
            return decimal_value
        except (InvalidOperation, ValueError):
            raise ValidationError("Noto‘g‘ri miqdor formati.")
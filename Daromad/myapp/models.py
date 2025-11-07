# finances/models.py — TO‘LIQ TUZATILGAN VERSIYA

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime


class CustomUser(AbstractUser):
    """Foydalanuvchi uchun kengaytirilgan model"""
    first_name = models.CharField(_("Ism"), max_length=150, blank=False)
    last_name = models.CharField(_("Familiya"), max_length=150, blank=False)
    phone = models.CharField(
        _("Telefon raqam"),
        max_length=15,
        blank=True,
        null=True,
        unique=True,
        help_text=_("Masalan: +998901234567")
    )

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        constraints = [
            models.CheckConstraint(
                check=models.Q(phone__regex=r'^\+998\d{9}$') | models.Q(phone=''),
                name='valid_phone_format'
            )
        ]

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


# === 2. USER MODEL (endi xavfsiz) ===
User = get_user_model()


# === 3. TYPE CHOICES ===
TYPE_CHOICES = (
    ('INCOME', 'Daromad'),
    ('EXPENSE', 'Xarajat'),
)


# === 4. CATEGORY ===
class Category(models.Model):
    user = models.ForeignKey(
        User,  # Bu yerda User emas, get_user_model()
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True,
        verbose_name=_("Foydalanuvchi"),
        help_text=_("Bo'sh bo'lsa — global kategoriya.")
    )
    name = models.CharField(max_length=100, verbose_name=_("Nomi"))
    type = models.CharField(max_length=7, choices=TYPE_CHOICES, verbose_name=_("Turi"))
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='subcategories',
        null=True,
        blank=True,
        verbose_name=_("Yuqori Kategoriya")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Kategoriya")
        verbose_name_plural = _("Kategoriyalar")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name', 'type', 'parent'],
                name='unique_category_user_name_type_parent'
            )
        ]
        ordering = ['type', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name} ({self.get_type_display()})"
        return f"{self.name} ({self.get_type_display()})"

    def clean(self):
        if not self.name.strip():
            raise ValidationError({'name': _('Kategoriya nomi bo\'sh bo\'lishi mumkin emas.')})
        if self.parent:
            if self.parent.type != self.type:
                raise ValidationError({'parent': _('Yuqori kategoriya turi bilan mos kelishi kerak.')})
            if self.parent.user and self.user != self.parent.user:
                raise ValidationError({'parent': _('Yuqori va pastki kategoriya bir foydalanuvchiga tegishli bo\'lishi kerak.')})
            if self.parent.user and not self.user:
                raise ValidationError({'user': _('Agar yuqori kategoriya foydalanuvchiga tegishli bo\'lsa, pastki ham shunday bo\'lishi kerak.')})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# === 5. RECURRING SCHEDULE ===
class RecurringSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_schedules')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='recurring_schedules')
    amount = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Miqdor (UZS)"))
    day_of_month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name=_("Har oyning kuni")
    )
    start_date = models.DateField(default=timezone.now, verbose_name=_("Boshlanish"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("Tugash"))
    last_executed = models.DateField(null=True, blank=True, verbose_name=_("Oxirgi bajarilgan"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    note = models.TextField(blank=True, verbose_name=_("Izoh"))

    class Meta:
        verbose_name = _("Takrorlanuvchi jadval")
        verbose_name_plural = _("Takrorlanuvchi jadvalar")
        ordering = ['day_of_month', '-is_active']

    def __str__(self):
        status = "Faol" if self.is_active else "To'xtatilgan"
        return f"{self.category} — {self.amount:,} UZS — {self.day_of_month}-kun [{status}]"


# === 6. TRANSACTION ===
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Miqdor (UZS)"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    date = models.DateField(default=timezone.now, verbose_name=_("Sana"))
    description = models.TextField(blank=True, verbose_name=_("Izoh"))
    recurring_schedule = models.ForeignKey(RecurringSchedule, on_delete=models.SET_NULL, null=True, blank=True)
    is_automated = models.BooleanField(default=False, verbose_name=_("Avtomatik"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Tranzaksiya")
        verbose_name_plural = _("Tranzaksiyalar")
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['user', 'date']), models.Index(fields=['category'])]

    def __str__(self):
        cat = self.category.get_full_path() if self.category else "Kategoriyasiz"
        auto = " [Avto]" if self.is_automated else ""
        return f"{self.date} | {self.amount:,} UZS | {cat}{auto}"


# === 7. BUDGET ===
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        limit_choices_to={'type': 'EXPENSE'},
        related_name='budgets'
    )
    amount = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Budjet (UZS)"))
    month = models.DateField(verbose_name=_("Oy (1-kun)"), help_text=_("Masalan: 2025-11-01"))
    warning_threshold = models.PositiveSmallIntegerField(default=80, verbose_name=_("Ogohlantirish (%)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))

    class Meta:
        verbose_name = _("Budjet")
        verbose_name_plural = _("Budjetlar")
        constraints = [models.UniqueConstraint(fields=['user', 'category', 'month'], name='unique_budget_per_month')]
        ordering = ['-month']

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} | {self.category} | {self.amount:,} UZS"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({'amount': _('Budjet musbat bo\'lishi kerak.')})
        if not (1 <= self.warning_threshold <= 100):
            raise ValidationError({'warning_threshold': _('1 dan 100 gacha.')})
        if self.month.day != 1:
            self.month = self.month.replace(day=1)

    def save(self, *args, **kwargs):
        if self.month.day != 1:
            self.month = self.month.replace(day=1)
        super().save(*args, **kwargs)

    def spent_amount(self):
        start = self.month
        end = (self.month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        total = self.category.transactions.filter(
            user=self.user,
            date__gte=start,
            date__lte=end
        ).aggregate(total=models.Sum('amount'))['total']
        return total or 0

    def spent_percentage(self):
        return round((self.spent_amount() / self.amount) * 100, 2) if self.amount > 0 else 0
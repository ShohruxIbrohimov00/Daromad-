# myapp/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import (
    CustomUser, Category, RecurringSchedule,
    Transaction, Budget
)


class SubCategoryInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 0
    fields = ('name', 'type', 'is_active')
    show_change_link = True


# === 2. CUSTOM USER ADMIN ===
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Shaxsiy ma’lumotlar'), {'fields': ('first_name', 'last_name')}),
        (_('Ruxsatlar'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Muhim sanalar'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


# === 3. CATEGORY ADMIN ===
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'user', 'parent', 'is_active', 'created_at')
    list_filter = ('type', 'is_active', 'user', 'created_at')
    search_fields = ('name', 'user__username')
    list_editable = ('is_active',)
    inlines = [SubCategoryInline]
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'type', 'parent', 'is_active')
        }),
        (_('Sanalar'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Category.objects.filter(user=request.user) if not request.user.is_superuser else Category.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# === 4. RECURRING SCHEDULE ADMIN ===
@admin.register(RecurringSchedule)
class RecurringScheduleAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'day_of_month', 'user', 'start_date', 'end_date', 'is_active', 'last_executed')
    list_filter = ('is_active', 'day_of_month', 'category__type', 'user', 'start_date')
    search_fields = ('category__name', 'note', 'user__username')
    list_editable = ('is_active',)
    readonly_fields = ('last_executed',)
    date_hierarchy = 'start_date'
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('user', 'category', 'amount', 'day_of_month')
        }),
        (_('Sanalar'), {
            'fields': ('start_date', 'end_date', 'last_executed')
        }),
        (_("Qo'shimcha"), {
            'fields': ('is_active', 'note'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    actions = ['mark_active', 'mark_inactive']

    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} ta yozuv faollashtirildi.")
    mark_active.short_description = _("Tanlanganlarni faollashtirish")

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} ta yozuv to‘xtatildi.")
    mark_inactive.short_description = _("Tanlanganlarni to‘xtatish")


# === 5. TRANSACTION ADMIN ===
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'category', 'user', 'is_automated', 'created_at')
    list_filter = ('is_automated', 'category__type', 'date', 'user')
    search_fields = ('description', 'category__name', 'user__username')
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'
    list_select_related = ('category', 'user', 'recurring_schedule')
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('user', 'amount', 'category', 'date', 'description')
        }),
        (_('Avtomatlashtirish'), {
            'fields': ('recurring_schedule', 'is_automated'),
            'classes': ('collapse',)
        }),
        (_('Sana'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# === 6. BUDGET ADMIN ===
@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('month', 'category', 'amount', 'spent_amount', 'spent_percentage', 'warning_threshold', 'is_active')
    list_filter = ('is_active', 'month', 'category__type', 'user')
    search_fields = ('category__name', 'user__username')
    list_editable = ('is_active',)
    readonly_fields = ('spent_amount', 'spent_percentage')
    date_hierarchy = 'month'
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('user', 'category', 'amount', 'month', 'warning_threshold')
        }),
        (_('Holati'), {
            'fields': ('spent_amount', 'spent_percentage', 'is_active')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def spent_amount(self, obj):
        return f"{obj.spent_amount():,.0f} so‘m"
    spent_amount.short_description = _("Sarflangan")

    def spent_percentage(self, obj):
        percent = obj.spent_percentage()
        color = "green" if percent < obj.warning_threshold else "red"
        return format_html(f'<span style="color: {color}; font-weight: bold;">{percent}%</span>')
    spent_percentage.short_description = _("Foiz")

    def changelist_view(self, request, extra_context=None):
        # Har bir budget uchun spent_amount hisoblash
        response = super().changelist_view(request, extra_context)
        if hasattr(response, 'context_data'):
            response.context_data['summary'] = []
        return response
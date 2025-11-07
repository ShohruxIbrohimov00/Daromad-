# myapp/views.py (yoki finances/views.py)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum,Min,Max
from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.serializers.json import DjangoJSONEncoder
from .models import *
from .forms import *
from django.utils.html import escape 
from django.utils.safestring import mark_safe 
import json
from django.db.models import Q
from django.db import models
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.urls import reverse 
from django.views.decorators.http import require_POST, require_http_methods
from django.template.loader import render_to_string
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomLoginForm, CustomRegisterForm
from django.utils import timezone
from .forms import UserUpdateForm
from django.db import IntegrityError


# === 1. LOGIN ===
def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request,
                f"Xush kelibsiz, {user.get_full_name() or user.username}!"
            )
            # next parametrini xavfsiz ishlatish
            next_page = request.GET.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect('dashboard')
        else:
            messages.error(request, "Login yoki parol noto‘g‘ri.")
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form})


def user_register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, "Hisob muvaffaqiyatli yaratildi! Endi kirishingiz mumkin.")
                return redirect('login')
            except IntegrityError as e:
                messages.error(request, f"Maʼlumotlarni saqlashda xatolik: {e}")
        else:
            # Field xatolar va umumiy xatolar to‘g‘ri ko‘rsatilsin
            for field, errors in form.errors.items():
                for error in errors:
                    if field == "__all__":
                        messages.error(request, error)
                    else:
                        # Formda field label bo‘ladi, labeldan foydalanamiz
                        label = form.fields[field].label if field in form.fields else field
                        messages.error(request, f"{label}: {error}")
    else:
        form = CustomRegisterForm()
    
    return render(request, 'register.html', {'form': form})

# === 3. LOGOUT ===
def user_logout(request):
    logout(request)
    messages.info(request, "Muvaffaqiyatli chiqdingiz.")
    return redirect('login')


# === 1. PROFIL KO‘RISH (faqat ko‘rish, yuklash yo‘q!) ===
@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Ma'lumotlar muvaffaqiyatli yangilandi!")
            return redirect('profile')
        else:
            messages.error(request, "Xatolik yuz berdi.")
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'profile_update.html', {
        'form': form
    })

@login_required
def profile_view(request):
    return render(request, 'profile.html', {
        'user': request.user
    })

@login_required
def dashboard_view(request, year=None, month=None):
    # --- Davrni Aniqlash Mantiqi ---
    today = date.today()
    
    if year is None or month is None:
        report_date = today
    else:
        try:
            report_date = date(int(year), int(month), 1)
        except ValueError:
            report_date = today

    # Hisobot Oyining Boshlanishi
    start_of_month = report_date.replace(day=1)
    
    # Joriy oyni aniqlash
    is_current_month = report_date.year == today.year and report_date.month == today.month
    
    if is_current_month:
        end_date = today  # Joriy oyning bugungi kunigacha
    else:
        end_date = start_of_month + relativedelta(months=1) - relativedelta(days=1)

    # --- Flatpickr uchun chegaralar ---
    date_bounds = Transaction.objects.filter(user=request.user).aggregate(
        min_date=Min('date'), 
        max_date=Max('date')
    )
    min_available_date = date_bounds['min_date']
    max_available_date = date_bounds['max_date']

    # --- Joriy davr tranzaksiyalari ---
    current_period_transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=start_of_month, 
        date__lte=end_date
    ).select_related('category', 'category__parent')

    # --- Moliyaviy hisob-kitoblar ---
    total_income = current_period_transactions.filter(category__type='INCOME').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = current_period_transactions.filter(category__type='EXPENSE').aggregate(total=Sum('amount'))['total'] or 0
    total_net_balance = total_income - total_expense

    # --- O‘tgan oy bilan solishtirish uchun balans ---
    prev_month_start = start_of_month - relativedelta(months=1)
    prev_month_end = start_of_month - relativedelta(days=1)

    prev_income = Transaction.objects.filter(
        user=request.user,
        date__gte=prev_month_start,
        date__lte=prev_month_end,
        category__type='INCOME'
    ).aggregate(total=Sum('amount'))['total'] or 0

    prev_expense = Transaction.objects.filter(
        user=request.user,
        date__gte=prev_month_start,
        date__lte=prev_month_end,
        category__type='EXPENSE'
    ).aggregate(total=Sum('amount'))['total'] or 0

    prev_net_balance = prev_income - prev_expense
    balance_change = total_net_balance - prev_net_balance  # + yoki -

    # --- Eng ko‘p xarajat kategoriyalari (kompyuter uchun) ---
    top_expense_categories = Category.objects.filter(
        user=request.user,
        type='EXPENSE',  # Category turi
        transactions__user=request.user,
        transactions__date__gte=start_of_month,
        transactions__date__lte=end_date
    ).annotate(
        total=Sum('transactions__amount')
    ).order_by('-total')[:5]

    # --- So‘nggi tranzaksiyalar (kompyuter uchun) ---
    recent_transactions = current_period_transactions.order_by('-date', '-created_at')[:5]

    # --- Barcha tranzaksiyalar (ro‘yxat uchun) ---
    all_transactions_list = current_period_transactions.order_by('-date', '-created_at')

    # --- Kontekst ---
    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'total_net_balance': total_net_balance,
        'balance_change': balance_change,  # YANGI

        'top_expense_categories': top_expense_categories,  # YANGI
        'recent_transactions': recent_transactions,        # YANGI

        'all_transactions': all_transactions_list,

        # Davr ma'lumotlari
        'report_date_start': start_of_month,
        'report_date_end': end_date,
        'is_current_month': is_current_month,
        'current_year': report_date.year,
        'current_month': report_date.month,

        # Flatpickr uchun
        'min_available_date': min_available_date.strftime('%Y-%m-%d') if min_available_date else None,
        'max_available_date': max_available_date.strftime('%Y-%m-%d') if max_available_date else None,

        'month_names_uz': {
            1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
            5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
            9: 'Sentabr', 10: 'Oktyabr', 11: 'Noyabr', 12: 'Dekabr'
        },
    }

    return render(request, 'dashboard.html', context)


@login_required
def get_transactions_list_partial(request):
    """AJAX so'rovlari uchun filtrlangan tranzaksiya ro'yxati qismini qaytaradi."""
    
    # 1. Parametrlarni olish
    filter_type = request.GET.get('type', 'ALL')
    year_str = request.GET.get('year')
    month_str = request.GET.get('month')

    # 2. year va month ni int ga aylantirish
    try:
        year = int(year_str)
        month = int(month_str)
    except (TypeError, ValueError):
        return HttpResponse("<p class='p-4 text-center text-red-500'>Noto‘g‘ri sana.</p>")

    # 3. Davrni aniqlash
    try:
        report_date = date(year, month, 1)
    except ValueError:
        return HttpResponse("<p class='p-4 text-center text-red-500'>Noto‘g‘ri oy.</p>")

    start_of_month = report_date.replace(day=1)
    end_of_month = start_of_month + relativedelta(months=1) - relativedelta(days=1)

    # 4. Tranzaksiyalarni filtrash
    transactions_qs = Transaction.objects.filter(
        user=request.user,
        date__gte=start_of_month,
        date__lte=end_of_month
    )

    # 5. INCOME / EXPENSE filtri
    if filter_type in ['INCOME', 'EXPENSE']:
        transactions_qs = transactions_qs.filter(category__type=filter_type)

    # 6. Optimallashtirish
    transactions_qs = transactions_qs.select_related(
        'category', 'category__parent'
    ).order_by('-date', '-created_at')

    # 7. HTML qaytarish
    html = render_to_string(
        'partials/transaction_list.html',
        {'all_transactions': transactions_qs},
        request=request
    )
    return HttpResponse(html)

# categories_json xatoga uchrayotganligi sababli, bu funksiyani eng xavfsiz usulda o'zgartiramiz
def get_categories_for_js(user):
    """
    Kategoriyalarni eng xavfsiz JSON formatida tayyorlaydi.
    """
    categories_queryset = Category.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True),
        is_active=True
    ).order_by('type', 'parent__id', 'name')

    # ... ICON_MAP bu yerda bo'ladi ...
    ICON_MAP = {
        'Oziq-ovqat': 'fas fa-shopping-basket', 'Uy-joy / Ijara': 'fas fa-home',
        'Transport': 'fas fa-car', 'Ko\'ngilochar': 'fas fa-film', 
        'Kommunal to\'lovlar': 'fas fa-lightbulb', 'Ta\'lim': 'fas fa-graduation-cap',
        'Restoran / Kafe': 'fas fa-utensils', 'Sog\'liqni Saqlash': 'fas fa-hospital',
        'Maosh / Oylik': 'fas fa-briefcase', 'Freelance': 'fas fa-laptop-code',
        'Ijara Daromadi': 'fas fa-house-user', 'Dividenda / Foiz': 'fas fa-chart-line',
        'Sovg\'a / Mukofot': 'fas fa-gift',
        'default_expense': 'fas fa-minus-circle',
        'default_income': 'fas fa-plus-circle',
    }
    # ...

    categories_list = []
    for cat in categories_queryset:
        icon_name = ICON_MAP.get(cat.name, ICON_MAP.get('default_expense' if cat.type == 'EXPENSE' else 'default_income'))
        
        categories_list.append({
            'id': cat.id,
            # Nomni qochirish: Apostroflarni JSON ichida qochirishimiz kerak bo'lishi mumkin
            'name': cat.name, 
            'type': cat.type,
            'icon': icon_name, 
            'parent_id': cat.parent.id if cat.parent else None,
        })
    
    # JSON stringga aylantirish. ensure_ascii=False o'zbekcha harflarni to'g'ri kodlaydi.
    # Bu qismni o'zgarishsiz qoldiramiz, chunki muammo keyingi qadamda
    return json.dumps(categories_list, cls=DjangoJSONEncoder, ensure_ascii=False)

# --- ASOSIY VIEW FUNKSIYASINI TUZATISH ---
@login_required
def add_transaction_view(request):
    transaction_type = request.POST.get('transaction_type', request.GET.get('type', 'EXPENSE'))

    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user, transaction_type=transaction_type)
        
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('dashboard') 
        else:
            # Agar form xato bo'lsa, uni kontekstga qaytarish
            pass

    else:
        form = TransactionForm(user=request.user, transaction_type=transaction_type)
        
    
    # 1. Kategoriyalarni JSON formatida olish
    categories_json_raw = get_categories_for_js(request.user)

    # 2. ENG ISHONCHLI QOCHIRISH (FINAL FIX):
    # 'Unterminated string' xatosi JSON ma'lumoti HTML atributiga joylashganda yuzaga keladi.
    # Biz data-categories='{{ ... | safe }}' ishlatganimiz uchun, JSON ichidagi barcha
    # maxsus belgilar HTML atributi uchun xavfsiz holatga keltirilishi kerak:
    
    # A) JSON ichidagi qo'shtirnoqlarni ("xato") HTML atributi uchun (&quot;) ga almashtiramiz.
    categories_json_safe = categories_json_raw.replace('"', '&quot;')
    
    # B) Yagona apostroflarni (masalan, o'zbekcha nomlardagi ' ) HTML atributi uchun xavfsizlashtiramiz (&#39;).
    # json.dumps bitta apostroflarni qochirmasligi mumkin, chunki u qo'shtirnoq ichida.
    categories_json_safe = categories_json_safe.replace("'", "&#39;")


    context = {
        'form': form,
        # categories_json: Endi bu &quot; va &#39; bilan tozalangan JSON matn.
        'categories_json': categories_json_safe, 
        'initial_type': transaction_type, 
    }
    return render(request, 'transaction_form.html', context)

def get_all_categories_for_js(user):
    """
    Foydalanuvchiga tegishli barcha kategoriyalarni, ularning turini, 
    otasini va o'chirish URL'ini o'z ichiga olgan JSON string yaratadi.
    """
    # Foydalanuvchi yoki global kategoriyalarni olish
    categories_queryset = Category.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True),
    ).select_related('parent').order_by('type', 'parent__id', 'name')
    
    categories_list = []
    
    # O'chirish url'ini to'g'ri yaratish uchun 'category_delete' URL nomi mavjud bo'lishi kerak.
    # Agar siz AJAX DELETE so'rovini ishlatmoqchi bo'lsangiz, bu yerda URL shart emas.

    for cat in categories_queryset:
        
        # Bu mantiq yordamchi usul orqali Category modelida bo'lishi kerak.
        # Bu yerda Category.objects.filter ga mos kelishi uchun:
        parent_full_name = cat.parent.name if cat.parent else None 
        
        categories_list.append({
            'id': cat.id,
            'name': cat.name,
            'type': cat.type,
            'parent_id': cat.parent.id if cat.parent else None,
            'parent_name': parent_full_name,
            'user_owned': cat.user == user, # Faqat foydalanuvchiga tegishli bo'lsa o'chirish mumkin
        })
    
    # JSON stringga aylantirish.
    return json.dumps(categories_list, cls=DjangoJSONEncoder, ensure_ascii=False)

@login_required
@require_http_methods(["DELETE"])
def delete_category_view(request, category_id):
    """
    Berilgan ID bo'yicha kategoriyani o'chirish (DELETE so'rovi orqali).
    Faqat foydalanuvchiga tegishli kategoriyalar o'chirilishi mumkin.
    """
    try:
        # Kategoriyani topish
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse({"success": False, "error": "Kategoriya topilmadi."}, status=404)
    
    # Kategoriya o'chirilishi mumkinmi? (Faqat user_owned kategoriyalar o'chirilishi mumkin)
    # Global kategoriyalarni (user=None) o'chirishga ruxsat yo'q.
    if category.user != request.user:
        return JsonResponse({"success": False, "error": "Siz ushbu kategoriyani o'chira olmaysiz. U sizga tegishli emas yoki globaldir."}, status=403)
    
    # Ushbu kategoriyaga bog'langan tranzaksiyalar bormi?
    if category.transactions.exists():
         # Buni yumshoq o'chirish (soft delete) yoki foydalanuvchiga ta'sir haqida xabar berish kerak
         return JsonResponse({
             "success": False, 
             "error": f"«{category.name}» kategoriyasi bog'langan tranzaksiyalarga ega. Uni o'chirish uchun avval tranzaksiyalarni o'zgartiring.",
             "name": category.name
        }, status=409) # Conflict status
        
    try:
        # O'chirish
        category_name = category.name
        category.delete()
        return JsonResponse({"success": True, "message": f"«{category_name}» kategoriyasi muvaffaqiyatli o'chirildi."})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"O'chirishda xato yuz berdi: {str(e)}"}, status=500)

@login_required
def add_category_view(request):
    user = request.user
    
    # Kategoriyalarni filtrlash uchun kerak bo'ladi, masalan, Category.objects.all()
    # yoki Category.objects.filter(user=user) - bu sizning modellar strukturasiga bog'liq.
    # Bizning holatda, parent sifatida faqat ota kategoriyalar kerak.

    # Formadagi yuqori kategoriya (Parent) tanlovi uchun barcha tegishli kategoriyalar
    parent_categories_for_form = Category.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True),
    ).select_related('parent')
    
    if request.method == 'POST':
        # ... (Siz yuborgan POST so'rovi mantig'i deyarli o'zgarishsiz qoladi) ...
        name = request.POST.get('name', '').strip()
        type_ = request.POST.get('type')
        parent_id = request.POST.get('parent') # Eslatma: parent_id bo'sh string bo'lishi mumkin
        is_active = request.POST.get('is_active') == 'on'

        # Validatsiya
        if not name:
            messages.error(request, "Kategoriya nomi bo‘sh bo‘lishi mumkin emas.")
        # ... (qolgan validatsiya mantiqi) ...
        elif not type_ in dict(TYPE_CHOICES):
             messages.error(request, "Noto‘g‘ri tur tanlandi.")
        else:
            parent = None
            if parent_id:
                # get_object_or_404 bu yerda to'g'ri, lekin faqat integer IDlar uchun.
                # Agar parent_id bo'sh bo'lsa, xato beradi. Shuning uchun biz tekshiramiz:
                try:
                    parent = Category.objects.get(id=parent_id)
                except Category.DoesNotExist:
                    messages.error(request, "Yuqori kategoriya topilmadi.")
                    parent = None
                
                if parent:
                    # Validatsiyani kuchaytirish
                    if parent.type != type_:
                        messages.error(request, "Yuqori kategoriya turi bilan mos kelishi kerak.")
                        parent = None
                    elif parent.user and parent.user != user and parent.user is not None:
                        messages.error(request, "Boshqa foydalanuvchi kategoriyasini tanlay olmaysiz.")
                        parent = None

            # Takrorlanishni tekshirish
            exists = Category.objects.filter(
                 user=user,
                 name=name,
                 type=type_,
                 parent=parent
            ).exists()

            if exists:
                 messages.error(request, "Bunday kategoriya allaqachon mavjud.")
            else:
                 # Yaratish
                 Category.objects.create(
                      user=user,
                      name=name,
                      type=type_,
                      parent=parent,
                      is_active=is_active
                 )
                 messages.success(request, f"«{name}» kategoriyasi muvaffaqiyatli qo‘shildi.")
                 
                 # category_list ga emas, shu sahifaning o'ziga redirect qilamiz
                 return redirect('add_category') # URL nomini 'add_category' deb taxmin qilamiz


    # Barcha kategoriyalarni JSON formatida olish (Ro'yxat uchun)
    all_categories_json_raw = get_all_categories_for_js(request.user)
    
    # Xavfsiz qochirish (oldingi muammolarni eslab)
    all_categories_json_safe = all_categories_json_raw.replace('"', '&quot;')
    all_categories_json_safe = all_categories_json_safe.replace("'", "&#39;")


    context = {
        'parent_categories': parent_categories_for_form,
        'type_choices': TYPE_CHOICES,
        'all_categories_json': all_categories_json_safe, # Ro'yxatni JS orqali render qilish uchun
    }
    return render(request, 'category_form.html', context)


@login_required
def recurring_list_view(request):
    today = timezone.localdate()

    # HAMMA SHARTLAR Q() ichida — keyword emas, positional
    recurring_incomes = RecurringSchedule.objects.filter(
        Q(user=request.user),
        Q(category__type='INCOME'),
        Q(is_active=True),
        Q(start_date__lte=today),
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).select_related('category').order_by('day_of_month')

    recurring_expenses = RecurringSchedule.objects.filter(
        Q(user=request.user),
        Q(category__type='EXPENSE'),
        Q(is_active=True),
        Q(start_date__lte=today),
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).select_related('category').order_by('day_of_month')

    return render(request, 'recurring_list.html', {
        'recurring_incomes': recurring_incomes,
        'recurring_expenses': recurring_expenses,
    })


@login_required
def add_recurring_view(request):
    if request.method == 'POST':
        form = RecurringScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Yangi takrorlanuvchi yozuv muvaffaqiyatli qo‘shildi!")
            return redirect('recurring_list')
    else:
        form = RecurringScheduleForm(user=request.user)

    return render(request, 'add_recurring.html', {'form': form})

@login_required
def delete_recurring_view(request, pk):
    item = get_object_or_404(RecurringSchedule, id=pk, user=request.user)
    if request.method == 'POST':
        item.delete()
    return redirect('recurring_list')

def about_view(request):
    return render(request, 'about.html')

# --- 4. Budjetlar View ---
def budget_about(request):
    return render(request, 'budget_about.html')

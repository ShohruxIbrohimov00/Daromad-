from django import template
from django.db.models import QuerySet 
from decimal import Decimal

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """ Lug'atdan kalit bo'yicha qiymatni qaytaradi. """
    return dictionary.get(key)

@register.filter(name='percentage_of')
def percentage_of(numerator, denominator):
    """ Ikki sonning foiz nisbatini hisoblaydi. """
    try:
        if denominator:
            # Foizni Decimal hisoblash uchun
            return (Decimal(str(numerator)) / Decimal(str(denominator))) * 100
    except Exception:
        return 0
    return 0

@register.filter(name='currency')
def currency(value, currency_symbol=' so\'m'):
    """ 
    Sonni valyuta formatiga o'tkazadi (masalan, 1234567.89 -> 1 234 567 so'm). 
    Oxiridagi .00 ni olib tashlaydi.
    """
    if value is None or value == '':
        return f'0{currency_symbol}'
    
    try:
        # Decimal'ga o'tkazamiz va faqat butun qismini olamiz
        value = Decimal(str(value))
        integer_part_val = int(value) # Butun sonni olish
        
        # Sonni stringga o'tkazish
        s = str(integer_part_val)
        
        # Manfiy sonni aniqlash
        is_negative = s.startswith('-')
        if is_negative:
            s = s[1:]
            
        # Har 3 ta raqamdan keyin bo'luvchi qo'shish
        new_integer_part = ''
        for i, digit in enumerate(reversed(s)):
            if i > 0 and i % 3 == 0:
                new_integer_part += ' '
            new_integer_part += digit
            
        formatted_integer_part = ''.join(reversed(new_integer_part))
        
        result = f"{formatted_integer_part}{currency_symbol}"
        
        return f"-{result}" if is_negative else result
        
    except Exception:
        # Xatolik yuz bersa, original qiymatni qaytarish
        return f"{str(value)}{currency_symbol}"

@register.filter
def filter_by_type(queryset, type_name):
    """ 
    Tranzaksiya QuerySet'ini category__type bo'yicha filtrlash uchun.
    """
    if not isinstance(queryset, QuerySet):
        return []
        
    if type_name not in ['INCOME', 'EXPENSE']:
        return queryset 
        
    return queryset.filter(category__type=type_name)

@register.filter
def filter_display_name(value):
    """
    INCOME/EXPENSE kabi qisqa nomlarni to'liq o'zbekcha nomga o'giradi.
    """
    if value == 'INCOME':
        return 'Daromadlar'
    elif value == 'EXPENSE':
        return 'Xarajatlar'
    return value

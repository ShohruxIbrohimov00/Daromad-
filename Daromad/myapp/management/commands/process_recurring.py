from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
# Kerakli modellarni import qilamiz
from myapp.models import RecurringSchedule, Transaction, Category
from django.db.models import Q

class Command(BaseCommand):
    help = 'Takrorlanuvchi jadvallarni tekshiradi va tegishli tranzaksiyalarni yaratadi.'

    def handle(self, *args, **options):
        # Bugungi sanani olamiz (faqat sanani, vaqtni emas)
        today = timezone.now().date()
        
        # SQL/DB sathida to'liq xavfsizlikni ta'minlaymiz
        with transaction.atomic():
            
            # Faol jadvallarni topish mantiqi:
            # 1. Faol bo'lishi kerak (is_active=True).
            # 2. Bugungi kun jadvalda belgilangan kunga mos kelishi kerak (day_of_month).
            # 3. Agar mavjud bo'lsa, tugash sanasidan oldin bo'lishi kerak (end_date).
            # 4. Oxirgi bajarilgan sana bugungi kundan oldin bo'lishi kerak, 
            #    yoki umuman bajarilmagan bo'lishi kerak (bir kunda ikki marta bajarilishining oldini oladi).
            
            schedules_to_execute = RecurringSchedule.objects.filter(
                is_active=True,
                day_of_month=today.day,
                start_date__lte=today, # Boshlanish sanasi o'tgan yoki bugun
                end_date__gte=today,    # Tugash sanasi kelajakda (yoki bo'sh)
            ).filter(
                # Oxirgi bajarilgan sana bugun bo'lmasligi kerak
                # OR Bu jadval hali umuman bajarilmagan (last_executed=None) bo'lishi kerak
                Q(last_executed__lt=today) | Q(last_executed__isnull=True)
            ).select_related('category', 'user') # Kategoriya va User ma'lumotlarini optimallashtirish uchun

            self.stdout.write(self.style.NOTICE(
                f"[{today}] Bajariladigan jadvallar soni topildi: {schedules_to_execute.count()}"
            ))

            for schedule in schedules_to_execute:
                try:
                    # 1. Yangi Tranzaksiya yaratish
                    Transaction.objects.create(
                        user=schedule.user,
                        amount=schedule.amount,
                        category=schedule.category,
                        date=today,
                        description=f"Avtomatik takrorlanuvchi tranzaksiya: {schedule.note or schedule.category.name}",
                        recurring_schedule=schedule,
                        is_automated=True  # Avtomatik yaratilganligini belgilash
                        # Eslatma: Account modeli qo'shilmagani uchun bu yerda Account qo'shilmayapti
                    )
                    
                    # 2. last_executed sanasini yangilash
                    schedule.last_executed = today
                    schedule.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"Muvaffaqiyatli: {schedule.category.name} ({schedule.amount}) {today} sanasi uchun qo'shildi."
                    ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Xatolik yuz berdi ({schedule.id}): {e}"
                    ))
        
        self.stdout.write(self.style.SUCCESS('Takrorlanuvchi tranzaksiyalarni qayta ishlash yakunlandi.'))
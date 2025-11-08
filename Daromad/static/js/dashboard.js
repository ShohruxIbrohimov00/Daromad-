// Faqatgina sahifa to'liq yuklanganidan so'ng JS kodini ishga tushirish
document.addEventListener('DOMContentLoaded', function () {
    // ----------------------------------------------------
    // DOM Elementlarini olish (ID tekshiruvi muhim!)
    // ----------------------------------------------------
    const prevBtn = document.getElementById('prev-month-btn');
    const nextBtn = document.getElementById('next-month-btn');
    const display = document.getElementById('date-display-text');
    const dataContainer = document.getElementById('report-data');
    const transactionListContainer = document.getElementById('transaction-list-container');
    const currentListTypeSpan = document.getElementById('current-list-type');

    // Tugmalar mavjudligini tezda tekshirish. Agar yo'q bo'lsa, konsolga xato chiqarib, to'xtash.
    if (!prevBtn || !nextBtn || !dataContainer) {
        console.error("Dashboard yuklanishda xato: HTML'da kerakli ID elementlari topilmadi (prev-month-btn, next-month-btn yoki report-data).");
        return; 
    }

    // ----------------------------------------------------
    // Dastlabki qiymatlar (Django kontekstidan olinadi)
    // ----------------------------------------------------
    let currentYear = parseInt(dataContainer.dataset.currentYear);
    let currentMonth = parseInt(dataContainer.dataset.currentMonth);
    // currentFilter = URL'dan olingan filter, agar yo'q bo'lsa 'INCOME' bo'lishi kerak
    let currentFilter = dataContainer.dataset.currentFilter || 'INCOME'; 
    
    const partialUrl = dataContainer.dataset.partialUrl; 

    // O‘zbekcha to‘liq oy nomlari
    const monthNames = [
        'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
        'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'
    ];
    
    // Tarjima qilingan filtr nomlari
    const filterNamesUz = {
        'INCOME': 'Daromadlar',
        'EXPENSE': 'Xarajatlar'
    };

    /**
     * Joriy sana parametrlarisiz toza bazaviy URL yo'lini oladi.
     * Masalan, agar URL '/dashboard/2025/11/' bo'lsa, '/dashboard/' ni qaytaradi.
     */
    function getBaseUrl() {
        const pathname = window.location.pathname;
        
        // '/YYYY/MM/' yoki '/YYYY/M/' naqshini aniqlaydi va olib tashlaydi.
        // Ikkala holatni ham qamrab olish uchun naqshni tuzatdik.
        const datePathRegex = /(\d{4})\/(\d{1,2})\/?$/; 
        
        let baseUrl;

        if (datePathRegex.test(pathname)) {
            // Agar sanali path bo'lsa, sanani olib tashlaymiz.
            baseUrl = pathname.replace(datePathRegex, '');
        } else {
            // Agar sanasiz path bo'lsa (masalan, faqat / yoki /dashboard/), u baza hisoblanadi.
            baseUrl = pathname;
        }

        // Oxirida doimo '/' mavjudligini ta'minlaymiz, bu Django URL reverse uchun muhim.
        return baseUrl.endsWith('/') ? baseUrl : baseUrl + '/';
    }

    /* ---------------- AJAX TRANTZAKSIYA YUKLASH FUNKSIYASI ---------------- */

    function loadTransactions() {
        if (!transactionListContainer) return; // Agar ro'yxat konteyneri topilmasa, to'xtatish

        // Yuklanmoqda animatsiyasini ko'rsatish
        transactionListContainer.innerHTML = `
            <div class="text-center p-10 text-gray-500">
                <i class="fas fa-spinner fa-spin text-2xl block mb-2"></i>
                Ma'lumotlar yuklanmoqda...
            </div>
        `;

        const monthFormatted = String(currentMonth).padStart(2, '0');
        // AJAX so'rovida Filter turini qo'shamiz
        const url = `${partialUrl}?year=${currentYear}&month=${monthFormatted}&type=${currentFilter}`; 

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Taranzaksiya ma\'lumotlarini yuklashda xato: Server xatosi.');
                }
                return response.text();
            })
            .then(html => {
                transactionListContainer.innerHTML = html;
            })
            .catch(error => {
                console.error("AJAX Xato:", error);
                transactionListContainer.innerHTML = `<div class="text-center p-10 text-red-500 bg-red-100 rounded-lg"><i class="fas fa-triangle-exclamation text-2xl block mb-2"></i>Xatolik: Ro'yxatni yuklab bo'lmadi. ${error.message}</div>`;
            });
    }

    /* ---------------- SANANI YANGILASH VA NAVIGATSIYA ---------------- */

    /**
     * Yangi sana bo'yicha URL'ga to'liq yo'naltirishni amalga oshiradi.
     * Bu, sahifaning boshqa Django kontekst ma'lumotlarini (balans, statistika) yangilash uchun muhim.
     */
    function updateUrlAndRedirect() {
        const newMonthFormatted = String(currentMonth);
        const baseUrl = getBaseUrl(); 
        
        // Yangi URL: BASE_URL + YYYY/MM/
        // Boshqa barcha ma'lumotlarni yangilash uchun sahifani butunlay yangi URL'ga yo'naltiramiz.
        // Hozirgi filtr turini ham URL so'roviga qo'shamiz (bu muhim)
        const redirectUrl = `${baseUrl}${currentYear}/${newMonthFormatted}/?filter=${currentFilter}`;
        
        // Debug qilish uchun konsolga chiqarish
        console.log("BASE URL:", baseUrl);
        console.log("REDIRECT TO:", redirectUrl); 
        
        // To'liq sahifani yangi URL'ga yo'naltirish (Sahifa yangilanadi!)
        window.location.href = redirectUrl;
    }

    /**
     * Faqat HTML elementlarni yangilash (navigatsiya qilmasdan)
     */
    function updateDisplayAndState() {
        const today = new Date();
        const isThisMonth = currentYear === today.getFullYear() && currentMonth === today.getMonth() + 1;

        // Sana displayini yangilash
        const monthName = monthNames[currentMonth - 1];
        if (isThisMonth) {
            display.textContent = `${monthName} 1 - ${today.getDate()}, ${currentYear}`;
        } else {
            display.textContent = `${monthName} ${currentYear}`;
        }

        // Keyingi oy tugmasini o'chirish/yoqish
        nextBtn.disabled = isThisMonth;
        
        // Filtr nomini yangilash (Tranzaksiya sarlavhasi)
        currentListTypeSpan.textContent = filterNamesUz[currentFilter] || currentFilter;

        // Filtr tablarning "active" holatini yangilash (AJAX orqali filtrlashda ishlatiladi)
        document.querySelectorAll('.filter-tab').forEach(t => {
            t.classList.remove('active-filter', 'income-active', 'expense-active');
            if (t.dataset.filter === currentFilter) {
                t.classList.add('active-filter');
                if (currentFilter === 'INCOME') {
                    t.classList.add('income-active');
                } else {
                    t.classList.add('expense-active');
                }
            }
        });
    }


    /* ---------------- EVENT LISTENERS ---------------- */

    // Oldingi oy tugmasini bosish
    prevBtn.addEventListener('click', () => {
        if (currentMonth === 1) {
            currentMonth = 12;
            currentYear--;
        } else {
            currentMonth--;
        }
        // Sahifani to'liq yangilash
        updateUrlAndRedirect(); 
    });

    // Keyingi oy tugmasini bosish
    nextBtn.addEventListener('click', () => {
        const today = new Date();
        const nextMonthYear = currentMonth === 12 ? currentYear + 1 : currentYear;
        const nextMonth = currentMonth === 12 ? 1 : currentMonth + 1;
        
        // Kelajak oyga o'tishni bloklash
        if (nextMonthYear > today.getFullYear() || (nextMonthYear === today.getFullYear() && nextMonth > today.getMonth() + 1)) {
            return; 
        }

        currentMonth = nextMonth;
        currentYear = nextMonthYear;
        
        // Sahifani to'liq yangilash
        updateUrlAndRedirect(); 
    });

    // Filtrlash tugmalari (Daromad/Xarajat)
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const newFilter = tab.dataset.filter;
            if (newFilter === currentFilter) {
                return; // Agar filtr o'zgarmasa, hech narsa qilmaymiz
            }

            currentFilter = newFilter;
            
            // Filtrlash tugmasi bosilganda, biz faqatgina tranzaksiya ro'yxatini AJAX orqali yangilaymiz, 
            // chunki boshqa ma'lumotlar (balans, statistika) oy navigatsiyasida yangilanadi.
            updateDisplayAndState(); 
            loadTransactions(); 
        });
    });

    // Dastlabki holatni o'rnatish
    updateDisplayAndState();
    
    console.log("Dashboard JS muvaffaqiyatli yuklandi. Event Listeners faollashdi.");
});
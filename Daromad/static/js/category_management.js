let allCategories = [];
let currentType = 'EXPENSE';

document.addEventListener('DOMContentLoaded', function () {
    // Parse data
    const raw = document.getElementById('category-data')?.dataset.categories || '';
    const cleaned = raw.replace(/&quot;/g, '"').replace(/&#39;/g, "'");
    try {
        allCategories = cleaned ? JSON.parse(cleaned) : [];
    } catch (e) {
        console.error("JSON parse xatosi:", e);
        document.getElementById('category-list').innerHTML = 
            `<div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Kategoriyalarni yuklashda xato yuz berdi.</p>
            </div>`;
        return;
    }

    // Tab o‘tish
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
            if (btn.dataset.tab === 'list') {
                renderList();
            } else if (btn.dataset.tab === 'add') {
                updateParentOptions(); // Forma ochilganda parent optionlarni yangilash
            }
        });
    });

    // Turi o‘zgartirish
    document.querySelectorAll('.type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentType = btn.dataset.type;
            document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderList();
        });
    });

    // O‘chirish (fetch)
    document.getElementById('category-list').addEventListener('click', async (e) => {
        const btn = e.target.closest('.delete-btn');
        if (!btn) return;

        const name = btn.dataset.name;
        if (!confirm(`"${name}" kategoriyasini o‘chirasizmi?`)) return;

        try {
            const res = await fetch(`/category/delete/${btn.dataset.id}/`, {
                method: 'DELETE',
                headers: { 
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (res.ok) {
                allCategories = allCategories.filter(c => c.id != btn.dataset.id);
                renderList();
                updateCounts();
            } else {
                const error = await res.text();
                alert('O‘chirishda xato: ' + (error || 'Server xatosi'));
            }
        } catch (err) {
            console.error(err);
            alert('Tarmoq xatosi. Internet aloqangizni tekshiring.');
        }
    });

    // Init
    renderList();
    updateCounts();

    // Agar xato yoki muvaffaqiyat xabari bo‘lsa → "Yangi qo‘shish" ga o‘t
    if (document.querySelector('.msg')) {
        document.querySelector('[data-tab="add"]').click();
    }

    // Forma turi o‘zgarganda parent optionlarni yangilash
    const typeSelect = document.querySelector('select[name="type"]');
    if (typeSelect) {
        typeSelect.addEventListener('change', updateParentOptions);
        updateParentOptions(); // Dastlabki holat
    }
});

// Kategoriyalarni render qilish
function renderList() {
    const container = document.getElementById('category-list');
    container.innerHTML = '';

    const filtered = allCategories.filter(c => c.type === currentType);
    if (!filtered.length) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>Bu turda kategoriya yo‘q. Yangi qo‘shing!</p>
            </div>`;
        return;
    }

    const parents = filtered.filter(c => !c.parent_id).sort((a, b) => a.name.localeCompare(b.name));
    parents.forEach(parent => {
        container.appendChild(createCard(parent, true));
        const subs = filtered.filter(c => c.parent_id === parent.id).sort((a, b) => a.name.localeCompare(b.name));
        if (subs.length) {
            const subGrid = document.createElement('div');
            subGrid.className = 'ml-12 grid grid-cols-1 gap-3 mt-3';
            subs.forEach(sub => subGrid.appendChild(createCard(sub, false)));
            container.appendChild(subGrid);
        }
    });
}

// Karta yaratish
function createCard(cat, isParent) {
    const card = document.createElement('div');
    card.className = `category-card ${cat.type.toLowerCase()}-card`;

    card.innerHTML = `
        <div class="category-info ${cat.type.toLowerCase()}-info">
            <h3><i class="fas fa-tag"></i> ${escapeHtml(cat.name)}</h3>
            <div class="category-meta">
                ${isParent 
                    ? '<span class="global-badge">Asosiy</span>' 
                    : `<span class="parent-path"><i class="fas fa-level-up-alt"></i> ${escapeHtml(cat.parent_name || 'Noma\'lum')}</span>`
                }
                ${cat.is_active ? '' : '<span class="global-badge bg-gray-200 text-gray-600">Faolsiz</span>'}
            </div>
        </div>
        <div class="category-actions">
            ${cat.user_owned ? `
                <button class="delete-btn" data-id="${cat.id}" data-name="${escapeHtml(cat.name)}" title="O‘chirish">
                    <i class="fas fa-trash-alt"></i>
                </button>
            ` : `<span class="global-badge">Global</span>`}
        </div>
    `;
    return card;
}

// Sonlarni yangilash
function updateCounts() {
    const expense = allCategories.filter(c => c.type === 'EXPENSE').length;
    const income = allCategories.filter(c => c.type === 'INCOME').length;
    document.getElementById('expense-count').textContent = expense;
    document.getElementById('income-count').textContent = income;
}

// CSRF token olish
function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Xavfsiz HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Parent optionlarni yangilash
window.updateParentOptions = function() {
    const type = document.querySelector('select[name="type"]').value;
    const group = document.getElementById('parent-group');
    if (!group) return;

    if (type) {
        group.style.display = 'block';
        document.querySelectorAll('.parent-option').forEach(opt => {
            opt.style.display = 'none';
        });
        document.querySelectorAll(`.parent-${type}`).forEach(opt => {
            opt.style.display = 'block';
        });
    } else {
        group.style.display = 'none';
    }
};
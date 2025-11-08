let allCategories = [];
let currentType = 'EXPENSE';

document.addEventListener('DOMContentLoaded', function () {
    // 1. Kategoriyalarni yuklash
    const raw = document.getElementById('category-data')?.dataset.categories || '';
    try {
        allCategories = raw ? JSON.parse(raw) : [];
    } catch (e) {
        console.error("JSON parse xatosi:", e);
        showEmptyState("Kategoriyalarni yuklashda xato yuz berdi.");
        return;
    }

    // 2. Tab o‘tish
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('panel-' + btn.dataset.tab).classList.add('active');

            if (btn.dataset.tab === 'list') renderList();
            if (btn.dataset.tab === 'add') updateParentOptions();
        });
    });

    // 3. Tur o‘zgartirish
    document.querySelectorAll('.type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentType = btn.dataset.type;
            document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderList();
        });
    });

    // 4. O‘chirish (AJAX)
    document.getElementById('category-list').addEventListener('click', async (e) => {
        const btn = e.target.closest('.delete-btn');
        if (!btn) return;

        const name = btn.dataset.name;
        if (!confirm(`"${name}" kategoriyasini o‘chirasizmi?`)) return;

        try {
            const res = await fetch(`/category/delete/${btn.dataset.id}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': window.csrfToken || getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (res.ok) {
                allCategories = allCategories.filter(c => c.id != btn.dataset.id);
                renderList();
                updateCounts();
            } else {
                const err = await res.text();
                alert('O‘chirishda xato: ' + (err || 'Server xatosi'));
            }
        } catch (err) {
            console.error(err);
            alert('Internet aloqasi muammosi.');
        }
    });

    // 5. Forma turi o‘zgarganda
    const typeSelect = document.querySelector('select[name="type"]');
    if (typeSelect) {
        typeSelect.addEventListener('change', updateParentOptions);
        updateParentOptions();
    }

    // 6. Dastlabki render
    renderList();
    updateCounts();

    // 7. Xabar bo‘lsa → "Yangi qo‘shish" ga o‘t
    if (document.querySelector('.msg, .alert')) {
        const addTab = document.querySelector('[data-tab="add"]');
        addTab && addTab.click();
    }
});

// === RENDER LIST ===
function renderList() {
    const container = document.getElementById('category-list');
    container.innerHTML = '';

    const filtered = allCategories.filter(c => c.type === currentType);
    if (!filtered.length) {
        showEmptyState(`Bu turda kategoriya yo‘q. Yangi qo‘shing!`);
        return;
    }

    const parents = filtered.filter(c => !c.parent_id).sort(byName);
    parents.forEach(parent => {
        container.appendChild(createCard(parent, true));

        const subs = filtered.filter(c => c.parent_id === parent.id).sort(byName);
        if (subs.length) {
            const subGrid = document.createElement('div');
            subGrid.className = 'ml-6 mt-1 pl-2 border-l-2 border-dashed border-gray-300';
            subs.forEach(sub => subGrid.appendChild(createCard(sub, false)));
            container.appendChild(subGrid);
        }
    });
}

// === KARTA YARATISH ===
function createCard(cat, isParent) {
    const card = document.createElement('div');
    card.className = `category-card ${cat.type.toLowerCase()}-card`;

    const statusBadge = cat.is_active
        ? ''
        : '<span class="global-badge bg-gray-200 text-gray-600">Faol</span>';

    const parentBadge = isParent
        ? '<span class="global-badge">Asosiy</span>'
        : `<span class="parent-path"><i class="fas fa-level-up-alt"></i> ${escapeHtml(cat.parent_name || 'Noma\'lum')}</span>`;

    card.innerHTML = `
        <div class="category-info ${cat.type.toLowerCase()}-info">
            <h3><i class="fas fa-tag"></i> ${escapeHtml(cat.name)}</h3>
            <div class="category-meta">
                ${isParent ? parentBadge : parentBadge}
                ${statusBadge}
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

// === SONLARNI YANGILASH ===
function updateCounts() {
    const expense = allCategories.filter(c => c.type === 'EXPENSE').length;
    const income = allCategories.filter(c => c.type === 'INCOME').length;
    const expEl = document.getElementById('expense-count');
    const incEl = document.getElementById('income-count');
    if (expEl) expEl.textContent = expense;
    if (incEl) incEl.textContent = income;
}

// === UTILS ===
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function byName(a, b) {
    return a.name.localeCompare(b.name, 'uz', { sensitivity: 'base' });
}

function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

function showEmptyState(message) {
    const container = document.getElementById('category-list');
    if (!container) return;
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-inbox"></i>
            <p>${escapeHtml(message)}</p>
        </div>`;
}

// === PARENT OPTIONS ===
window.updateParentOptions = function() {
    const type = document.querySelector('select[name="type"]').value;
    const group = document.getElementById('parent-group');
    if (!group) return;

    const options = group.querySelectorAll('.parent-option');
    options.forEach(opt => {
        const matches = type && opt.classList.contains(`parent-${type}`);
        opt.style.display = matches ? 'block' : 'none';
    });
    group.style.display = type ? 'block' : 'none';
};
// Configuration
const STAR_PRICE = 1.5;

document.addEventListener('DOMContentLoaded', function() {
    generateStars();
    initializeForm();
    loadLiveStats();
});

async function loadLiveStats() {
    try {
        const response = await fetch('/api/admin/stats');
        const data = await response.json();

        if (data.success) {
            const orders = data.orders || [];
            const today = new Date().toDateString();
            const todayOrders = orders.filter(o => new Date(o.date).toDateString() === today);
            const starsToday = todayOrders.reduce((sum, o) => sum + o.stars, 0);

            const el = document.getElementById('ordersToday');
            const el2 = document.getElementById('starsToday');
            if (el) el.textContent = todayOrders.length || '0';
            if (el2) el2.textContent = starsToday || '0';

            // Последние покупки — реальные из базы
            const recent = document.getElementById('recentOrders');
            if (recent && orders.length > 0) {
                recent.innerHTML = orders.slice(0, 4).map(o => {
                    const masked = maskAccount(o.account);
                    return `<div class="recent-order"><span class="recent-user">${masked}</span><span class="recent-amount">+${o.stars} ⭐</span></div>`;
                }).join('');
            }
        }
    } catch (e) {
        // тихо — показываем дефолт
    }
}

function maskAccount(account) {
    let u = account.replace(/^@/, '').replace(/https?:\/\/t\.me\//, '').split('?')[0];
    if (u.length <= 3) return '@' + u[0] + '***';
    return '@' + u.slice(0, 2) + '***' + u.slice(-1);
}

function generateStars() {
    const starsContainer = document.getElementById('stars');
    const starCount = 120;

    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = `${Math.random() * 100}%`;
        star.style.top = `${Math.random() * 100}%`;
        star.style.animationDelay = `${Math.random() * 3}s`;
        starsContainer.appendChild(star);
    }

    for (let i = 0; i < 3; i++) {
        const shootingStar = document.createElement('div');
        shootingStar.className = 'shooting-star';
        shootingStar.style.left = `${Math.random() * 100}%`;
        shootingStar.style.top = `${Math.random() * 50}%`;
        shootingStar.style.animationDelay = `${Math.random() * 4}s`;
        shootingStar.style.width = '80px';
        starsContainer.appendChild(shootingStar);
    }
}

function initializeForm() {
    const form = document.getElementById('purchaseForm');
    const starsInput = document.querySelector('input[name="stars"]');
    const accountInput = document.getElementById('account');
    const totalPriceElement = document.getElementById('totalPrice');
    const quickButtons = document.querySelectorAll('.quick-btn');
    const submitBtn = document.getElementById('submitBtn');

    quickButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const amount = btn.dataset.amount;
            starsInput.value = amount;
            starsInput.dispatchEvent(new Event('input', { bubbles: true }));

            quickButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            updatePrice();
        });
    });

    starsInput.addEventListener('input', () => {
        quickButtons.forEach(b => b.classList.remove('active'));
        updatePrice();
    });

    function updatePrice() {
        const stars = parseInt(starsInput.value) || 0;
        const totalPrice = stars * STAR_PRICE;
        totalPriceElement.textContent = totalPrice.toLocaleString('ru-RU');
    }

    // Initial price update
    updatePrice();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const stars = parseInt(starsInput.value);
        const account = accountInput.value.trim();

        if (stars < 1) {
            showNotification('Введите корректное количество звезд', 'error');
            return;
        }

        if (!account) {
            showNotification('Введите ссылку на аккаунт', 'error');
            return;
        }

        if (!isValidTelegramAccount(account)) {
            showNotification('Введите корректную ссылку на аккаунт Telegram', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.querySelector('.btn-text').textContent = 'Создание заказа...';

        await createPayment(stars, account);
    });

    function isValidTelegramAccount(account) {
        return account.startsWith('@') ||
               account.includes('t.me/') ||
               account.includes('telegram.me/') ||
               /^[a-zA-Z0-9_]{5,32}$/.test(account);
    }

    async function createPayment(stars, account) {
        try {
            const response = await fetch('/api/create-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    stars: stars,
                    account: account,
                    amount: stars * STAR_PRICE
                })
            });

            const data = await response.json();

            if (data.success && data.paymentUrl) {
                window.location.href = data.paymentUrl;
            } else {
                throw new Error(data.error || 'Payment creation failed');
            }

        } catch (error) {
            console.error('Error:', error);
            showNotification('Ошибка при создании платежа. Попробуйте снова.', 'error');
            submitBtn.disabled = false;
            submitBtn.querySelector('.btn-text').textContent = 'Перейти к оплате';
        }
    }

    function showNotification(message, type = 'info') {
        alert(message);
    }
}

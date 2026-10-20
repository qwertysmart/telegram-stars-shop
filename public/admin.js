document.addEventListener('DOMContentLoaded', function() {
    generateStars();
    loadDashboardData();
    initializeControls();
});

function generateStars() {
    const starsContainer = document.getElementById('stars');
    const starCount = 80;

    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = `${Math.random() * 100}%`;
        star.style.top = `${Math.random() * 100}%`;
        star.style.animationDelay = `${Math.random() * 3}s`;
        starsContainer.appendChild(star);
    }
}

function initializeControls() {
    const updatePriceBtn = document.getElementById('updatePriceBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const logoutBtn = document.getElementById('logoutBtn');

    updatePriceBtn.addEventListener('click', updateStarPrice);
    refreshBtn.addEventListener('click', loadDashboardData);
    logoutBtn.addEventListener('click', logout);
}

async function loadDashboardData() {
    try {
        const response = await fetch('/api/admin/stats');
        const data = await response.json();

        if (data.success) {
            updateStats(data.stats);
            updateOrdersTable(data.orders);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateStats(stats) {
    document.getElementById('totalRevenue').textContent =
        `${stats.totalRevenue.toLocaleString('ru-RU')}₽`;
    document.getElementById('totalOrders').textContent = stats.totalOrders;
    document.getElementById('totalStars').textContent =
        stats.totalStars.toLocaleString('ru-RU');
    document.getElementById('starPrice').textContent = `${stats.starPrice}₽`;
    document.getElementById('priceInput').value = stats.starPrice;
}

function updateOrdersTable(orders) {
    const tbody = document.getElementById('ordersTable');

    if (!orders || orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Нет заказов</td></tr>';
        return;
    }

    tbody.innerHTML = orders.map(order => `
        <tr>
            <td>#${order.id}</td>
            <td>${new Date(order.date).toLocaleString('ru-RU')}</td>
            <td>${order.account}</td>
            <td>${order.product === 'premium' ? `Premium ${order.months}м 👑` : `${order.stars} ⭐`}</td>
            <td>${order.amount}₽</td>
            <td><span class="status status-${order.status}">${getStatusText(order.status)}</span></td>
        </tr>
    `).join('');
}

function getStatusText(status) {
    const statuses = {
        'pending': 'Ожидает',
        'completed': 'Выполнен',
        'failed': 'Отменен'
    };
    return statuses[status] || status;
}

async function updateStarPrice() {
    const priceInput = document.getElementById('priceInput');
    const newPrice = parseFloat(priceInput.value);

    if (newPrice < 0.1) {
        alert('Цена должна быть больше 0.1₽');
        return;
    }

    try {
        const response = await fetch('/api/admin/update-price', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ price: newPrice })
        });

        const data = await response.json();

        if (data.success) {
            alert('Цена успешно обновлена!');
            document.getElementById('starPrice').textContent = `${newPrice}₽`;
            loadDashboardData();
        } else {
            alert('Ошибка при обновлении цены');
        }
    } catch (error) {
        console.error('Error updating price:', error);
        alert('Ошибка при обновлении цены');
    }
}

function logout() {
    if (confirm('Выйти из админ панели?')) {
        window.location.href = '/';
    }
}

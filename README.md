# Telegram Stars Shop

Сервис для покупки и продажи Telegram Stars с интеграцией Gramix API.

## Функции

- 🌟 Покупка Telegram Stars
- 💳 Интеграция с платежными системами (в процессе)
- ⚡ Мгновенная доставка через Gramix API
- 📊 Отслеживание заказов через MongoDB
- 🎨 Современный дизайн с темной темой

## Технологии

- Python 3 + Flask
- MongoDB (для хранения заказов)
- Gramix API (для отправки звезд)
- Vanilla JavaScript (frontend)

## Установка

```bash
# Установить Python зависимости
pip install -r requirements.txt

# Запустить MongoDB (если используете локально)
# macOS с Homebrew:
brew services start mongodb-community

# Запустить сервер
python app.py
```

## Конфигурация

Файл `.env` уже создан с настройками:

```
GRAMIX_API_KEY=9Ad50-2wVLjU7WSAs8yNog97YqQ_Vud1Gxgs9_FnJlU
GRAMIX_API_URL=https://api.gramix.org
STAR_PRICE=2
MONGODB_URI=mongodb://localhost:27017/telegram-stars-shop
PORT=3000
```

## Структура проекта

```
telegram-stars-new/
├── app.py                 # Flask сервер
├── requirements.txt       # Python зависимости
├── public/
│   ├── index.html         # Главная страница
│   ├── payment.html       # Страница оплаты
│   ├── success.html       # Страница успеха
│   ├── style.css          # Стили
│   └── script.js          # Frontend логика
└── .env                   # Переменные окружения
```

## API Endpoints

### POST /api/create-payment
Создает новый заказ на покупку звезд.

**Body:**
```json
{
  "stars": 100,
  "account": "@username",
  "amount": 200
}
```

### POST /api/payment-webhook
Webhook для обработки платежей (вызывается платежной системой).

### GET /api/order/:orderId
Получить статус заказа по ID.

## TODO

- [ ] Интегрировать реальную платежную систему (ЮKassa, Robokassa, Cryptomus)
- [ ] Проверить и настроить Gramix API endpoints
- [ ] Добавить обработку ошибок и retry логику
- [ ] Добавить логирование
- [ ] Добавить rate limiting
- [ ] Добавить тесты

## Gramix API

Интеграция с Gramix API находится в `src/server.js` в функции `sendStarsViaGramix()`.

Текущий endpoint (может требоваться уточнение):
```
POST https://api.gramix.org/send-stars
Authorization: Bearer 9Ad50-2wVLjU7WSAs8yNog97YqQ_Vud1Gxgs9_FnJlU

{
  "recipient": "username",
  "amount": 100
}
```

## Лицензия

ISC

import os
import json
import time
import random
import string
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')

# Configuration
GRAMIX_API_KEY = os.getenv('GRAMIX_API_KEY', '')
GRAMIX_API_URL = os.getenv('GRAMIX_API_URL', 'https://api.gramix.org')
STAR_PRICE = float(os.getenv('STAR_PRICE', 1.5))
PORT = int(os.getenv('PORT', 3000))

# JSON database file
DB_FILE = 'orders.json'

def load_db():
    """Load orders from JSON file"""
    if not os.path.exists(DB_FILE):
        return {'orders': []}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'orders': []}

def save_db(data):
    """Save orders to JSON file"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def find_order(order_id):
    """Find order by ID"""
    db = load_db()
    for order in db['orders']:
        if order['orderId'] == order_id:
            return order
    return None

def update_order(order_id, updates):
    """Update order fields"""
    db = load_db()
    for order in db['orders']:
        if order['orderId'] == order_id:
            order.update(updates)
            order['updatedAt'] = datetime.utcnow().isoformat()
            break
    save_db(db)

# Routes
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/payment.html')
def payment():
    return send_from_directory('public', 'payment.html')


@app.route('/success.html')
def success():
    return send_from_directory('public', 'success.html')


@app.route('/admin')
def admin():
    return send_from_directory('public', 'admin.html')


# API: Create payment
@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    try:
        data = request.json
        product = data.get('product', 'stars')
        account = data.get('account')
        amount = data.get('amount')

        if not account or not amount:
            return jsonify({'error': 'Missing required fields'}), 400

        order_id = generate_order_id()

        order = {
            'orderId': order_id,
            'product': product,
            'account': account,
            'amount': amount,
            'status': 'pending',
            'paymentData': {},
            'gramixResponse': {},
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }

        if product == 'stars':
            stars = data.get('stars')
            if not stars or stars < 1:
                return jsonify({'error': 'Stars must be at least 1'}), 400
            order['stars'] = stars
        elif product == 'premium':
            months = data.get('months')
            if not months:
                return jsonify({'error': 'Months required for premium'}), 400
            order['months'] = months

        db = load_db()
        db['orders'].append(order)
        save_db(db)

        print(f'✓ Order created: {order_id} ({product})')

        payment_url = f'/payment.html?order={order_id}'

        return jsonify({
            'success': True,
            'orderId': order_id,
            'paymentUrl': payment_url,
            'amount': amount
        })

    except Exception as e:
        print(f'✗ Error creating payment: {e}')
        return jsonify({'error': 'Failed to create payment'}), 500


# API: Payment webhook
@app.route('/api/payment-webhook', methods=['POST'])
def payment_webhook():
    try:
        data = request.json
        order_id = data.get('orderId')
        status = data.get('status')
        payment_data = {k: v for k, v in data.items() if k not in ['orderId', 'status']}

        print(f'✓ Webhook received for order: {order_id}')

        order = find_order(order_id)

        if not order:
            print(f'✗ Order not found: {order_id}')
            return jsonify({'error': 'Order not found'}), 404

        if status == 'success':
            update_order(order_id, {
                'status': 'paid',
                'paymentData': payment_data
            })

            print(f'✓ Payment confirmed for order: {order_id}')

            try:
                gramix_result = send_via_gramix(order)

                update_order(order_id, {
                    'status': 'completed',
                    'gramixResponse': gramix_result
                })

                print(f'✓ Stars sent successfully for order: {order_id}')
                return jsonify({'success': True})

            except Exception as e:
                print(f'✗ Error sending stars: {e}')
                update_order(order_id, {'status': 'failed'})
                return jsonify({'success': False, 'error': str(e)}), 500

        else:
            update_order(order_id, {
                'status': 'failed',
                'paymentData': payment_data
            })

            print(f'✗ Payment failed for order: {order_id}')
            return jsonify({'success': False, 'error': 'Payment not successful'})

    except Exception as e:
        print(f'✗ Webhook error: {e}')
        return jsonify({'error': 'Webhook processing failed'}), 500


# API: Get order status
@app.route('/api/order/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        order = find_order(order_id)

        if not order:
            return jsonify({'error': 'Order not found'}), 404

        result = {
            'orderId': order['orderId'],
            'status': order['status'],
            'product': order.get('product', 'stars'),
            'account': order['account'],
            'amount': order['amount'],
            'createdAt': order['createdAt']
        }

        if order.get('stars'):
            result['stars'] = order['stars']
        if order.get('months'):
            result['months'] = order['months']

        return jsonify(result)

    except Exception as e:
        print(f'✗ Error fetching order: {e}')
        return jsonify({'error': 'Failed to fetch order'}), 500


# API: Admin stats
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        db = load_db()
        orders = db['orders']

        completed = [o for o in orders if o['status'] == 'completed']
        total_revenue = sum(o['amount'] for o in completed)
        total_stars = sum(o.get('stars', 0) for o in completed)

        # Last 20 orders sorted by date desc
        recent = sorted(orders, key=lambda x: x['createdAt'], reverse=True)[:20]

        formatted = []
        for order in recent:
            item = {
                'id': order['orderId'],
                'date': order['createdAt'],
                'account': order['account'],
                'amount': order['amount'],
                'status': order['status'],
                'product': order.get('product', 'stars')
            }
            if order.get('stars'):
                item['stars'] = order['stars']
            if order.get('months'):
                item['months'] = order['months']
            formatted.append(item)

        return jsonify({
            'success': True,
            'stats': {
                'totalRevenue': total_revenue,
                'totalOrders': len(orders),
                'totalStars': total_stars,
                'starPrice': STAR_PRICE
            },
            'orders': formatted
        })

    except Exception as e:
        print(f'✗ Error fetching admin stats: {e}')
        return jsonify({'error': 'Failed to fetch stats'}), 500


# API: Update star price
@app.route('/api/admin/update-price', methods=['POST'])
def update_star_price():
    try:
        data = request.json
        new_price = float(data.get('price', 0))

        if new_price < 0.1:
            return jsonify({'error': 'Price must be at least 0.1'}), 400

        global STAR_PRICE
        STAR_PRICE = new_price

        print(f'✓ Star price updated to {new_price}₽')

        return jsonify({'success': True})

    except Exception as e:
        print(f'✗ Error updating price: {e}')
        return jsonify({'error': 'Failed to update price'}), 500


# Gramix API integration
def send_via_gramix(order):
    """Send stars or premium via Gramix API"""
    try:
        username = extract_username(order['account'])
        product = order.get('product', 'stars')

        if product == 'premium':
            print(f"→ Sending Premium {order['months']}mo to {username} via Gramix...")
            response = requests.post(
                f'{GRAMIX_API_URL}/send-premium',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {GRAMIX_API_KEY}'
                },
                json={
                    'recipient': username,
                    'months': order['months']
                },
                timeout=30
            )
        else:
            print(f"→ Sending {order['stars']} stars to {username} via Gramix...")
            response = requests.post(
                f'{GRAMIX_API_URL}/send-stars',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {GRAMIX_API_KEY}'
                },
                json={
                    'recipient': username,
                    'amount': order['stars']
                },
                timeout=30
            )

        data = response.json()

        if not response.ok:
            raise Exception(f"Gramix API error: {data.get('error', response.text)}")

        print(f'✓ Gramix API response: {data}')
        return data

    except Exception as e:
        print(f'✗ Error sending via Gramix: {e}')
        raise


def extract_username(account):
    """Extract username from various Telegram account formats"""
    if account.startswith('@'):
        return account[1:]
    if 't.me/' in account:
        return account.split('t.me/')[1].split('?')[0]
    if 'telegram.me/' in account:
        return account.split('telegram.me/')[1].split('?')[0]
    return account


def generate_order_id():
    """Generate unique order ID"""
    timestamp = str(int(time.time() * 1000))
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
    return f'ORD{timestamp}{random_str}'


if __name__ == '__main__':
    print(f'\n🚀 Server starting on http://localhost:{PORT}\n')
    app.run(host='0.0.0.0', port=PORT, debug=True)

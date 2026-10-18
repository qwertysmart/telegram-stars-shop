import os
import time
import random
import string
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')

# Configuration
GRAMIX_API_KEY = os.getenv('GRAMIX_API_KEY')
GRAMIX_API_URL = os.getenv('GRAMIX_API_URL', 'https://api.gramix.org')
STAR_PRICE = int(os.getenv('STAR_PRICE', 2))
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/telegram-stars-shop')
PORT = int(os.getenv('PORT', 3000))

# MongoDB connection
try:
    client = MongoClient(MONGODB_URI)
    db = client.get_default_database()
    orders_collection = db.orders
    print('✓ MongoDB connected')
except Exception as e:
    print(f'✗ MongoDB connection error: {e}')
    orders_collection = None


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
        stars = data.get('stars')
        account = data.get('account')
        amount = data.get('amount')

        # Validate input
        if not stars or not account or not amount:
            return jsonify({'error': 'Missing required fields'}), 400

        if stars < 1:
            return jsonify({'error': 'Stars must be at least 1'}), 400

        # Generate unique order ID
        order_id = generate_order_id()

        # Create order in database
        order = {
            'orderId': order_id,
            'stars': stars,
            'account': account,
            'amount': amount,
            'status': 'pending',
            'paymentData': {},
            'gramixResponse': {},
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

        if orders_collection:
            orders_collection.insert_one(order)
            print(f'✓ Order created: {order_id}')
        else:
            print('✗ MongoDB not connected, order not saved')

        # TODO: Integrate real payment system
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

        if not orders_collection:
            return jsonify({'error': 'Database not connected'}), 500

        # Find order in database
        order = orders_collection.find_one({'orderId': order_id})

        if not order:
            print(f'✗ Order not found: {order_id}')
            return jsonify({'error': 'Order not found'}), 404

        if status == 'success':
            # Update order status
            orders_collection.update_one(
                {'orderId': order_id},
                {'$set': {
                    'status': 'paid',
                    'paymentData': payment_data,
                    'updatedAt': datetime.utcnow()
                }}
            )

            print(f'✓ Payment confirmed for order: {order_id}')

            # Send stars via Gramix API
            try:
                gramix_result = send_stars_via_gramix(order['stars'], order['account'])

                # Update order with Gramix response
                orders_collection.update_one(
                    {'orderId': order_id},
                    {'$set': {
                        'status': 'completed',
                        'gramixResponse': gramix_result,
                        'updatedAt': datetime.utcnow()
                    }}
                )

                print(f'✓ Stars sent successfully for order: {order_id}')
                return jsonify({'success': True})

            except Exception as e:
                print(f'✗ Error sending stars: {e}')
                orders_collection.update_one(
                    {'orderId': order_id},
                    {'$set': {
                        'status': 'failed',
                        'updatedAt': datetime.utcnow()
                    }}
                )
                return jsonify({'success': False, 'error': str(e)}), 500

        else:
            orders_collection.update_one(
                {'orderId': order_id},
                {'$set': {
                    'status': 'failed',
                    'paymentData': payment_data,
                    'updatedAt': datetime.utcnow()
                }}
            )

            print(f'✗ Payment failed for order: {order_id}')
            return jsonify({'success': False, 'error': 'Payment not successful'})

    except Exception as e:
        print(f'✗ Webhook error: {e}')
        return jsonify({'error': 'Webhook processing failed'}), 500


# API: Get order status
@app.route('/api/order/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        if not orders_collection:
            return jsonify({'error': 'Database not connected'}), 500

        order = orders_collection.find_one({'orderId': order_id})

        if not order:
            return jsonify({'error': 'Order not found'}), 404

        return jsonify({
            'orderId': order['orderId'],
            'status': order['status'],
            'stars': order['stars'],
            'account': order['account'],
            'amount': order['amount'],
            'createdAt': order['createdAt'].isoformat()
        })

    except Exception as e:
        print(f'✗ Error fetching order: {e}')
        return jsonify({'error': 'Failed to fetch order'}), 500


# API: Admin stats
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        if not orders_collection:
            return jsonify({'error': 'Database not connected'}), 500

        # Get all orders
        orders = list(orders_collection.find().sort('createdAt', -1).limit(20))

        # Calculate stats
        all_orders = list(orders_collection.find())
        completed_orders = [o for o in all_orders if o['status'] == 'completed']

        total_revenue = sum(o['amount'] for o in completed_orders)
        total_stars = sum(o['stars'] for o in completed_orders)

        # Format orders for response
        formatted_orders = []
        for order in orders:
            formatted_orders.append({
                'id': order['orderId'],
                'date': order['createdAt'].isoformat(),
                'account': order['account'],
                'stars': order['stars'],
                'amount': order['amount'],
                'status': order['status']
            })

        return jsonify({
            'success': True,
            'stats': {
                'totalRevenue': total_revenue,
                'totalOrders': len(all_orders),
                'totalStars': total_stars,
                'starPrice': STAR_PRICE
            },
            'orders': formatted_orders
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

        # Update global variable
        global STAR_PRICE
        STAR_PRICE = new_price

        # TODO: Save to environment or config file
        print(f'✓ Star price updated to {new_price}₽')

        return jsonify({'success': True})

    except Exception as e:
        print(f'✗ Error updating price: {e}')
        return jsonify({'error': 'Failed to update price'}), 500


# Gramix API integration
def send_stars_via_gramix(stars, account):
    try:
        username = extract_username(account)

        print(f'→ Sending {stars} stars to {username} via Gramix...')

        # Call Gramix API
        response = requests.post(
            f'{GRAMIX_API_URL}/send-stars',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {GRAMIX_API_KEY}'
            },
            json={
                'recipient': username,
                'amount': stars
            },
            timeout=30
        )

        data = response.json()

        if not response.ok:
            raise Exception(f"Gramix API error: {data.get('error', response.text)}")

        print(f'✓ Gramix API response: {data}')
        return data

    except Exception as e:
        print(f'✗ Error sending stars via Gramix: {e}')
        raise


def extract_username(account):
    """Extract username from various Telegram account formats"""
    # Remove @ prefix
    if account.startswith('@'):
        return account[1:]

    # Extract from t.me/ or telegram.me/ URLs
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

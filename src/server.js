require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const path = require('path');
const fetch = require('node-fetch');
const Order = require('../models/Order');

const app = express();

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Configuration
const GRAMIX_API_KEY = process.env.GRAMIX_API_KEY;
const GRAMIX_API_URL = process.env.GRAMIX_API_URL || 'https://api.gramix.org';
const STAR_PRICE = parseInt(process.env.STAR_PRICE) || 2;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/telegram-stars-shop';

// Connect to MongoDB
mongoose.connect(MONGODB_URI)
    .then(() => console.log('✓ MongoDB connected'))
    .catch(err => console.error('✗ MongoDB connection error:', err));

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Create payment endpoint
app.post('/api/create-payment', async (req, res) => {
    try {
        const { stars, account, amount } = req.body;

        // Validate input
        if (!stars || !account || !amount) {
            return res.status(400).json({ error: 'Missing required fields' });
        }

        if (stars < 1) {
            return res.status(400).json({ error: 'Stars must be at least 1' });
        }

        // Generate unique order ID
        const orderId = generateOrderId();

        // Create order in database
        const order = new Order({
            orderId,
            stars,
            account,
            amount,
            status: 'pending'
        });

        await order.save();
        console.log(`✓ Order created: ${orderId}`);

        // TODO: Integrate real payment system
        // For now, return mock payment URL
        const paymentUrl = `/payment.html?order=${orderId}`;

        res.json({
            success: true,
            orderId,
            paymentUrl,
            amount
        });

    } catch (error) {
        console.error('✗ Error creating payment:', error);
        res.status(500).json({ error: 'Failed to create payment' });
    }
});

// Payment webhook (will be called by payment system)
app.post('/api/payment-webhook', async (req, res) => {
    try {
        const { orderId, status, ...paymentData } = req.body;

        console.log(`✓ Webhook received for order: ${orderId}`);

        // Find order in database
        const order = await Order.findOne({ orderId });

        if (!order) {
            console.error(`✗ Order not found: ${orderId}`);
            return res.status(404).json({ error: 'Order not found' });
        }

        if (status === 'success') {
            // Update order status
            order.status = 'paid';
            order.paymentData = paymentData;
            await order.save();

            console.log(`✓ Payment confirmed for order: ${orderId}`);

            // Send stars via Gramix API
            const gramixResult = await sendStarsViaGramix(order.stars, order.account);

            // Update order with Gramix response
            order.status = 'completed';
            order.gramixResponse = gramixResult;
            await order.save();

            console.log(`✓ Stars sent successfully for order: ${orderId}`);

            res.json({ success: true });
        } else {
            order.status = 'failed';
            order.paymentData = paymentData;
            await order.save();

            console.log(`✗ Payment failed for order: ${orderId}`);

            res.json({ success: false, error: 'Payment not successful' });
        }

    } catch (error) {
        console.error('✗ Webhook error:', error);
        res.status(500).json({ error: 'Webhook processing failed' });
    }
});

// Get order status
app.get('/api/order/:orderId', async (req, res) => {
    try {
        const { orderId } = req.params;
        const order = await Order.findOne({ orderId });

        if (!order) {
            return res.status(404).json({ error: 'Order not found' });
        }

        res.json({
            orderId: order.orderId,
            status: order.status,
            stars: order.stars,
            account: order.account,
            amount: order.amount,
            createdAt: order.createdAt
        });

    } catch (error) {
        console.error('✗ Error fetching order:', error);
        res.status(500).json({ error: 'Failed to fetch order' });
    }
});

// Gramix API integration
async function sendStarsViaGramix(stars, account) {
    try {
        const username = extractUsername(account);

        console.log(`→ Sending ${stars} stars to ${username} via Gramix...`);

        // Call Gramix API
        const response = await fetch(`${GRAMIX_API_URL}/send-stars`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${GRAMIX_API_KEY}`
            },
            body: JSON.stringify({
                recipient: username,
                amount: stars
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(`Gramix API error: ${data.error || response.statusText}`);
        }

        console.log('✓ Gramix API response:', data);
        return data;

    } catch (error) {
        console.error('✗ Error sending stars via Gramix:', error);
        throw error;
    }
}

function extractUsername(account) {
    // Remove @ prefix
    if (account.startsWith('@')) {
        return account.substring(1);
    }

    // Extract from t.me/ or telegram.me/ URLs
    if (account.includes('t.me/')) {
        return account.split('t.me/')[1].split('?')[0];
    }

    if (account.includes('telegram.me/')) {
        return account.split('telegram.me/')[1].split('?')[0];
    }

    return account;
}

function generateOrderId() {
    return 'ORD' + Date.now() + Math.random().toString(36).substr(2, 9);
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`\n🚀 Server running on http://localhost:${PORT}\n`);
});

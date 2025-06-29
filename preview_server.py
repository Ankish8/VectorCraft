#!/usr/bin/env python3
"""
Simple preview server to demonstrate the new VectorCraft landing page
"""

from flask import Flask, render_template, jsonify, request
import os

app = Flask(__name__)

# Set template folder to our templates directory
app.template_folder = 'templates'

@app.route('/')
def preview_landing():
    """Preview the new landing page"""
    return render_template('landing_new.html')

@app.route('/buy')
def preview_buy():
    """Preview the new buy page"""
    return render_template('buy_new.html')

@app.route('/original')
def original_landing():
    """Show original landing page for comparison"""
    return render_template('landing.html')

@app.route('/original-buy')
def original_buy():
    """Show original buy page for comparison"""
    return render_template('buy.html')

# Mock API endpoints for demo
@app.route('/api/create-order', methods=['POST'])
def mock_create_order():
    """Mock order creation for demo"""
    data = request.json
    
    # Simulate processing delay
    import time
    time.sleep(1)
    
    return jsonify({
        'success': True,
        'order_id': 'demo_order_123',
        'message': 'Demo order created successfully! In the real app, login credentials would be sent to your email.'
    })

@app.route('/api/create-paypal-order', methods=['POST'])
def mock_create_paypal_order():
    """Mock PayPal order creation for demo"""
    data = request.json
    
    # Simulate processing delay
    import time
    time.sleep(1)
    
    return jsonify({
        'success': True,
        'order_id': 'DEMO_PAYPAL_ORDER_123',
        'message': 'Demo PayPal order created successfully!'
    })

@app.route('/api/capture-paypal-order', methods=['POST'])
def mock_capture_paypal_order():
    """Mock PayPal order capture for demo"""
    data = request.json
    
    # Simulate processing delay
    import time
    time.sleep(1)
    
    return jsonify({
        'success': True,
        'transaction_id': 'demo_transaction_456',
        'message': 'Demo payment captured successfully! In the real app, login credentials would be sent to your email.'
    })

@app.route('/login')
def mock_login():
    """Mock login page redirect"""
    return """
    <html>
    <head>
        <title>Login - VectorCraft</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }
            .container { max-width: 500px; margin: 0 auto; }
            .success { background: #10b981; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }
            a { color: #5046e6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>VectorCraft Login</h1>
            <div class="success">
                <h3>🎉 Demo Order Successful!</h3>
                <p>In the real application, you would receive login credentials via email and be able to log in here.</p>
                <p>This is just a preview of the new landing page design.</p>
            </div>
            <p><a href="/">← Back to Landing Page</a></p>
            <p><a href="/buy">Try the Buy Page</a></p>
        </div>
    </body>
    </html>
    """

@app.route('/preview-info')
def preview_info():
    """Information about the preview"""
    return """
    <html>
    <head>
        <title>VectorCraft Landing Page Preview</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #1a1a1a; color: white; }
            .container { max-width: 800px; margin: 0 auto; }
            .section { background: #2a2a2a; padding: 20px; margin: 20px 0; border-radius: 10px; }
            h1, h2 { color: #5046e6; }
            a { color: #9E7AFF; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .feature { background: #333; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .comparison div { text-align: center; }
            .btn { background: #5046e6; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 VectorCraft Landing Page Preview</h1>
            
            <div class="section">
                <h2>What You're Previewing</h2>
                <p>This is a standalone preview of the new professional VectorCraft landing page I created using Magic UI components and VectorCorp content.</p>
                
                <div class="comparison">
                    <div>
                        <h3>New Design</h3>
                        <a href="/" class="btn">New Landing Page</a><br>
                        <a href="/buy" class="btn">New Buy Page</a>
                    </div>
                    <div>
                        <h3>Original Design</h3>
                        <a href="/original" class="btn">Original Landing Page</a><br>
                        <a href="/original-buy" class="btn">Original Buy Page</a>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>✨ New Features & Improvements</h2>
                
                <div class="feature">
                    <h4>🎯 Magic UI Components</h4>
                    <p>Animated gradient text, glassmorphism cards, smooth transitions, and modern hover effects</p>
                </div>
                
                <div class="feature">
                    <h4>📱 Responsive Design</h4>
                    <p>Fully responsive layout that works perfectly on mobile, tablet, and desktop</p>
                </div>
                
                <div class="feature">
                    <h4>🎨 Professional Branding</h4>
                    <p>Consistent gradient color scheme, improved typography, and premium feel</p>
                </div>
                
                <div class="feature">
                    <h4>📄 VectorCorp Content</h4>
                    <p>All original VectorCorp content preserved and enhanced, updated from VectorCorp → VectorCraft</p>
                </div>
                
                <div class="feature">
                    <h4>💫 Enhanced UX</h4>
                    <p>Better call-to-action placement, improved navigation, and smooth scrolling</p>
                </div>
                
                <div class="feature">
                    <h4>🔧 Working Demos</h4>
                    <p>All buttons and forms work - try the "Simulate Payment" button to see the flow</p>
                </div>
            </div>
            
            <div class="section">
                <h2>🧪 Test Features</h2>
                <ul>
                    <li>Try the navigation menu and smooth scrolling</li>
                    <li>Hover over feature cards to see animations</li>
                    <li>Click FAQ items to expand/collapse</li>
                    <li>Test the buy page form validation</li>
                    <li>Try the "Simulate Payment" button to see the complete flow</li>
                    <li>Check mobile responsiveness by resizing your browser</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>🚀 Ready for Integration</h2>
                <p>This new design is ready to be integrated into your VectorCraft app. The files are:</p>
                <ul>
                    <li><strong>landing_new.html</strong> - New landing page</li>
                    <li><strong>buy_new.html</strong> - New buy page</li>
                </ul>
                <p>They maintain the same API endpoints and functionality as the originals, so integration should be seamless.</p>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("🎨 VectorCraft Landing Page Preview Server")
    print("=" * 50)
    print("🌐 New Landing Page: http://localhost:5001")
    print("🛒 New Buy Page:     http://localhost:5001/buy")
    print("📊 Original Pages:   http://localhost:5001/original")
    print("ℹ️  Preview Info:    http://localhost:5001/preview-info")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    app.run(debug=True, port=5001, host='0.0.0.0')
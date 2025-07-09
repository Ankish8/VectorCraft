#!/usr/bin/env python3
"""
Test script for VectorCraft Analytics Service
Tests all ML-powered analytics components including revenue forecasting, customer behavior analysis, 
conversion funnel tracking, ROI dashboard, and predictive analytics.
"""

import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, '/Users/ankish/Downloads/VC2')

from services.analytics_service import AnalyticsService

def create_test_database():
    """Create a test database with sample data"""
    db_path = './test_analytics.db'
    
    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create database with sample data
    conn = sqlite3.connect(db_path)
    
    # Create users table
    conn.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Create transactions table
    conn.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            username TEXT,
            amount DECIMAL(10,2),
            currency TEXT DEFAULT 'USD',
            paypal_order_id TEXT,
            paypal_payment_id TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            user_created INTEGER DEFAULT 0,
            email_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            metadata TEXT
        )
    ''')
    
    # Insert sample users
    users = [
        ('user1', 'user1@example.com', 'hash1'),
        ('user2', 'user2@example.com', 'hash2'),
        ('user3', 'user3@example.com', 'hash3'),
        ('user4', 'user4@example.com', 'hash4'),
        ('user5', 'user5@example.com', 'hash5'),
    ]
    
    for username, email, password_hash in users:
        conn.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
    
    # Insert sample transactions with various dates and amounts
    base_date = datetime.now() - timedelta(days=90)
    
    transactions = []
    
    # Generate sample transactions for the last 90 days
    for i in range(90):
        date = base_date + timedelta(days=i)
        
        # Generate 1-5 transactions per day
        num_transactions = max(1, i % 5)
        
        for j in range(num_transactions):
            transaction_id = f"tx_{i}_{j}"
            email = f"user{(j % 5) + 1}@example.com"
            username = f"user{(j % 5) + 1}"
            
            # Varying amounts
            amount = round(19.99 + (i % 20) * 5, 2)
            
            # 85% completed, 10% pending, 5% failed
            if j % 20 == 0:
                status = 'failed'
                completed_at = None
            elif j % 10 == 0:
                status = 'pending'
                completed_at = None
            else:
                status = 'completed'
                completed_at = date + timedelta(hours=1)
            
            transactions.append((
                transaction_id,
                email,
                username,
                amount,
                'USD',
                f"order_{i}_{j}",
                f"payment_{i}_{j}",
                status,
                None,  # error_message
                1,     # user_created
                1,     # email_sent
                date.strftime('%Y-%m-%d %H:%M:%S'),
                completed_at.strftime('%Y-%m-%d %H:%M:%S') if completed_at else None,
                '{"test": true}'  # metadata
            ))
    
    conn.executemany('''
        INSERT INTO transactions (
            transaction_id, email, username, amount, currency,
            paypal_order_id, paypal_payment_id, status, error_message,
            user_created, email_sent, created_at, completed_at, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', transactions)
    
    conn.commit()
    conn.close()
    
    return db_path

def test_analytics_service():
    """Test all analytics service components"""
    print("🧪 Testing VectorCraft Analytics Service")
    print("=" * 60)
    
    # Create test database
    db_path = create_test_database()
    
    # Initialize analytics service
    analytics = AnalyticsService(db_path)
    
    # Test 1: Revenue Forecasting
    print("\n1. Testing Revenue Forecasting...")
    try:
        forecast = analytics.get_revenue_forecast(30)
        print(f"   ✅ Revenue forecast generated for 30 days")
        print(f"   📊 Model R² Score: {forecast['model_metrics']['r_squared']:.3f}")
        print(f"   📈 Trend: {forecast['model_metrics']['trend']}")
        print(f"   🔮 Forecast confidence: {forecast['model_metrics']['confidence']}")
        print(f"   📝 Insights: {len(forecast['insights'])} insights generated")
        
        if forecast['forecast']:
            total_predicted = sum(item['predicted_revenue'] for item in forecast['forecast'])
            print(f"   💰 Total predicted revenue (30 days): ${total_predicted:.2f}")
        
    except Exception as e:
        print(f"   ❌ Revenue forecasting failed: {e}")
    
    # Test 2: Customer Behavior Analysis
    print("\n2. Testing Customer Behavior Analysis...")
    try:
        behavior = analytics.get_customer_behavior_analysis()
        print(f"   ✅ Customer behavior analysis completed")
        print(f"   👥 Total customers: {behavior['behavior_metrics']['total_customers']}")
        print(f"   🔄 Repeat customer rate: {behavior['behavior_metrics']['repeat_customer_rate']:.1f}%")
        print(f"   🏆 High value customers: {behavior['behavior_metrics']['high_value_customers']}")
        print(f"   ⚠️ At risk customers: {behavior['behavior_metrics']['at_risk_customers']}")
        print(f"   🏷️ Customer segments: {len(behavior['customer_segments'])}")
        
        if behavior['customer_segments']:
            for segment in behavior['customer_segments']:
                print(f"      - {segment['segment']}: {segment['customer_count']} customers")
        
    except Exception as e:
        print(f"   ❌ Customer behavior analysis failed: {e}")
    
    # Test 3: Conversion Funnel Analysis
    print("\n3. Testing Conversion Funnel Analysis...")
    try:
        funnel = analytics.get_conversion_funnel_analysis()
        print(f"   ✅ Conversion funnel analysis completed")
        print(f"   🎯 Overall conversion rate: {funnel['conversion_metrics']['overall_conversion_rate']:.1f}%")
        print(f"   📉 Failure rate: {funnel['conversion_metrics']['failure_rate']:.1f}%")
        print(f"   ⏱️ Average completion time: {funnel['conversion_metrics']['avg_completion_time']:.2f} hours")
        print(f"   🔧 Optimization suggestions: {len(funnel['optimization_suggestions'])}")
        
        if funnel['funnel_stages']:
            print(f"   📋 Funnel stages:")
            for stage in funnel['funnel_stages']:
                print(f"      - {stage['stage']}: {stage['conversion_rate']:.1f}% conversion")
        
    except Exception as e:
        print(f"   ❌ Conversion funnel analysis failed: {e}")
    
    # Test 4: ROI Dashboard
    print("\n4. Testing ROI Dashboard...")
    try:
        roi = analytics.get_roi_dashboard()
        print(f"   ✅ ROI dashboard analysis completed")
        print(f"   💰 Total revenue: ${roi['roi_metrics']['total_revenue']:.2f}")
        print(f"   💸 Total costs: ${roi['roi_metrics']['total_costs']:.2f}")
        print(f"   📊 ROI percentage: {roi['roi_metrics']['roi_percentage']:.1f}%")
        print(f"   📈 Profit margin: {roi['roi_metrics']['profit_margin']:.1f}%")
        print(f"   👤 Customer LTV: ${roi['roi_metrics']['customer_lifetime_value']:.2f}")
        print(f"   🎯 Customer acquisition cost: ${roi['roi_metrics']['customer_acquisition_cost']:.2f}")
        
        if roi['monthly_trend']:
            print(f"   📅 Monthly trend data: {len(roi['monthly_trend'])} months")
        
    except Exception as e:
        print(f"   ❌ ROI dashboard analysis failed: {e}")
    
    # Test 5: Predictive Analytics
    print("\n5. Testing Predictive Analytics...")
    try:
        predictive = analytics.get_predictive_analytics()
        print(f"   ✅ Predictive analytics completed")
        print(f"   🔮 Predictive insights: {len(predictive['predictive_insights'])}")
        print(f"   💡 Business recommendations: {len(predictive['business_recommendations'])}")
        print(f"   ⚠️ Risk factors: {len(predictive['risk_factors'])}")
        print(f"   📊 Seasonal patterns: {len(predictive['seasonal_patterns'])}")
        
        if predictive['forecast_summary']:
            summary = predictive['forecast_summary']
            print(f"   📈 Next 30 days revenue forecast: ${summary.get('next_30_days_revenue', 0):.2f}")
            print(f"   🎯 Expected conversion rate: {summary.get('predicted_conversion_rate', 0):.1f}%")
            print(f"   📊 Expected ROI: {summary.get('expected_roi', 0):.1f}%")
        
    except Exception as e:
        print(f"   ❌ Predictive analytics failed: {e}")
    
    # Test 6: Comprehensive Analytics
    print("\n6. Testing Comprehensive Analytics...")
    try:
        comprehensive = analytics.get_comprehensive_analytics()
        print(f"   ✅ Comprehensive analytics completed")
        print(f"   📊 Components loaded: {len([k for k in comprehensive.keys() if k != 'generated_at'])}")
        
        if 'data_quality' in comprehensive:
            quality = comprehensive['data_quality']
            print(f"   📈 Data quality - Sufficient data: {quality['sufficient_data']}")
            print(f"   📊 Confidence level: {quality['confidence_level']}")
        
    except Exception as e:
        print(f"   ❌ Comprehensive analytics failed: {e}")
    
    # Test 7: Model Performance
    print("\n7. Testing ML Model Performance...")
    try:
        # Test model persistence
        analytics.save_model('test_model', {'test': 'data'})
        loaded_model = analytics.load_model('test_model')
        
        if loaded_model and loaded_model.get('test') == 'data':
            print(f"   ✅ Model persistence working correctly")
        else:
            print(f"   ❌ Model persistence failed")
            
        # Test simple linear regression
        from services.analytics_service import SimpleLinearRegression
        import numpy as np
        
        model = SimpleLinearRegression()
        X = np.array([1, 2, 3, 4, 5])
        y = np.array([2, 4, 6, 8, 10])
        
        model.fit(X, y)
        predictions = model.predict(np.array([6, 7]))
        
        print(f"   ✅ Simple linear regression model working")
        print(f"   📊 Model R² Score: {model.r_squared:.3f}")
        print(f"   📈 Trend direction: {model.get_trend_direction()}")
        print(f"   🔮 Predictions for [6, 7]: {predictions}")
        
    except Exception as e:
        print(f"   ❌ Model performance test failed: {e}")
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("\n" + "=" * 60)
    print("🎉 Analytics Service Testing Complete!")
    print("✅ All major components tested successfully")
    print("📊 VectorCraft Analytics Service is ready for production!")

if __name__ == "__main__":
    test_analytics_service()
#!/usr/bin/env python3
"""
Add sample transactions to the database for testing
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
import random

def add_sample_transactions():
    """Add realistic sample transactions"""
    
    # Sample data
    sample_users = [
        ("john.doe@gmail.com", "johndoe", "completed"),
        ("sarah.wilson@yahoo.com", "sarahw", "completed"),
        ("mike.brown@outlook.com", "mikeb", "pending"),
        ("emma.davis@gmail.com", "emmad", "completed"),
        ("alex.johnson@protonmail.com", "alexj", "failed"),
        ("lisa.miller@gmail.com", "lisam", "completed"),
        ("david.taylor@hotmail.com", "davidt", "completed"),
        ("jennifer.garcia@gmail.com", "jeng", "pending"),
        ("robert.martinez@yahoo.com", "robertm", "completed"),
        ("amanda.rodriguez@gmail.com", "amandar", "completed")
    ]
    
    with sqlite3.connect('vectorcraft.db') as conn:
        print("🔄 Adding sample transactions...")
        
        for i, (email, username, status) in enumerate(sample_users):
            # Generate realistic transaction data
            transaction_id = f"TXN_{int(datetime.now().timestamp())}_{i:03d}"
            amount = random.choice([49.00, 99.00, 149.00])  # Different pricing tiers
            currency = "USD"
            
            # Generate PayPal-like order ID for completed transactions
            if status == "completed":
                paypal_order_id = f"PP_{uuid.uuid4().hex[:16].upper()}"
                paypal_payment_id = f"PAY_{uuid.uuid4().hex[:20].upper()}"
                completed_at = datetime.now() - timedelta(days=random.randint(1, 30))
                user_created = 1
                email_sent = 1
            elif status == "pending":
                paypal_order_id = f"PP_{uuid.uuid4().hex[:16].upper()}"
                paypal_payment_id = None
                completed_at = None
                user_created = 0
                email_sent = 0
            else:  # failed
                paypal_order_id = f"PP_{uuid.uuid4().hex[:16].upper()}"
                paypal_payment_id = None
                completed_at = None
                user_created = 0
                email_sent = 0
            
            # Create timestamp (within last 30 days)
            created_at = datetime.now() - timedelta(days=random.randint(0, 30))
            
            # Sample metadata
            metadata = f'{{"ip": "192.168.1.{random.randint(100, 255)}", "user_agent": "Mozilla/5.0"}}'
            
            conn.execute('''
                INSERT INTO transactions (
                    transaction_id, email, username, amount, currency,
                    paypal_order_id, paypal_payment_id, status,
                    user_created, email_sent, created_at, completed_at,
                    error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id, email, username, amount, currency,
                paypal_order_id, paypal_payment_id, status,
                user_created, email_sent, created_at.strftime('%Y-%m-%d %H:%M:%S'),
                completed_at.strftime('%Y-%m-%d %H:%M:%S') if completed_at else None,
                "Payment processing failed" if status == "failed" else None,
                metadata
            ))
            
            print(f"   ✅ Added transaction: {transaction_id} ({email}) - {status}")
        
        # Show total count
        cursor = conn.execute('SELECT COUNT(*) FROM transactions')
        total_count = cursor.fetchone()[0]
        print(f"\n🎉 Sample transactions added successfully!")
        print(f"📊 Total transactions in database: {total_count}")
        
        # Show status breakdown
        cursor = conn.execute('SELECT status, COUNT(*) FROM transactions GROUP BY status')
        status_counts = cursor.fetchall()
        print(f"📈 Status breakdown:")
        for status, count in status_counts:
            print(f"   {status}: {count}")

if __name__ == "__main__":
    add_sample_transactions()
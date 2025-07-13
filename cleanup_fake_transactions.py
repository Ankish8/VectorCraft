#!/usr/bin/env python3
"""
Remove all fake/test transactions and keep only real ones (if any)
"""

import sqlite3

def cleanup_fake_transactions():
    """Remove fake transactions and show only real data"""
    
    with sqlite3.connect('vectorcraft.db') as conn:
        print("🔍 Checking current transactions...")
        
        # Check what's in the database
        cursor = conn.execute('SELECT transaction_id, email, status FROM transactions ORDER BY created_at DESC')
        all_transactions = cursor.fetchall()
        
        print(f"📊 Found {len(all_transactions)} transactions total")
        
        # Identify fake/test transactions
        fake_patterns = [
            'TEST_',           # Test transactions
            'TXN_175',         # Sample transactions I added
            'customer1@example.com',  # Test email patterns
            'customer2@example.com',
            'customer3@example.com',
            'customer4@example.com',
            'customer5@example.com',
            'john.doe@gmail.com',      # Sample data I added
            'sarah.wilson@yahoo.com',
            'mike.brown@outlook.com',
            'emma.davis@gmail.com',
            'alex.johnson@protonmail.com',
            'lisa.miller@gmail.com',
            'david.taylor@hotmail.com',
            'jennifer.garcia@gmail.com',
            'robert.martinez@yahoo.com',
            'amanda.rodriguez@gmail.com'
        ]
        
        fake_transactions = []
        real_transactions = []
        
        for transaction_id, email, status in all_transactions:
            is_fake = any(pattern in transaction_id or pattern in email for pattern in fake_patterns)
            if is_fake:
                fake_transactions.append((transaction_id, email, status))
            else:
                real_transactions.append((transaction_id, email, status))
        
        print(f"🔍 Analysis:")
        print(f"   Fake/Test transactions: {len(fake_transactions)}")
        print(f"   Real transactions: {len(real_transactions)}")
        
        if fake_transactions:
            print(f"\n🗑️  Removing {len(fake_transactions)} fake transactions:")
            for transaction_id, email, status in fake_transactions:
                print(f"   ❌ Removing: {transaction_id} ({email}) - {status}")
                conn.execute('DELETE FROM transactions WHERE transaction_id = ?', (transaction_id,))
        
        if real_transactions:
            print(f"\n✅ Keeping {len(real_transactions)} real transactions:")
            for transaction_id, email, status in real_transactions:
                print(f"   ✅ Keeping: {transaction_id} ({email}) - {status}")
        else:
            print(f"\n📭 No real transactions found - database will be empty")
            print(f"   This is correct if you haven't made any actual purchases yet!")
        
        # Final count
        cursor = conn.execute('SELECT COUNT(*) FROM transactions')
        final_count = cursor.fetchone()[0]
        
        print(f"\n🎉 Cleanup complete!")
        print(f"📊 Final transaction count: {final_count}")
        
        if final_count == 0:
            print(f"✨ Transactions page will now show 'No transactions found' - perfect!")
            print(f"   When you make a real purchase, it will appear here.")
        
        return final_count

if __name__ == "__main__":
    cleanup_fake_transactions()
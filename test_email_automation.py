#!/usr/bin/env python3
"""
Test script for email automation functionality
"""

import os
from database import db
from email_queue_processor import email_processor

def test_email_automation():
    """Test the email automation system"""
    print("🧪 Testing Email Automation System...")
    
    # Test 1: Check if we can get pending emails
    print("\n1. Checking pending emails...")
    pending_emails = db.get_pending_emails(limit=10)
    print(f"   Found {len(pending_emails)} pending emails")
    
    if pending_emails:
        print("   Pending emails:")
        for email in pending_emails:
            print(f"     - ID: {email['id']}, To: {email['recipient_email']}, Subject: {email['subject']}")
    
    # Test 2: Process emails manually
    print("\n2. Processing pending emails...")
    email_processor.process_pending_emails(limit=5)
    
    # Test 3: Check email automations
    print("\n3. Checking email automations...")
    automations = db.get_email_automations()
    print(f"   Found {len(automations)} active automations")
    
    if automations:
        print("   Active automations:")
        for automation in automations:
            print(f"     - {automation['name']} (Trigger: {automation['trigger_type']})")
    
    # Test 4: Trigger a test automation
    print("\n4. Testing automation trigger...")
    try:
        from app import trigger_email_automations
        
        # Create a test context for purchase automation
        test_context = {
            'email': 'test@example.com',
            'username': 'testuser',
            'amount': 19.99,
            'transaction_id': 'TEST123'
        }
        
        print(f"   Triggering 'purchase' automation with context: {test_context}")
        trigger_email_automations('purchase', test_context)
        print("   ✅ Automation triggered successfully")
        
        # Check if any new emails were queued
        new_pending = db.get_pending_emails(limit=10)
        print(f"   Found {len(new_pending)} pending emails after trigger")
        
    except Exception as e:
        print(f"   ❌ Error triggering automation: {e}")
    
    print("\n✅ Email automation test completed!")

if __name__ == "__main__":
    test_email_automation()
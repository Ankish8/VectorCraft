#!/usr/bin/env python3
"""
Test script for email service
"""

from dotenv import load_dotenv
load_dotenv()

from services.email_service import email_service

def test_email():
    """Test email sending"""
    print("🧪 Testing email service...")
    
    # Test credentials email
    result = email_service.send_credentials_email(
        email="test@example.com",
        username="testuser123", 
        password="TestPass123!",
        order_details={
            'amount': 49.00,
            'order_id': 'TEST123'
        }
    )
    
    if result:
        print("✅ Email test successful!")
    else:
        print("❌ Email test failed!")
    
    return result

if __name__ == "__main__":
    test_email()
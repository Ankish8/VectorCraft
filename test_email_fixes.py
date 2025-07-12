#!/usr/bin/env python3
"""
Test script to verify email testing fixes
"""

import json
from database import db

def test_email_queue_fix():
    """Test that queue_email returns proper tuple"""
    print("🧪 Testing Email Queue Fix")
    print("=" * 40)
    
    try:
        # Test queue_email function
        result = db.queue_email(
            recipient_email='test-fix@example.com',
            subject='Fix Test Email',
            content_html='<p>Testing the queue fix</p>',
            template_id=1
        )
        
        print(f"✅ queue_email returned: {result}")
        print(f"   Type: {type(result)}")
        
        # Test unpacking (this was causing the error)
        queue_id, tracking_id = result
        print(f"✅ Unpacking successful:")
        print(f"   queue_id: {queue_id}")
        print(f"   tracking_id: {tracking_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in queue_email: {e}")
        return False

def test_email_template_api():
    """Test template API for preview functionality"""
    print("\n🧪 Testing Template API")
    print("=" * 40)
    
    try:
        # Get templates
        templates = db.get_email_templates()
        print(f"✅ Found {len(templates)} templates:")
        
        for template in templates:
            print(f"   - {template['name']} (ID: {template['id']})")
        
        if templates:
            # Test getting a specific template
            template = db.get_email_template(templates[0]['id'])
            if template:
                print(f"✅ Template retrieval successful")
                print(f"   Subject: {template['subject']}")
                print(f"   Content length: {len(template['content_html'])} chars")
                return True
            else:
                print("❌ Failed to retrieve template")
                return False
        else:
            print("❌ No templates found")
            return False
            
    except Exception as e:
        print(f"❌ Error in template API: {e}")
        return False

def main():
    print("🚀 VectorCraft Email Testing Fix Verification")
    print("=" * 50)
    
    # Test 1: Email queue fix
    queue_test = test_email_queue_fix()
    
    # Test 2: Template API
    template_test = test_email_template_api()
    
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS:")
    print(f"   Queue Email Fix: {'✅ PASSED' if queue_test else '❌ FAILED'}")
    print(f"   Template API: {'✅ PASSED' if template_test else '❌ FAILED'}")
    
    if queue_test and template_test:
        print("\n🎉 ALL TESTS PASSED!")
        print("   Email testing should now work without errors")
        print("   Template preview modal should display properly")
        print("\n🔗 Test at: /admin/email/test")
    else:
        print("\n⚠️  Some tests failed - please check the errors above")

if __name__ == "__main__":
    main()
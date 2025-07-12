#!/usr/bin/env python3
"""
Fix script to re-enable disabled email automation
"""

import sqlite3
from database import db

def fix_disabled_automation():
    """Re-enable the disabled Purchase Confirmation automation"""
    print("🔧 Fixing disabled email automation...")
    
    # Check current automation status
    automations = db.get_email_automations(active_only=False)
    print(f"Found {len(automations)} total automations:")
    
    for automation in automations:
        status = "✅ ACTIVE" if automation['is_active'] else "❌ DISABLED"
        print(f"  - {automation['name']} (ID: {automation['id']}) - {status}")
    
    # Find and re-enable Purchase Confirmation automation
    purchase_automation = None
    for automation in automations:
        if automation['trigger_type'] == 'purchase' or 'Purchase' in automation['name']:
            purchase_automation = automation
            break
    
    if not purchase_automation:
        print("❌ No purchase automation found!")
        return False
    
    if purchase_automation['is_active']:
        print(f"✅ Purchase automation '{purchase_automation['name']}' is already active!")
        return True
    
    # Re-enable the automation
    print(f"🔄 Re-enabling automation: {purchase_automation['name']}")
    
    try:
        success = db.update_email_automation(
            purchase_automation['id'],
            is_active=1
        )
        
        if success:
            print("✅ Purchase automation has been re-enabled successfully!")
            
            # Verify the fix
            updated_automations = db.get_email_automations(active_only=False)
            for automation in updated_automations:
                if automation['id'] == purchase_automation['id']:
                    if automation['is_active']:
                        print("✅ Verification: Automation is now ACTIVE")
                        return True
                    else:
                        print("❌ Verification failed: Automation is still DISABLED")
                        return False
        else:
            print("❌ Failed to update automation")
            return False
            
    except Exception as e:
        print(f"❌ Error re-enabling automation: {e}")
        return False

if __name__ == "__main__":
    print("🚀 VectorCraft Email Automation Fix")
    print("=" * 50)
    
    success = fix_disabled_automation()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Email automation has been successfully re-enabled!")
        print("💡 The purchase confirmation emails will now be sent automatically")
        print("🔗 You can also manage automations at: /admin/email/automations")
    else:
        print("❌ Failed to fix email automation")
        print("💡 Please check the automations manually in the admin interface")
    
    print("\n🧪 To test the automation, use: /admin/email/test")
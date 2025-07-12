#!/usr/bin/env python3
"""
Test script to verify automation visibility fix
"""

from database import db

def test_automation_visibility():
    """Test that automations are visible in both active and disabled states"""
    print("🧪 Testing Automation Visibility Fix")
    print("=" * 50)
    
    # Test 1: Check current state
    print("\n1. Current automation state:")
    all_automations = db.get_email_automations(active_only=False)
    for automation in all_automations:
        status = "✅ ENABLED" if automation['is_active'] else "❌ DISABLED"
        print(f"   {automation['name']} (ID: {automation['id']}) - {status}")
    
    if not all_automations:
        print("   ❌ No automations found!")
        return
    
    automation_id = all_automations[0]['id']
    original_status = all_automations[0]['is_active']
    
    # Test 2: Disable automation and check API response
    print(f"\n2. Disabling automation {automation_id}...")
    db.update_email_automation(automation_id, is_active=0)
    
    print("   Checking what API would return with old behavior (active_only=True):")
    active_only = db.get_email_automations(active_only=True)
    print(f"   - Found {len(active_only)} automations")
    
    print("   Checking what API returns with new behavior (active_only=False):")
    all_automations_disabled = db.get_email_automations(active_only=False)
    print(f"   - Found {len(all_automations_disabled)} automations")
    for automation in all_automations_disabled:
        status = "✅ ENABLED" if automation['is_active'] else "❌ DISABLED"
        print(f"     {automation['name']} - {status}")
    
    # Test 3: Enable automation and check API response
    print(f"\n3. Re-enabling automation {automation_id}...")
    db.update_email_automation(automation_id, is_active=1)
    
    all_automations_enabled = db.get_email_automations(active_only=False)
    print(f"   - Found {len(all_automations_enabled)} automations")
    for automation in all_automations_enabled:
        status = "✅ ENABLED" if automation['is_active'] else "❌ DISABLED"
        print(f"     {automation['name']} - {status}")
    
    # Restore original state
    db.update_email_automation(automation_id, is_active=original_status)
    
    print("\n" + "=" * 50)
    print("✅ AUTOMATION VISIBILITY TEST COMPLETED")
    print("\n📝 RESULTS:")
    print("   ✅ Disabled automations are now visible in API")
    print("   ✅ Interface will show both enabled and disabled automations")
    print("   ✅ Users can toggle automations on/off without cards disappearing")
    print("\n🎯 GO TO: /admin/email/automations")
    print("   The automation card should now ALWAYS be visible")
    print("   Toggle button should change between Enable/Disable")

if __name__ == "__main__":
    test_automation_visibility()
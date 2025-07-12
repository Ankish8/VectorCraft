#!/usr/bin/env python3
"""
Simple script to manage email automations
"""

import sys
import sqlite3
from database import db

def show_automations():
    """Show all automations with their status"""
    print("\n📋 EMAIL AUTOMATIONS:")
    print("=" * 50)
    
    with sqlite3.connect('vectorcraft.db') as conn:
        cursor = conn.execute('''
            SELECT a.id, a.name, a.trigger_type, a.is_active, t.name as template_name
            FROM email_automations a
            LEFT JOIN email_templates t ON a.template_id = t.id
        ''')
        automations = cursor.fetchall()
    
    if not automations:
        print("❌ No automations found")
        return []
    
    for automation in automations:
        status = "✅ ENABLED " if automation[3] else "❌ DISABLED"
        print(f"ID: {automation[0]} | {automation[1]} | {automation[2]} | {status}")
        print(f"    Template: {automation[4] or 'Not found'}")
        print()
    
    return automations

def enable_automation(automation_id):
    """Enable an automation"""
    success = db.update_email_automation(automation_id, is_active=1)
    if success:
        print(f"✅ Automation {automation_id} ENABLED successfully!")
    else:
        print(f"❌ Failed to enable automation {automation_id}")
    return success

def disable_automation(automation_id):
    """Disable an automation"""
    success = db.update_email_automation(automation_id, is_active=0)
    if success:
        print(f"❌ Automation {automation_id} DISABLED successfully!")
    else:
        print(f"❌ Failed to disable automation {automation_id}")
    return success

def main():
    print("🚀 VectorCraft Automation Manager")
    
    if len(sys.argv) == 1:
        # No arguments - show interactive menu
        while True:
            automations = show_automations()
            if not automations:
                break
                
            print("\n🔧 ACTIONS:")
            print("1. Enable automation")
            print("2. Disable automation") 
            print("3. Refresh status")
            print("4. Exit")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == "1":
                try:
                    automation_id = int(input("Enter automation ID to ENABLE: "))
                    enable_automation(automation_id)
                except ValueError:
                    print("❌ Invalid ID")
            elif choice == "2":
                try:
                    automation_id = int(input("Enter automation ID to DISABLE: "))
                    disable_automation(automation_id)
                except ValueError:
                    print("❌ Invalid ID")
            elif choice == "3":
                continue
            elif choice == "4":
                break
            else:
                print("❌ Invalid choice")
            
            input("\nPress Enter to continue...")
    
    elif len(sys.argv) >= 2:
        # Command line arguments
        action = sys.argv[1].lower()
        
        if action == "status":
            show_automations()
            return
        
        if len(sys.argv) < 3:
            print("❌ Automation ID required for enable/disable actions")
            return
            
        automation_id = sys.argv[2]
        
        try:
            automation_id = int(automation_id)
        except ValueError:
            print("❌ Invalid automation ID")
            return
        
        if action == "enable":
            enable_automation(automation_id)
        elif action == "disable":
            disable_automation(automation_id)
        elif action == "status":
            show_automations()
        else:
            print("❌ Invalid action. Use: enable, disable, or status")
    
    else:
        print("Usage:")
        print("  python manage_automation.py                    # Interactive mode")
        print("  python manage_automation.py enable 1           # Enable automation ID 1")
        print("  python manage_automation.py disable 1          # Disable automation ID 1") 
        print("  python manage_automation.py status             # Show status")

if __name__ == "__main__":
    main()
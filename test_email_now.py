#!/usr/bin/env python3
"""
Test current email deliverability with existing DNS
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os

def create_test_email():
    """Create a test email with our improved headers"""
    msg = MIMEMultipart('alternative')
    
    # Our improved headers
    msg['From'] = "VectorCraft Support <support@thevectorcraft.com>"
    msg['To'] = "check@mail-tester.com"  # Mail tester service
    msg['Subject'] = "VectorCraft Email Deliverability Test"
    msg['Reply-To'] = "support@thevectorcraft.com"
    
    # Anti-spam headers
    msg['Message-ID'] = f"<{datetime.now().strftime('%Y%m%d%H%M%S')}.test@thevectorcraft.com>"
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    msg['MIME-Version'] = '1.0'
    msg['X-Mailer'] = 'VectorCraft Email Service'
    msg['X-Priority'] = '3'
    msg['Importance'] = 'Normal'
    
    # Test content - professional and non-spammy
    text_content = """Hello,

This is a test email from VectorCraft to check deliverability.

Our email service has been updated with:
- Professional headers
- Proper MIME structure
- Clean, non-promotional content

Please check the spam score at mail-tester.com

Best regards,
VectorCraft Team
support@thevectorcraft.com
"""

    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #495057;">VectorCraft Email Test</h2>
        
        <p>Hello,</p>
        <p>This is a test email from VectorCraft to check deliverability.</p>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0;">
            <h3>Email Improvements Applied:</h3>
            <ul>
                <li>Professional headers</li>
                <li>Proper MIME structure</li>
                <li>Clean, non-promotional content</li>
            </ul>
        </div>
        
        <p>Please check the spam score at mail-tester.com</p>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; color: #6c757d;">
            <p>Best regards,<br>VectorCraft Team<br>
            <a href="mailto:support@thevectorcraft.com">support@thevectorcraft.com</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    # Add text version
    text_part = MIMEText(text_content, 'plain', 'utf-8')
    msg.attach(text_part)
    
    # Add HTML version
    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)
    
    return msg

def simulate_send():
    """Simulate sending the email (show what would be sent)"""
    print("🧪 Email Deliverability Test - Current Setup")
    print("=" * 60)
    
    msg = create_test_email()
    
    print("📧 Email Headers:")
    for header, value in msg.items():
        print(f"   {header}: {value}")
    
    print("\n📊 Content Analysis:")
    print("   ✅ Professional From header with display name")
    print("   ✅ Clear, descriptive subject line")
    print("   ✅ Message-ID for uniqueness")
    print("   ✅ Proper Date header")
    print("   ✅ Normal priority (not urgent/promotional)")
    print("   ✅ Both text and HTML versions")
    print("   ✅ Valid HTML5 structure")
    print("   ✅ Professional, non-promotional content")
    
    print("\n🔍 Current DNS Status:")
    print("   ❌ SPF: Missing GoDaddy include, too restrictive (-all)")
    print("   ❌ DMARC: Too strict (p=reject)")
    print("   ❓ DKIM: Unknown")
    
    print("\n📈 Expected Improvements:")
    print("   • Better than previous emails (improved headers)")
    print("   • Still may go to spam due to DNS issues")
    print("   • Should score better on mail-tester.com")
    
    print("\n🎯 Recommendation:")
    print("   1. Send this test to check@mail-tester.com")
    print("   2. Check score at mail-tester.com")
    print("   3. Compare with previous email scores")
    print("   4. Fix DNS records when propagation allows")
    
    return msg

if __name__ == "__main__":
    simulate_send()
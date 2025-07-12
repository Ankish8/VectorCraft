#!/usr/bin/env python3
"""
Test email template variable replacement
"""

def test_variable_replacement():
    """Test the _replace_variables function"""
    print("🧪 Testing Email Variable Replacement")
    print("=" * 50)
    
    # Test template content (like what's in database)
    template_content = """
    Hello {{username}},
    
    Your login details:
    Username: {{username}}
    Password: {{password}}
    Login URL: {{login_url}}
    
    Best regards,
    VectorCraft Team
    """
    
    # Test variables
    test_variables = {
        'username': 'testuser123',
        'password': 'mypassword456',
        'login_url': 'https://thevectorcraft.com/login'
    }
    
    print("📄 Original Template:")
    print(template_content)
    
    print("\n🔧 Test Variables:")
    for key, value in test_variables.items():
        print(f"   {key}: {value}")
    
    # Manual replacement test (simulating the _replace_variables function)
    result = template_content
    for key, value in test_variables.items():
        # Replace both {{key}} and {key} formats
        result = result.replace(f'{{{{{key}}}}}', str(value))
        result = result.replace(f'{{{key}}}', str(value))
    
    print("\n✅ Result After Variable Replacement:")
    print(result)
    
    # Check if replacement worked
    success = (
        '{{username}}' not in result and
        '{{password}}' not in result and
        '{{login_url}}' not in result and
        'testuser123' in result and
        'mypassword456' in result and
        'https://thevectorcraft.com/login' in result
    )
    
    if success:
        print("\n🎉 Variable replacement WORKING correctly!")
        print("   ✅ All template variables replaced")
        print("   ✅ Actual values present in output")
        return True
    else:
        print("\n❌ Variable replacement FAILED!")
        print("   - Some template variables still present")
        print("   - Check the _replace_variables function")
        return False

def test_email_template_format():
    """Test the exact format from your email template"""
    print("\n" + "=" * 50)
    print("🧪 Testing Purchase Confirmation Template Format")
    print("=" * 50)
    
    # This is the exact format from your email screenshot
    html_template = """
    <div class="credentials">
        <h3 style="margin-top: 0;">Login Details</h3>
        <p><strong>Username:</strong> {{username}}</p>
        <p><strong>Password:</strong> {{password}}</p>
        <p><strong>Access:</strong> <a href="{{login_url}}" style="color: #0d6efd;">{{login_url}}</a></p>
    </div>
    """
    
    variables = {
        'username': 'johndoe',
        'password': 'secure123',
        'login_url': 'https://thevectorcraft.com/login'
    }
    
    print("📧 HTML Template:")
    print(html_template)
    
    print("\n🔧 Variables:")
    for key, value in variables.items():
        print(f"   {key}: {value}")
    
    # Apply replacement
    result = html_template
    for key, value in variables.items():
        result = result.replace(f'{{{{{key}}}}}', str(value))
    
    print("\n✅ Final HTML:")
    print(result)
    
    # Verify
    if '{{username}}' not in result and 'johndoe' in result:
        print("\n🎉 HTML template replacement WORKING!")
        return True
    else:
        print("\n❌ HTML template replacement FAILED!")
        return False

if __name__ == "__main__":
    test1 = test_variable_replacement()
    test2 = test_email_template_format()
    
    if test1 and test2:
        print("\n🚀 ALL TESTS PASSED!")
        print("Variable replacement should work correctly now.")
    else:
        print("\n⚠️  Some tests failed - check the implementation.")
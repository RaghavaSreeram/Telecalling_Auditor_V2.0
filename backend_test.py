import requests
import sys
import json
from datetime import datetime
import os
import tempfile

class TelecallingAuditorAPITester:
    def __init__(self, base_url="https://voiceaudit-pro.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_script_id = None
        self.created_audit_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, is_form_data=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        
        if not is_form_data:
            headers['Content-Type'] = 'application/json'
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, headers={'Authorization': headers.get('Authorization', '')})
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_user_registration(self):
        """Test user registration"""
        test_user_data = {
            "email": f"test_user_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response['user']
            print(f"   Registered user: {self.user_data['email']}")
            return True
        return False

    def test_user_login(self):
        """Test user login with existing credentials"""
        if not self.user_data:
            print("❌ No user data available for login test")
            return False
            
        login_data = {
            "email": self.user_data['email'],
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST", 
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_create_script(self):
        """Test creating a telecalling script"""
        script_data = {
            "title": "Test Sales Script",
            "content": "Hello, this is a test telecalling script for sales purposes. We offer great products and services.",
            "expected_outcomes": ["Schedule site visit", "Qualify lead", "Get contact information"],
            "key_points": ["Introduce company", "Ask qualifying questions", "Present offer", "Handle objections"],
            "category": "sales"
        }
        
        success, response = self.run_test(
            "Create Script",
            "POST",
            "scripts",
            200,
            data=script_data
        )
        
        if success and 'id' in response:
            self.created_script_id = response['id']
            print(f"   Created script ID: {self.created_script_id}")
            return True
        return False

    def test_get_scripts(self):
        """Test getting all scripts"""
        success, response = self.run_test(
            "Get All Scripts",
            "GET",
            "scripts",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} scripts")
            return True
        return False

    def test_get_single_script(self):
        """Test getting a single script by ID"""
        if not self.created_script_id:
            print("❌ No script ID available for single script test")
            return False
            
        success, response = self.run_test(
            "Get Single Script",
            "GET",
            f"scripts/{self.created_script_id}",
            200
        )
        return success

    def test_update_script(self):
        """Test updating a script"""
        if not self.created_script_id:
            print("❌ No script ID available for update test")
            return False
            
        update_data = {
            "title": "Updated Test Sales Script",
            "category": "updated_sales"
        }
        
        success, response = self.run_test(
            "Update Script",
            "PUT",
            f"scripts/{self.created_script_id}",
            200,
            data=update_data
        )
        return success

    def test_audio_upload(self):
        """Test audio file upload (with dummy file)"""
        if not self.created_script_id:
            print("❌ No script ID available for audio upload test")
            return False
            
        # Create a dummy audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(b'dummy audio content for testing')
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as audio_file:
                files = {'audio_file': ('test_audio.wav', audio_file, 'audio/wav')}
                data = {
                    'agent_number': 'AG001',
                    'customer_number': '+1234567890',
                    'script_id': self.created_script_id,
                    'call_date': datetime.now().isoformat()
                }
                
                success, response = self.run_test(
                    "Upload Audio File",
                    "POST",
                    "audits/upload",
                    200,
                    data=data,
                    files=files,
                    is_form_data=True
                )
                
                if success and 'audit_id' in response:
                    self.created_audit_id = response['audit_id']
                    print(f"   Created audit ID: {self.created_audit_id}")
                    return True
                return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass

    def test_get_audits(self):
        """Test getting all audits"""
        success, response = self.run_test(
            "Get All Audits",
            "GET",
            "audits",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} audits")
            return True
        return False

    def test_get_single_audit(self):
        """Test getting a single audit by ID"""
        if not self.created_audit_id:
            print("❌ No audit ID available for single audit test")
            return False
            
        success, response = self.run_test(
            "Get Single Audit",
            "GET",
            f"audits/{self.created_audit_id}",
            200
        )
        return success

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        success, response = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        
        if success and isinstance(response, dict):
            expected_keys = ['total_audits', 'completed_audits', 'pending_audits', 'total_scripts', 'average_score']
            has_all_keys = all(key in response for key in expected_keys)
            if has_all_keys:
                print(f"   Stats: {response}")
                return True
            else:
                print(f"   Missing expected keys in response: {response}")
        return False

    def test_delete_script(self):
        """Test deleting a script"""
        if not self.created_script_id:
            print("❌ No script ID available for delete test")
            return False
            
        success, response = self.run_test(
            "Delete Script",
            "DELETE",
            f"scripts/{self.created_script_id}",
            200
        )
        return success

    def test_authentication_required_endpoints(self):
        """Test that endpoints require authentication"""
        # Temporarily remove token
        original_token = self.token
        self.token = None
        
        success, _ = self.run_test(
            "Unauthorized Access Test",
            "GET",
            "scripts",
            401  # Should return 401 Unauthorized
        )
        
        # Restore token
        self.token = original_token
        return success

def main():
    print("🚀 Starting Telecalling Auditor API Tests")
    print("=" * 50)
    
    tester = TelecallingAuditorAPITester()
    
    # Test sequence
    test_sequence = [
        ("User Registration", tester.test_user_registration),
        ("User Login", tester.test_user_login),
        ("Get Current User", tester.test_get_current_user),
        ("Authentication Required", tester.test_authentication_required_endpoints),
        ("Create Script", tester.test_create_script),
        ("Get All Scripts", tester.test_get_scripts),
        ("Get Single Script", tester.test_get_single_script),
        ("Update Script", tester.test_update_script),
        ("Audio Upload", tester.test_audio_upload),
        ("Get All Audits", tester.test_get_audits),
        ("Get Single Audit", tester.test_get_single_audit),
        ("Dashboard Stats", tester.test_dashboard_stats),
        ("Delete Script", tester.test_delete_script),
    ]
    
    # Run all tests
    for test_name, test_func in test_sequence:
        try:
            result = test_func()
            if not result:
                print(f"⚠️  Test '{test_name}' failed but continuing...")
        except Exception as e:
            print(f"💥 Test '{test_name}' crashed: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
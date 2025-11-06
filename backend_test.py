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
        self.test_call_id = None

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

    # ============================================================================
    # CRM Integration Tests
    # ============================================================================
    
    def test_admin_login(self):
        """Login as admin for CRM tests"""
        admin_credentials = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data=admin_credentials
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response['user']
            print(f"   Logged in as: {self.user_data.get('role', 'unknown')} - {self.user_data.get('email', 'unknown')}")
            return True
        else:
            # Try to register admin if login fails
            admin_user_data = {
                "email": "admin@example.com",
                "password": "admin123",
                "full_name": "Admin User",
                "role": "admin"
            }
            
            success, response = self.run_test(
                "Admin Registration",
                "POST",
                "auth/register",
                200,
                data=admin_user_data
            )
            
            if success and 'access_token' in response:
                self.token = response['access_token']
                self.user_data = response['user']
                print(f"   Registered and logged in as: {self.user_data.get('role', 'unknown')}")
                return True
        
        return False

    def test_crm_seed_data(self):
        """Test seeding CRM mock data"""
        success, response = self.run_test(
            "Seed CRM Data",
            "POST",
            "crm/seed?count=50",
            200
        )
        
        if success and response.get('success'):
            print(f"   Created {response.get('records_created', 0)} CRM records")
            print(f"   Created {response.get('logs_created', 0)} sync logs")
            return True
        return False

    def test_crm_list_calls(self):
        """Test listing CRM calls with pagination"""
        success, response = self.run_test(
            "List CRM Calls",
            "GET",
            "crm/calls?page=1&page_size=10",
            200
        )
        
        if success and 'records' in response:
            records = response['records']
            print(f"   Found {len(records)} records (page 1)")
            print(f"   Total records: {response.get('total', 0)}")
            print(f"   Total pages: {response.get('total_pages', 0)}")
            
            # Verify record structure
            if records:
                record = records[0]
                required_fields = ['call_id', 'crm_user_id', 'agent_id', 'agent_name', 
                                 'campaign_name', 'call_datetime', 'recording_url', 
                                 'transcript_status', 'sync_status', 'last_sync_at']
                
                missing_fields = [field for field in required_fields if field not in record]
                if missing_fields:
                    print(f"   ⚠️  Missing fields: {missing_fields}")
                    return False
                
                # Store a call_id for detail tests
                self.test_call_id = record['call_id']
                print(f"   Sample call_id: {self.test_call_id}")
            
            return True
        return False

    def test_crm_search_filter(self):
        """Test CRM calls search and filtering"""
        # Test search
        success1, response1 = self.run_test(
            "Search CRM Calls",
            "GET",
            "crm/calls?search=CRM",
            200
        )
        
        # Test sync status filter
        success2, response2 = self.run_test(
            "Filter by Sync Status",
            "GET",
            "crm/calls?sync_status=synced",
            200
        )
        
        # Test transcript status filter
        success3, response3 = self.run_test(
            "Filter by Transcript Status",
            "GET",
            "crm/calls?transcript_status=available",
            200
        )
        
        if success1 and success2 and success3:
            print(f"   Search results: {len(response1.get('records', []))} records")
            print(f"   Synced records: {len(response2.get('records', []))} records")
            print(f"   Available transcripts: {len(response3.get('records', []))} records")
            return True
        return False

    def test_crm_call_detail(self):
        """Test getting CRM call detail"""
        if not hasattr(self, 'test_call_id'):
            print("❌ No call_id available for detail test")
            return False
        
        success, response = self.run_test(
            "Get CRM Call Detail",
            "GET",
            f"crm/calls/{self.test_call_id}",
            200
        )
        
        if success and 'record' in response:
            record = response['record']
            sync_logs = response.get('sync_logs', [])
            agent_mapping = response.get('agent_mapping')
            audit_info = response.get('audit_info')
            
            print(f"   Call ID: {record.get('call_id')}")
            print(f"   Agent: {record.get('agent_name')} ({record.get('agent_id')})")
            print(f"   Sync logs: {len(sync_logs)} entries")
            print(f"   Agent mapping: {'Found' if agent_mapping else 'Not found'}")
            print(f"   Audit info: {'Linked' if audit_info else 'No audit'}")
            
            # Verify sync logs structure
            if sync_logs:
                log = sync_logs[0]
                required_log_fields = ['action', 'status', 'timestamp']
                missing_log_fields = [field for field in required_log_fields if field not in log]
                if missing_log_fields:
                    print(f"   ⚠️  Missing log fields: {missing_log_fields}")
                    return False
            
            return True
        return False

    def test_crm_resync(self):
        """Test CRM call resync (Manager/Admin only)"""
        if not hasattr(self, 'test_call_id'):
            print("❌ No call_id available for resync test")
            return False
        
        success, response = self.run_test(
            "Resync CRM Call",
            "POST",
            f"crm/calls/{self.test_call_id}/resync",
            200
        )
        
        if success and response.get('status') == 'success':
            print(f"   Resync result: {response.get('message')}")
            return True
        return False

    def test_crm_validate_mapping(self):
        """Test CRM agent mapping validation"""
        if not hasattr(self, 'test_call_id'):
            print("❌ No call_id available for mapping validation test")
            return False
        
        success, response = self.run_test(
            "Validate CRM Mapping",
            "POST",
            f"crm/calls/{self.test_call_id}/validate-mapping",
            200
        )
        
        if success:
            status = response.get('status')
            message = response.get('message')
            print(f"   Validation status: {status}")
            print(f"   Message: {message}")
            
            if status in ['success', 'warning']:
                return True
        return False

    def test_crm_health_stats(self):
        """Test CRM health statistics"""
        success, response = self.run_test(
            "Get CRM Health Stats",
            "GET",
            "crm/health",
            200
        )
        
        if success:
            expected_fields = ['total_records', 'records_synced_today', 'failures_today', 
                             'average_latency_ms', 'pending_syncs', 'error_count', 'success_rate']
            
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing health fields: {missing_fields}")
                return False
            
            print(f"   Total records: {response.get('total_records')}")
            print(f"   Synced today: {response.get('records_synced_today')}")
            print(f"   Success rate: {response.get('success_rate')}%")
            print(f"   Avg latency: {response.get('average_latency_ms')}ms")
            return True
        return False

    def test_crm_health_trends(self):
        """Test CRM health trends"""
        success, response = self.run_test(
            "Get CRM Health Trends",
            "GET",
            "crm/health/trends?days=7",
            200
        )
        
        if success and 'trends' in response:
            trends = response['trends']
            print(f"   Trend data points: {len(trends)} days")
            
            if trends:
                trend = trends[0]
                required_trend_fields = ['date', 'success_count', 'failure_count', 'total_records']
                missing_trend_fields = [field for field in required_trend_fields if field not in trend]
                if missing_trend_fields:
                    print(f"   ⚠️  Missing trend fields: {missing_trend_fields}")
                    return False
                
                print(f"   Sample trend: {trend['date']} - {trend['total_records']} records")
            
            return True
        return False

    def test_crm_retry_failed(self):
        """Test retrying failed syncs"""
        success, response = self.run_test(
            "Retry Failed Syncs",
            "POST",
            "crm/retry-failed",
            200
        )
        
        if success:
            success_count = response.get('success_count', 0)
            failure_count = response.get('failure_count', 0)
            total_attempted = response.get('total_attempted', 0)
            
            print(f"   Attempted: {total_attempted} records")
            print(f"   Successful: {success_count}")
            print(f"   Failed: {failure_count}")
            return True
        return False

    def test_crm_rbac_auditor(self):
        """Test RBAC for auditor role"""
        # Create auditor user
        auditor_data = {
            "email": f"auditor_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "auditor123",
            "full_name": "Test Auditor",
            "role": "auditor",
            "team_id": "team_1"
        }
        
        success, response = self.run_test(
            "Register Auditor",
            "POST",
            "auth/register",
            200,
            data=auditor_data
        )
        
        if not success:
            print("❌ Failed to create auditor user")
            return False
        
        # Save admin token
        admin_token = self.token
        
        # Login as auditor
        auditor_token = response['access_token']
        self.token = auditor_token
        
        # Test auditor can view calls (should be filtered)
        success1, response1 = self.run_test(
            "Auditor View Calls",
            "GET",
            "crm/calls",
            200
        )
        
        # Test auditor cannot resync (should get 403)
        success2, response2 = self.run_test(
            "Auditor Resync (Should Fail)",
            "POST",
            f"crm/calls/{getattr(self, 'test_call_id', 'dummy')}/resync",
            403
        )
        
        # Restore admin token
        self.token = admin_token
        
        if success1 and success2:
            print(f"   Auditor sees {len(response1.get('records', []))} records (filtered)")
            print("   Auditor correctly denied resync access")
            return True
        return False

    def test_crm_rbac_manager(self):
        """Test RBAC for manager role"""
        # Create manager user
        manager_data = {
            "email": f"manager_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "manager123",
            "full_name": "Test Manager",
            "role": "manager"
        }
        
        success, response = self.run_test(
            "Register Manager",
            "POST",
            "auth/register",
            200,
            data=manager_data
        )
        
        if not success:
            print("❌ Failed to create manager user")
            return False
        
        # Save admin token
        admin_token = self.token
        
        # Login as manager
        manager_token = response['access_token']
        self.token = manager_token
        
        # Test manager can view all calls
        success1, response1 = self.run_test(
            "Manager View Calls",
            "GET",
            "crm/calls",
            200
        )
        
        # Test manager can resync
        success2, response2 = self.run_test(
            "Manager Resync",
            "POST",
            f"crm/calls/{getattr(self, 'test_call_id', 'dummy')}/resync",
            200
        )
        
        # Restore admin token
        self.token = admin_token
        
        if success1 and success2:
            print(f"   Manager sees {len(response1.get('records', []))} records (all)")
            print("   Manager successfully performed resync")
            return True
        return False

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
        
        # CRM Integration Tests
        ("=== CRM INTEGRATION TESTS ===", lambda: True),
        ("Admin Login", tester.test_admin_login),
        ("Seed CRM Data", tester.test_crm_seed_data),
        ("List CRM Calls", tester.test_crm_list_calls),
        ("Search & Filter CRM", tester.test_crm_search_filter),
        ("Get CRM Call Detail", tester.test_crm_call_detail),
        ("Resync CRM Call", tester.test_crm_resync),
        ("Validate CRM Mapping", tester.test_crm_validate_mapping),
        ("CRM Health Stats", tester.test_crm_health_stats),
        ("CRM Health Trends", tester.test_crm_health_trends),
        ("Retry Failed Syncs", tester.test_crm_retry_failed),
        ("RBAC - Auditor", tester.test_crm_rbac_auditor),
        ("RBAC - Manager", tester.test_crm_rbac_manager),
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
import io
import unittest
from app import app
from database import get_db_connection, get_account_profile
from fraud_detection import analyze_transaction

class FraudGuardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_landing_page(self):
        res = self.app.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'FraudGuard', res.data)
        self.assertIn(b'Detect. Analyze. Protect.', res.data)

    def test_02_login_flow(self):
        # GET login page
        res = self.app.get('/login')
        self.assertEqual(res.status_code, 200)

        # POST login with valid demo credentials
        res = self.app.post('/login', data={
            'auth_mode': 'analyst',
            'email': 'admin@fraudguard.ai',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Security Overview', res.data)

    def test_03_otp_send_and_verify(self):
        # 1. Send OTP to sample phone 8148534339
        res = self.app.post('/api/auth/send-otp', json={'identifier': '8148534339'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        otp = data['otp']
        self.assertEqual(len(otp), 6)

        # 2. Verify OTP
        res_verify = self.app.post('/api/auth/verify-otp', json={
            'identifier': '8148534339',
            'otp_code': otp
        })
        self.assertEqual(res_verify.status_code, 200)
        verify_data = res_verify.get_json()
        self.assertTrue(verify_data['success'])
        self.assertEqual(verify_data['account']['account_id'], 'ACC101')

    def test_04_transaction_limit_80000(self):
        # Test transaction exceeding ₹80,000 ceiling
        payload = {
            'account_id': 'ACC101',
            'amount': 85000.0,
            'location': 'Chennai',
            'time': '12:00 PM',
            'device': 'Known Mobile Device',
            'transactions_10min': 1
        }
        analysis = analyze_transaction(payload)
        self.assertEqual(analysis['risk_level'], 'CRITICAL')
        reasons = [r['title'] for r in analysis['flagged_reasons']]
        self.assertTrue(any('80,000' in r for r in reasons))

    def test_05_sms_response_self_safe(self):
        # When customer confirms transaction was done by SELF -> SAFE (ACTIVE)
        res = self.app.post('/api/accounts/ACC101/sms-response', json={
            'decision': 'SELF',
            'transaction_id': 'TX_TEST_SAFE'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'ACTIVE')

        acc = get_account_profile('ACC101')
        self.assertEqual(acc['status'], 'ACTIVE')

    def test_06_sms_response_others_fraud_block(self):
        # When customer reports transaction was done by OTHERS -> IMMEDIATELY BLOCKED
        res = self.app.post('/api/accounts/ACC105/sms-response', json={
            'decision': 'OTHERS',
            'transaction_id': 'TX_TEST_FRAUD'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'BLOCKED')

        acc = get_account_profile('ACC105')
        self.assertEqual(acc['status'], 'BLOCKED')

    def test_07_call_workflow_and_sms_fallback(self):
        # Attempt 1 missed
        res1 = self.app.post('/api/accounts/ACC108/call-step', json={
            'attempt': 1,
            'outcome': 'NOT_ATTENDED',
            'transaction_id': 'TX10099',
            'amount': '85,000',
            'location': 'Delhi'
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json()['next_step'], 'RETRY_CALL')

        # Attempt 2 missed -> Fallback to SMS Decision
        res2 = self.app.post('/api/accounts/ACC108/call-step', json={
            'attempt': 2,
            'outcome': 'NOT_ATTENDED',
            'transaction_id': 'TX10099',
            'amount': '85,000',
            'location': 'Delhi'
        })
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()['next_step'], 'SMS_DECISION')

    def test_08_dashboard_api(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Administrator'
            sess['user_email'] = 'admin@fraudguard.ai'

        res = self.app.get('/api/dashboard')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('total_transactions', data['metrics'])

    def test_09_simulate_endpoint(self):
        res = self.app.post('/api/simulate')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('transaction', data)
        self.assertIn('steps', data)

    def test_10_csv_upload(self):
        csv_data = (
            "transaction_id,account_id,amount,avg_amount,location,time,new_device,transactions_10min\n"
            "TX_TEST_01,ACC102,95000,3500,Dubai,03:30 AM,1,8\n"
            "TX_TEST_02,ACC101,2000,3200,Chennai,01:15 PM,0,1\n"
        )
        res = self.app.post('/api/upload', data={
            'file': (io.BytesIO(csv_data.encode('utf-8')), 'test_batch.csv')
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 2)

    def test_11_phone_capture_and_update(self):
        # 1. Update phone via API
        res = self.app.post('/api/user/update-phone', json={'phone': '9876543210'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['phone'], '+919876543210')

        # 2. Reset back to user phone
        res2 = self.app.post('/api/user/update-phone', json={'phone': '8148534339'})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()['phone'], '+918148534339')

if __name__ == '__main__':
    unittest.main()

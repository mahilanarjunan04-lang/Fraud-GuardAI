import io
import unittest
from app import app
from database import get_db_connection

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
            'email': 'admin@fraudguard.ai',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Security Overview', res.data)

    def test_03_dashboard_api(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Administrator'
            sess['user_email'] = 'admin@fraudguard.ai'

        res = self.app.get('/api/dashboard')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('total_transactions', data['metrics'])

    def test_04_simulate_endpoint(self):
        res = self.app.post('/api/simulate')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('transaction', data)
        self.assertIn('steps', data)
        self.assertGreaterEqual(len(data['steps']), 5)

    def test_05_transaction_detail(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Administrator'

        res = self.app.get('/transactions/TX10045')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'TX10045', res.data)
        self.assertIn(b'Why was this transaction flagged?', res.data)

    def test_06_csv_upload(self):
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

    def test_07_analytics_endpoint(self):
        res = self.app.get('/api/analytics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('risk_distribution', data)
        self.assertIn('location_analysis', data)

    def test_08_network_endpoint(self):
        res = self.app.get('/api/network')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('nodes', data)
        self.assertIn('edges', data)

if __name__ == '__main__':
    unittest.main()

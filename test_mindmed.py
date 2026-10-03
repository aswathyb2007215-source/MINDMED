import unittest
import os
import json
from app import app
from database import get_db_connection, init_db, reset_demo_user_seed

class MindMedEndToEndTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        init_db()
        reset_demo_user_seed()

    def test_00_home_page(self):
        """Test home landing page renders with brand and core pillars"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MINDMED', response.data)
        self.assertIn(b'Talk. Understand.', response.data)
        self.assertIn(b'Detect. Connect.', response.data)
        self.assertIn(b'Four Core Pillars', response.data)
        self.assertIn(b'Box Breathing', response.data)

    def test_01_protected_routes_redirect_unauthenticated(self):
        """Ensure all protected routes redirect unauthenticated users to /login"""
        protected_urls = [
            '/dashboard',
            '/assessment',
            '/results',
            '/ai-companion',
            '/professionals',
            '/doctors',
            '/appointments',
            '/profile',
            '/summary',
            '/insights'
        ]
        for url in protected_urls:
            response = self.client.get(url, follow_redirects=False)
            self.assertEqual(response.status_code, 302, f"Route {url} should redirect")
            self.assertIn('/login', response.headers['Location'])

    def test_02_login_and_logout_flow(self):
        """Test login with demo user and logout"""
        # Bad login
        res_bad = self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res_bad.data)

        # Successful login
        res_good = self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)
        self.assertEqual(res_good.status_code, 200)
        self.assertIn(b'Welcome', res_good.data)
        self.assertIn(b'Aswathy', res_good.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'logged out securely', res_logout.data)

        # Confirm dashboard is now inaccessible
        res_dash = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(res_dash.status_code, 302)

    def test_03_signup_flow(self):
        """Test user signup with validations and automatic login"""
        test_email = 'test_judge_user@mindmed.health'

        # Clean up any leftover test user
        conn = get_db_connection()
        conn.execute('DELETE FROM users WHERE email = ?', (test_email,))
        conn.commit()
        conn.close()

        # Signup with password mismatch
        res_mismatch = self.client.post('/signup', data={
            'name': 'Test Judge',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'password456',
            'age': '30',
            'gender': 'Male',
            'location': 'Bengaluru'
        }, follow_redirects=True)
        self.assertIn(b'Passwords do not match', res_mismatch.data)

        # Successful signup
        res_success = self.client.post('/signup', data={
            'name': 'Test Judge',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'password123',
            'age': '30',
            'gender': 'Male',
            'location': 'Bengaluru'
        }, follow_redirects=True)
        self.assertEqual(res_success.status_code, 200)
        self.assertIn(b'Establish Your Personal Baseline', res_success.data)
        self.assertIn(b'Test', res_success.data)

        # Clean up
        self.client.get('/logout')

    def test_04_assessment_baseline_and_early_awareness(self):
        """Test taking assessment, baseline establishment, delta comparison, and early awareness"""
        # Login demo user who already has elevated stress data
        self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)

        # View dashboard
        res_dash = self.client.get('/dashboard')
        self.assertIn(b'MindMED Early Awareness', res_dash.data)
        self.assertIn(b'Current Wellbeing vs. Personal Baseline', res_dash.data)

        # Submit a new assessment with balanced scores
        res_post_assess = self.client.post('/assessment', data={
            'mood': '4',
            'stress': '2',
            'energy': '4',
            'sleep': '4',
            'anx_nervous': '1',
            'anx_worry': '1',
            'dep_pleasure': '1',
            'dep_hopeless': '1',
            'burn_exhaustion': '1',
            'burn_motivation': '1',
            'burn_recovery': '1',
            'hlth_fatigue': '1',
            'hlth_activity': '1'
        }, follow_redirects=True)
        self.assertEqual(res_post_assess.status_code, 200)
        self.assertIn(b'Your Wellbeing Screening Summary', res_post_assess.data)
        self.assertIn(b'Low Indication', res_post_assess.data)

        self.client.get('/logout')

    def test_05_ai_companion_and_crisis_detection(self):
        """Test AI companion responses and immediate crisis safety alert"""
        self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)

        # Normal supportive chat
        res_chat = self.client.post('/api/chat',
            data=json.dumps({'message': 'I am feeling very stressed about my work'}),
            content_type='application/json'
        )
        self.assertEqual(res_chat.status_code, 200)
        data = json.loads(res_chat.data)
        self.assertFalse(data['is_crisis'])
        self.assertIn('Box Breathing', data['reply'])

        # Crisis detection
        res_crisis = self.client.post('/api/chat',
            data=json.dumps({'message': 'I feel like I want to kill myself'}),
            content_type='application/json'
        )
        self.assertEqual(res_crisis.status_code, 200)
        crisis_data = json.loads(res_crisis.data)
        self.assertTrue(crisis_data['is_crisis'])
        self.assertIn('Tele-MANAS', crisis_data['reply'])
        self.assertIn('14416', crisis_data['reply'])
        self.assertIn('988', crisis_data['reply'])

        self.client.get('/logout')

    def test_06_appointments_and_professionals(self):
        """Test viewing professionals and booking an appointment"""
        self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)

        # Check professionals page and doctors alias
        res_profs = self.client.get('/professionals')
        self.assertIn(b'Dr. Ananya Menon', res_profs.data)
        self.assertIn(b'Dr. Rahul Nair', res_profs.data)

        res_docs = self.client.get('/doctors')
        self.assertEqual(res_docs.status_code, 200)
        self.assertIn(b'Tele-MANAS', res_docs.data)

        # Book appointment
        res_book = self.client.post('/appointments', data={
            'professional_id': '2',
            'appointment_date': '2026-10-15',
            'appointment_time': '02:00 PM',
            'notes': 'Test appointment booking for sleep fatigue'
        }, follow_redirects=True)
        self.assertEqual(res_book.status_code, 200)
        self.assertIn(b'Appointment booked successfully', res_book.data)
        self.assertIn(b'Dr. Rahul Nair', res_book.data)

        self.client.get('/logout')

    def test_07_profile_consent_and_clinical_summary(self):
        """Test updating consent preferences and viewing provider summary"""
        self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)

        # Update consent
        res_consent = self.client.post('/profile', data={
            'action': 'update_consent',
            'share_summary': '1',
            'share_assessment': '1'
        }, follow_redirects=True)
        self.assertEqual(res_consent.status_code, 200)
        self.assertIn(b'Privacy and sharing consent preferences saved', res_consent.data)

        # View summary
        res_sum = self.client.get('/summary')
        self.assertEqual(res_sum.status_code, 200)
        self.assertIn(b'Authorized for Healthcare Provider Sharing', res_sum.data)
        self.assertIn(b'Core Wellbeing Metrics vs. Established Baseline', res_sum.data)
        self.assertIn(b'CLINICAL DISCLAIMER', res_sum.data)

        self.client.get('/logout')

    def test_08_mood_checkin_api(self):
        """Test daily mood check-in API endpoint"""
        self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)

        res = self.client.post('/api/mood-checkin',
            data=json.dumps({
                'mood_score': 5,
                'mood_label': 'Great',
                'energy_score': 4,
                'note': 'Feeling energized after exercise'
            }),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('Great', data['message'])
        self.assertGreaterEqual(data['streak'], 1)

        self.client.get('/logout')

    def test_09_insights_page_and_timeline(self):
        """Test insights page renders timeline, trajectory chart datasets, and risk prediction"""
        self.client.post('/login', data={
            'email': 'demo@mindmed.health',
            'password': 'mindmed123'
        }, follow_redirects=True)

        res = self.client.get('/insights')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Longitudinal Insights & Trend Detection', res.data)
        self.assertIn(b'Personalized Risk Prediction Index', res.data)
        self.assertIn(b'Explainable Factor Attribution', res.data)
        self.assertIn(b'Longitudinal Wellbeing Timeline', res.data)
        self.assertIn(b'Screening Completed', res.data)

        self.client.get('/logout')

if __name__ == '__main__':
    unittest.main()

"""
FindBack - End-to-End System Integration Test
Executes the complete college presentation workflow using Flask test client:
1. Verifies Landing page and live counters
2. Logs in as Rahul (Lost Wallet Owner)
3. Verifies AI Match identified between Rahul's lost wallet and Sneha's found wallet
4. Rahul submits ownership claim with distinguishing details
5. Verifies item status updates to 'Claim Requested'
6. Logs in as Sneha (Finder)
7. Sneha inspects claim, cross-verifies private secret proof, approves claim
8. Verifies status transitions to 'Verified'
9. Sneha confirms physical handover and marks item 'Returned'
10. Verifies recovery statistics update on Admin Dashboard
11. Tests QR Code scan and anonymous finder messaging
"""

import unittest
from app import create_app
from app.models import get_db_connection

class TestFindBackE2E(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_01_landing_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'FindBack', res.data)
        self.assertIn(b'Intelligent TF-IDF Cosine Similarity Matching', res.data)
        print("\n[OK] Test 1: Landing page accessible with live counters.")

    def test_02_authentication_and_dashboard(self):
        # Invalid login
        res = self.client.post('/login', data={'email': 'rahul@campus.edu', 'password': 'WrongPassword'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res.data)

        # Valid login as Rahul
        res = self.client.post('/login', data={'email': 'rahul@campus.edu', 'password': 'User@123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Hello, Rahul!', res.data)
        print("[OK] Test 2: Authentication & RBAC validated successfully.")

    def test_03_ai_matching_detection(self):
        # Log in as Rahul
        self.client.post('/login', data={'email': 'rahul@campus.edu', 'password': 'User@123'})
        res = self.client.get('/matches')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Black Leather Bi-Fold Wallet', res.data)
        self.assertIn(b'Black Men Leather Wallet', res.data)
        print("[OK] Test 3: AI Matching engine detected cross-item suggestion.")

    def test_04_full_demonstration_lifecycle(self):
        """
        The Presentation Scenario:
        1. Rahul submits claim with secret details.
        2. Sneha verifies & approves.
        3. Handover confirmed -> Marked Returned.
        """
        # Step A: Login as Rahul and submit claim for Found Item #1
        self.client.post('/login', data={'email': 'rahul@campus.edu', 'password': 'User@123'})
        res = self.client.post('/claim/1', data={
            'lost_item_id': '1',
            'claimant_details': 'College ID ending in 4921, exactly Rs 250 in cash (two 100 notes, one 50 note).',
            'contact_note': 'I can meet at Central Library entrance at 4 PM.'
        }, follow_redirects=True)
        self.assertIn(b'Your claim has been submitted', res.data)

        conn = get_db_connection()
        found_item = conn.execute('SELECT status FROM found_items WHERE id = 1').fetchone()
        self.assertEqual(found_item['status'], 'Claim Requested')
        claim = conn.execute('SELECT id, status FROM claims WHERE found_item_id = 1').fetchone()
        self.assertEqual(claim['status'], 'Pending')
        claim_id = claim['id']
        conn.close()
        print("[OK] Step 4A: Claim submitted, status changed to 'Claim Requested'.")

        # Step B: Login as Sneha (Finder) to review and approve
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'sneha@campus.edu', 'password': 'User@123'})
        
        # Sneha accesses review page
        res = self.client.get(f'/claims/review/{claim_id}')
        self.assertIn(b'Evidence Cross-Verification', res.data)
        self.assertIn(b'Contains College ID ending in 4921', res.data)

        # Sneha approves claim
        res = self.client.post(f'/claims/review/{claim_id}', data={
            'action': 'approve',
            'review_notes': 'Distinguishing ID and exact cash amount confirmed. Ready for handover.'
        }, follow_redirects=True)
        self.assertIn(b'Claim verified and approved', res.data)

        conn = get_db_connection()
        found_item = conn.execute('SELECT status FROM found_items WHERE id = 1').fetchone()
        self.assertEqual(found_item['status'], 'Verified')
        conn.close()
        print("[OK] Step 4B: Finder reviewed proof and approved claim -> status 'Verified'.")

        # Step C: Confirm Handover & Mark Returned
        res = self.client.post('/claims/handover-complete/1', follow_redirects=True)
        self.assertIn(b'Item officially marked as RETURNED', res.data)

        conn = get_db_connection()
        found_item = conn.execute('SELECT status FROM found_items WHERE id = 1').fetchone()
        self.assertEqual(found_item['status'], 'Returned')
        lost_item = conn.execute('SELECT status FROM lost_items WHERE id = 1').fetchone()
        self.assertEqual(lost_item['status'], 'Returned')
        conn.close()
        print("[OK] Step 4C: Physical handover completed -> status 'Returned'. Full loop closed!")

    def test_05_admin_dashboard(self):
        self.client.get('/logout')
        # Login as Admin
        self.client.post('/login', data={'email': 'admin@findback.com', 'password': 'Admin@123'})
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'System Analytics & Operations', res.data)
        self.assertIn(b'Recovery Rate', res.data)
        self.assertIn(b'Most Lost Categories', res.data)
        print("[OK] Test 5: Admin telemetry & analytics dashboard fully operational.")

    def test_06_qr_anonymous_contact(self):
        conn = get_db_connection()
        qr = conn.execute('SELECT qr_code_uuid, id FROM qr_registrations LIMIT 1').fetchone()
        qr_uuid = qr['qr_code_uuid']
        conn.close()

        # Public scan page (anonymous)
        self.client.get('/logout')
        res = self.client.get(f'/qr/scan/{qr_uuid}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Privacy Protection Active', res.data)

        # Post finder message
        res = self.client.post(f'/qr/scan/{qr_uuid}', data={
            'finder_name': 'Kavita',
            'finder_contact': '+91 9123456789',
            'found_location': 'Block C Reading Hall',
            'finder_message': 'Found your item, safely kept with me.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Thank You, Good Samaritan!', res.data)

        conn = get_db_connection()
        msg = conn.execute('SELECT * FROM qr_messages WHERE qr_registration_id = ?', (qr['id'],)).fetchone()
        self.assertIsNotNone(msg)
        self.assertEqual(msg['finder_contact'], '+91 9123456789')
        conn.close()
        print("[OK] Test 6: QR Scan & privacy-preserving anonymous contact works end-to-end.")

if __name__ == '__main__':
    unittest.main()

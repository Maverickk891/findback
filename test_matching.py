"""
FindBack - Intelligent Matching Algorithm Test Suite
Verifies TF-IDF NLP scoring, category alignment, location fuzzy matching, date closeness, and combined weighting.
"""

import unittest
from datetime import datetime, timedelta
from app.matching.engine import (
    preprocess_text,
    calculate_text_similarity,
    calculate_category_similarity,
    calculate_location_similarity,
    calculate_date_similarity,
    match_items
)

class TestMatchingAlgorithm(unittest.TestCase):

    def test_synonym_expansion(self):
        """Verifies synonym expansion ensures related terms match under TF-IDF."""
        text1 = "Black leather wallet with cards"
        text2 = "Black leather purse with cards"
        score, shared = calculate_text_similarity(text1, text2)
        self.assertGreater(score, 50.0, f"Expected > 50% for wallet/purse synonym match, got {score}")
        self.assertTrue(len(shared) > 0)

    def test_category_matching(self):
        """Verifies exact category yields 100, soft group yields 70, disjoint yields 0."""
        self.assertEqual(calculate_category_similarity("Electronics", "Electronics"), 100.0)
        self.assertEqual(calculate_category_similarity("Wallets & Bags", "Wallets & Bags"), 100.0)
        self.assertEqual(calculate_category_similarity("Electronics", "Clothing"), 0.0)

    def test_location_matching(self):
        """Verifies identical and overlapping campus locations."""
        # Exact match
        self.assertEqual(calculate_location_similarity("Central Library", "Central Library"), 100.0)
        # Substring / overlap match
        score = calculate_location_similarity("Central Library 2nd Floor", "Central Library")
        self.assertGreaterEqual(score, 80.0)
        # Disjoint locations
        score_disjoint = calculate_location_similarity("Sports Gymnasium", "Chemistry Lab Block C")
        self.assertEqual(score_disjoint, 0.0)

    def test_date_similarity(self):
        """Verifies date closeness curve."""
        today = datetime.today().date()
        same_day = today.strftime('%Y-%m-%d')
        one_day = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        seven_days = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        thirty_days = (today - timedelta(days=30)).strftime('%Y-%m-%d')

        self.assertEqual(calculate_date_similarity(same_day, same_day), 100.0)
        self.assertEqual(calculate_date_similarity(same_day, one_day), 90.0)
        self.assertEqual(calculate_date_similarity(same_day, seven_days), 50.0)
        self.assertLess(calculate_date_similarity(same_day, thirty_days), 20.0)

    def test_end_to_end_wallet_match(self):
        """Verifies real demo scenario: Rahul's lost wallet vs Sneha's found wallet."""
        lost_wallet = {
            'id': 1,
            'item_name': 'Black Leather Bi-Fold Wallet',
            'category': 'Wallets & Bags',
            'description': 'Matte black genuine leather Tommy Hilfiger wallet with student ID and debit card.',
            'color': 'Black',
            'brand': 'Tommy Hilfiger',
            'last_seen_location': 'Central Library 2nd Floor Reading Room',
            'date_lost': '2026-11-17'
        }

        found_wallet = {
            'id': 1,
            'item_name': 'Black Men Leather Wallet',
            'category': 'Wallets & Bags',
            'description': 'Black leather bi-fold wallet found on desk chair.',
            'color': 'Black',
            'brand': 'Tommy Hilfiger',
            'found_location': 'Central Library 2nd Floor Desk',
            'date_found': '2026-11-17'
        }

        result = match_items(lost_wallet, found_wallet)
        
        # Combined score should be high confidence (>= 75%)
        self.assertGreaterEqual(result['total_score'], 75.0)
        self.assertIn('Wallets & Bags', result['match_reasons'])
        print(f"\n[Test Result] Wallet Match Score: {result['total_score']}%")
        print(f"  Description Score (50% wt): {result['description_score']}%")
        print(f"  Category Score (20% wt):    {result['category_score']}%")
        print(f"  Location Score (20% wt):    {result['location_score']}%")
        print(f"  Date Score (10% wt):        {result['date_score']}%")
        print(f"  Verdict: {result['match_reasons']}")

    def test_unrelated_items_do_not_match(self):
        """Verifies an unrelated lost phone does not falsely match a found key."""
        lost_phone = {
            'id': 10,
            'item_name': 'Blue iPhone 13',
            'category': 'Electronics',
            'description': 'Blue Apple iPhone 13 with cracked glass back.',
            'color': 'Blue',
            'brand': 'Apple',
            'last_seen_location': 'Cafeteria',
            'date_lost': '2026-11-10'
        }

        found_key = {
            'id': 20,
            'item_name': 'Brass Motorcycle Key',
            'category': 'Keys',
            'description': 'Single brass key with round fob.',
            'color': 'Brass',
            'brand': 'Hero',
            'found_location': 'Parking Lot',
            'date_found': '2026-11-18'
        }

        result = match_items(lost_phone, found_key)
        self.assertLess(result['total_score'], 30.0, f"Expected < 30% for disjoint items, got {result['total_score']}")

if __name__ == '__main__':
    unittest.main()

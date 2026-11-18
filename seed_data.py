"""
FindBack - Realistic Demonstration Seed Data Generator
Populates accounts, realistic campus lost/found reports, AI matches, claims, status history, and QR codes.
"""

import os
from datetime import datetime, timedelta
from app.models import get_db_connection, init_db
from app.services.auth_service import hash_password
from app.services.qr_service import generate_qr_for_item
from app.matching.engine import run_matching_for_item

def seed_database():
    print("[*] Initializing database schema...")
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clean any previous demo data
    print("[*] Preparing clean demonstration state...")
    cursor.execute('DELETE FROM notifications;')
    cursor.execute('DELETE FROM qr_messages;')
    cursor.execute('DELETE FROM qr_registrations;')
    cursor.execute('DELETE FROM item_status_history;')
    cursor.execute('DELETE FROM claims;')
    cursor.execute('DELETE FROM matches;')
    cursor.execute('DELETE FROM found_items;')
    cursor.execute('DELETE FROM lost_items;')
    cursor.execute('DELETE FROM users;')
    cursor.execute("DELETE FROM sqlite_sequence;")
    conn.commit()

    print("[*] Seeding user accounts...")
    users = [
        ('Administrator', 'admin@findback.com', hash_password('Admin@123'), '+91 9876540001', 'admin'),
        ('Rahul Sharma', 'rahul@campus.edu', hash_password('User@123'), '+91 9876540002', 'user'),
        ('Sneha Patel', 'sneha@campus.edu', hash_password('User@123'), '+91 9876540003', 'user'),
        ('Vikram Verma', 'vikram@campus.edu', hash_password('User@123'), '+91 9876540004', 'user'),
        ('Ananya Sen', 'ananya@campus.edu', hash_password('User@123'), '+91 9876540005', 'user')
    ]
    cursor.executemany('''
        INSERT INTO users (name, email, password_hash, phone, role)
        VALUES (?, ?, ?, ?, ?)
    ''', users)
    conn.commit()

    # Query dynamic user IDs to guarantee foreign key integrity
    user_rows = cursor.execute('SELECT email, id FROM users').fetchall()
    user_map = {row['email']: row['id'] for row in user_rows}
    admin_id = user_map['admin@findback.com']
    rahul_id = user_map['rahul@campus.edu']
    sneha_id = user_map['sneha@campus.edu']
    vikram_id = user_map['vikram@campus.edu']
    ananya_id = user_map['ananya@campus.edu']

    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    three_days_ago = today - timedelta(days=3)

    print("[*] Seeding lost item reports...")
    lost_items_data = [
        # Item 1: The flagship demo wallet
        (
            rahul_id,
            'Black Leather Bi-Fold Wallet',
            'Wallets & Bags',
            'Matte black genuine leather Tommy Hilfiger wallet with student ID and debit card.',
            'Black',
            'Tommy Hilfiger',
            'Central Library 2nd Floor Reading Room',
            yesterday.strftime('%Y-%m-%d'),
            None,
            'Student ID ending in 4921, Rs 250 in cash',
            'Reported'
        ),
        # Item 2: Apple AirPods Pro
        (
            ananya_id,
            'Apple AirPods Pro 2nd Gen',
            'Electronics',
            'White wireless earbuds in a silicone lavender case with small astronaut keychain. Lost during lunch hour.',
            'White',
            'Apple',
            'Campus Main Cafeteria Table #12',
            two_days_ago.strftime('%Y-%m-%d'),
            None,
            'Engraved name "Ananya" on case',
            'Reported'
        ),
        # Item 3: College RFID Access Smartcard
        (
            vikram_id,
            'College Identity Card & Blue Lanyard',
            'Documents & IDs',
            'Official AI&DS Department ID card with blue university lanyard and magnetic hostel swipe tag.',
            'Blue',
            'Campus RFID',
            'Block B Computer Center Lab 3',
            three_days_ago.strftime('%Y-%m-%d'),
            None,
            'Registration number 21AIDS044',
            'Reported'
        ),
        # Item 4: Scientific Calculator
        (
            rahul_id,
            'Casio FX-991EX Scientific Calculator',
            'Books & Stationery',
            'Black scientific calculator with QR code function. Has matrix operations shortcut written on the protective slide cover.',
            'Black',
            'Casio',
            'Mechanical Seminar Hall',
            today.strftime('%Y-%m-%d'),
            None,
            'Small white scratch near back battery door',
            'Reported'
        )
    ]

    for item in lost_items_data:
        cursor.execute('''
            INSERT INTO lost_items (user_id, item_name, category, description, color, brand, last_seen_location, date_lost, photo_filename, additional_identifying_info, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', item)
        lost_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO item_status_history (item_type, item_id, old_status, new_status, remarks, changed_by)
            VALUES ('lost', ?, NULL, 'Reported', 'Item initially reported lost by owner', ?)
        ''', (lost_id, item[0]))
    
    conn.commit()

    print("[*] Seeding found item reports...")
    found_items_data = [
        # Found Item 1: Pairs with Rahul's wallet (Found by Sneha!)
        (
            sneha_id,
            'Black Men Leather Wallet',
            'Wallets & Bags',
            'Black leather bi-fold wallet found on desk chair.',
            'Black',
            'Tommy Hilfiger',
            'Central Library 2nd Floor Desk',
            yesterday.strftime('%Y-%m-%d'),
            None,
            'Contains College ID ending in 4921 and two currency notes of Rs 100 and one Rs 50 (Total Rs 250)',
            'Library Circulation Desk',
            'Reported'
        ),
        # Found Item 2: Apple AirPods (Found by Vikram)
        (
            vikram_id,
            'White Wireless Earbuds with Case',
            'Electronics',
            'White earbuds in protective colored silicone sleeve found on bench.',
            'White',
            'Apple',
            'Main Cafeteria Outdoor Seating',
            two_days_ago.strftime('%Y-%m-%d'),
            None,
            'Lavender silicone cover with small astronaut charm',
            'With Finder',
            'Reported'
        ),
        # Found Item 3: Set of Keys
        (
            ananya_id,
            'Hero Bike Key & Brass Ring',
            'Keys',
            'Single motorcycle ignition key with a black rubber fob and brass ring.',
            'Silver/Black',
            'Hero',
            'Student Two-Wheeler Parking Lot Zone C',
            today.strftime('%Y-%m-%d'),
            None,
            'Key code stamped #H449',
            'Security Gate #2 Office',
            'Reported'
        )
    ]

    for item in found_items_data:
        cursor.execute('''
            INSERT INTO found_items (user_id, item_name, category, description, color, brand, found_location, date_found, photo_filename, distinguishing_details, storage_location, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', item)
        found_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO item_status_history (item_type, item_id, old_status, new_status, remarks, changed_by)
            VALUES ('found', ?, NULL, 'Reported', 'Item reported found by finder', ?)
        ''', (found_id, item[0]))

    conn.commit()

    print("[*] Seeding historical recovered item for analytics...")
    cursor.execute('''
        INSERT INTO lost_items (user_id, item_name, category, description, color, brand, last_seen_location, date_lost, status)
        VALUES (?, 'Titan Smartwatch Neo', 'Jewelry & Watches', 'Black dial digital smartwatch with black silicone strap.', 'Black', 'Titan', 'Sports Complex Gymnasium', ?, 'Returned')
    ''', (ananya_id, (today - timedelta(days=5)).strftime('%Y-%m-%d')))
    ret_lost_id = cursor.lastrowid
    
    cursor.execute('''
        INSERT INTO found_items (user_id, item_name, category, description, color, brand, found_location, date_found, distinguishing_details, storage_location, status)
        VALUES (?, 'Black Digital Smartwatch', 'Jewelry & Watches', 'Black smartwatch found near locker room.', 'Black', 'Titan', 'Sports Complex', ?, 'Custom spider wallpaper on watch dial', 'Sports Office', 'Returned')
    ''', (sneha_id, (today - timedelta(days=4)).strftime('%Y-%m-%d')))
    ret_found_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO claims (found_item_id, lost_item_id, claimant_id, claimant_details, contact_note, status, review_notes, reviewed_by, reviewed_at)
        VALUES (?, ?, ?, 'Custom spider-man watch face with red seconds ring', 'Verified and returned in person', 'Approved', 'Accurate wallpaper proof verified', ?, CURRENT_TIMESTAMP)
    ''', (ret_found_id, ret_lost_id, ananya_id, sneha_id))

    cursor.execute('''
        INSERT INTO item_status_history (item_type, item_id, old_status, new_status, remarks, changed_by, created_at)
        VALUES ('found', ?, NULL, 'Reported', 'Initially reported', ?, ?)
    ''', (ret_found_id, sneha_id, (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('''
        INSERT INTO item_status_history (item_type, item_id, old_status, new_status, remarks, changed_by, created_at)
        VALUES ('found', ?, 'Reported', 'Verified', 'Distinguishing watch wallpaper confirmed', ?, ?)
    ''', (ret_found_id, sneha_id, (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('''
        INSERT INTO item_status_history (item_type, item_id, old_status, new_status, remarks, changed_by, created_at)
        VALUES ('found', ?, 'Verified', 'Returned', 'Handover confirmed at Sports Office', ?, ?)
    ''', (ret_found_id, sneha_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()

    print("[*] Running TF-IDF matching engine on all items...")
    run_matching_for_item('lost', 1)
    run_matching_for_item('lost', 2)
    run_matching_for_item('lost', 3)
    run_matching_for_item('lost', 4)

    print("[*] Generating QR codes for registered belongings...")
    generate_qr_for_item(
        rahul_id,
        "Rahul's Dell Inspiron Laptop",
        "Electronics",
        "Silver 15-inch Dell laptop with AI sticker on top lid.",
        "Please return to Rahul Sharma (5th Sem AI&DS). Reward guaranteed upon return!"
    )
    generate_qr_for_item(
        vikram_id,
        "Vikram's Hostel Room & Bike Keys",
        "Keys",
        "Set of 3 keys with red lanyard.",
        "Please deposit at Boys Hostel Block 2 Warden Office."
    )

    print("\n[+] SUCCESS: FindBack Seed Database fully initialized!")
    print("========================================================")
    print("DEMO CREDENTIALS:")
    print("  Administrator: admin@findback.com  |  Pass: Admin@123")
    print("  User 1 (Owner): rahul@campus.edu   |  Pass: User@123")
    print("  User 2 (Finder): sneha@campus.edu  |  Pass: User@123")
    print("  User 3 (Member): vikram@campus.edu |  Pass: User@123")
    print("========================================================")

if __name__ == '__main__':
    seed_database()

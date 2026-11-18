import sqlite3
import os
from datetime import datetime
from config import Config

def get_db_connection():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # 2. Lost Items Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lost_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        color TEXT NOT NULL,
        brand TEXT,
        last_seen_location TEXT NOT NULL,
        date_lost DATE NOT NULL,
        photo_filename TEXT,
        additional_identifying_info TEXT,
        status TEXT NOT NULL DEFAULT 'Reported',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # 3. Found Items Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS found_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        color TEXT NOT NULL,
        brand TEXT,
        found_location TEXT NOT NULL,
        date_found DATE NOT NULL,
        photo_filename TEXT,
        distinguishing_details TEXT,
        storage_location TEXT DEFAULT 'With Finder',
        status TEXT NOT NULL DEFAULT 'Reported',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # 4. Matches Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lost_item_id INTEGER NOT NULL,
        found_item_id INTEGER NOT NULL,
        description_score REAL NOT NULL,
        category_score REAL NOT NULL,
        location_score REAL NOT NULL,
        date_score REAL NOT NULL,
        total_score REAL NOT NULL,
        match_reasons TEXT,
        is_dismissed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(lost_item_id, found_item_id),
        FOREIGN KEY (lost_item_id) REFERENCES lost_items(id) ON DELETE CASCADE,
        FOREIGN KEY (found_item_id) REFERENCES found_items(id) ON DELETE CASCADE
    );
    ''')

    # 5. Claims Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        found_item_id INTEGER NOT NULL,
        lost_item_id INTEGER,
        claimant_id INTEGER NOT NULL,
        claimant_details TEXT NOT NULL,
        contact_note TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        review_notes TEXT,
        reviewed_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        FOREIGN KEY (found_item_id) REFERENCES found_items(id) ON DELETE CASCADE,
        FOREIGN KEY (lost_item_id) REFERENCES lost_items(id) ON DELETE SET NULL,
        FOREIGN KEY (claimant_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
    );
    ''')

    # 6. Item Status History Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS item_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_type TEXT NOT NULL,
        item_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        remarks TEXT,
        changed_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # 7. QR Registrations Table (Pre-registered Belongings)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS qr_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        qr_code_uuid TEXT UNIQUE NOT NULL,
        recovery_instructions TEXT,
        qr_image_filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # 8. QR Finder Messages Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS qr_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qr_registration_id INTEGER NOT NULL,
        finder_name TEXT,
        finder_contact TEXT NOT NULL,
        finder_message TEXT NOT NULL,
        found_location TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (qr_registration_id) REFERENCES qr_registrations(id) ON DELETE CASCADE
    );
    ''')

    # 9. Notifications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Create Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lost_items_user ON lost_items(user_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lost_items_status ON lost_items(status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_found_items_user ON found_items(user_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_found_items_status ON found_items(status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_lost ON matches(lost_item_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_found ON matches(found_item_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_claims_found ON claims(found_item_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_claims_claimant ON claims(claimant_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_qr_uuid ON qr_registrations(qr_code_uuid);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);')

    conn.commit()
    conn.close()

def log_status_change(item_type, item_id, old_status, new_status, remarks, changed_by, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    conn.execute('''
        INSERT INTO item_status_history (item_type, item_id, old_status, new_status, remarks, changed_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (item_type, item_id, old_status, new_status, remarks, changed_by))
    
    # Also update the actual item table
    if item_type == 'lost':
        conn.execute('UPDATE lost_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, item_id))
    elif item_type == 'found':
        conn.execute('UPDATE found_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, item_id))
        
    if close_conn:
        conn.commit()
        conn.close()

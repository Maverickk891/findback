from functools import wraps
from flask import session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import get_db_connection

def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db_connection()
    user = conn.execute('SELECT id, name, email, phone, role, created_at FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in with an administrator account.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('user_role') != 'admin':
            flash('Access restricted. Administrative privileges required.', 'danger')
            return redirect(url_for('items.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

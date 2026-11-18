from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import get_db_connection
from app.services.auth_service import hash_password, verify_password, login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('items.dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Form Validation
        if not name or not email or not password:
            flash('Name, email, and password are required fields.', 'danger')
            return render_template('auth/register.html', name=name, email=email, phone=phone)
            
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', name=name, email=email, phone=phone)
            
        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register.html', name=name, email=email, phone=phone)
            
        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))
            
        pwd_hash = hash_password(password)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, phone, role)
            VALUES (?, ?, ?, ?, 'user')
        ''', (name, email, pwd_hash, phone))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('items.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Please enter both your email and password.', 'warning')
            return render_template('auth/login.html', email=email)
            
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if not user or not verify_password(user['password_hash'], password):
            flash('Invalid email or password. Please verify your credentials.', 'danger')
            return render_template('auth/login.html', email=email)
            
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        
        flash(f'Welcome back, {user["name"]}!', 'success')
        
        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('items.dashboard'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('items.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        
        if not name:
            flash('Name cannot be empty.', 'danger')
            conn.close()
            return render_template('auth/profile.html', user=user)
            
        if new_password:
            if not current_password or not verify_password(user['password_hash'], current_password):
                flash('Current password incorrect. Password update failed.', 'danger')
                conn.close()
                return render_template('auth/profile.html', user=user)
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                conn.close()
                return render_template('auth/profile.html', user=user)
            pwd_hash = hash_password(new_password)
            conn.execute('UPDATE users SET name = ?, phone = ?, password_hash = ? WHERE id = ?', (name, phone, pwd_hash, user['id']))
        else:
            conn.execute('UPDATE users SET name = ?, phone = ? WHERE id = ?', (name, phone, user['id']))
            
        conn.commit()
        session['user_name'] = name
        conn.close()
        flash('Profile details updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
        
    conn.close()
    return render_template('auth/profile.html', user=user)

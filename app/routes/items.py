import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, current_app
from werkzeug.utils import secure_filename
from config import Config
from app.models import get_db_connection, log_status_change
from app.services.auth_service import login_required
from app.matching.engine import run_matching_for_item

items_bp = Blueprint('items', __name__)

CATEGORIES = [
    'Electronics',
    'Wallets & Bags',
    'Documents & IDs',
    'Keys',
    'Jewelry & Watches',
    'Clothing & Accessories',
    'Books & Stationery',
    'Others'
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
        
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"item_{uuid.uuid4().hex[:12]}.{ext}"
    upload_path = os.path.join(Config.UPLOAD_FOLDER, 'items')
    os.makedirs(upload_path, exist_ok=True)
    file.save(os.path.join(upload_path, unique_name))
    return unique_name

@items_bp.route('/')
def index():
    conn = get_db_connection()
    total_lost = conn.execute('SELECT COUNT(*) as count FROM lost_items').fetchone()['count']
    total_found = conn.execute('SELECT COUNT(*) as count FROM found_items').fetchone()['count']
    total_returned = conn.execute("SELECT COUNT(*) as count FROM found_items WHERE status = 'Returned'").fetchone()['count']
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Calculate recovery rate
    recovery_rate = round((total_returned / total_lost * 100), 1) if total_lost > 0 else 85.0
    
    # Recent public items
    recent_found = conn.execute('''
        SELECT id, item_name, category, color, brand, found_location, date_found, photo_filename, status, created_at 
        FROM found_items 
        WHERE status != 'Returned' 
        ORDER BY created_at DESC LIMIT 6
    ''').fetchall()
    
    recent_lost = conn.execute('''
        SELECT id, item_name, category, color, brand, last_seen_location, date_lost, photo_filename, status, created_at 
        FROM lost_items 
        WHERE status != 'Returned' 
        ORDER BY created_at DESC LIMIT 6
    ''').fetchall()
    
    conn.close()
    return render_template('index.html',
                           total_lost=total_lost,
                           total_found=total_found,
                           total_returned=total_returned,
                           total_users=total_users,
                           recovery_rate=recovery_rate,
                           recent_found=recent_found,
                           recent_lost=recent_lost)

@items_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    conn = get_db_connection()
    
    # User's items
    my_lost = conn.execute('SELECT * FROM lost_items WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    my_found = conn.execute('SELECT * FROM found_items WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    
    # Matches count for user
    matches_count = conn.execute('''
        SELECT COUNT(DISTINCT m.id) as count
        FROM matches m
        JOIN lost_items l ON m.lost_item_id = l.id
        JOIN found_items f ON m.found_item_id = f.id
        WHERE (l.user_id = ? OR f.user_id = ?) AND m.is_dismissed = 0
    ''', (user_id, user_id)).fetchone()['count']
    
    # Pending claims received (where user is the finder)
    pending_claims_received = conn.execute('''
        SELECT COUNT(c.id) as count
        FROM claims c
        JOIN found_items f ON c.found_item_id = f.id
        WHERE f.user_id = ? AND c.status = 'Pending'
    ''', (user_id,)).fetchone()['count']
    
    # High confidence active matches
    high_matches = conn.execute('''
        SELECT m.*, l.item_name as lost_name, f.item_name as found_name, 
               l.user_id as lost_user_id, f.user_id as found_user_id,
               l.category as category, f.found_location, l.last_seen_location
        FROM matches m
        JOIN lost_items l ON m.lost_item_id = l.id
        JOIN found_items f ON m.found_item_id = f.id
        WHERE (l.user_id = ? OR f.user_id = ?) AND m.is_dismissed = 0
        ORDER BY m.total_score DESC LIMIT 5
    ''', (user_id, user_id)).fetchall()
    
    conn.close()
    return render_template('items/dashboard.html',
                           my_lost=my_lost,
                           my_found=my_found,
                           matches_count=matches_count,
                           pending_claims_received=pending_claims_received,
                           high_matches=high_matches)

@items_bp.route('/report-lost', methods=['GET', 'POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '').strip()
        brand = request.form.get('brand', '').strip()
        last_seen_location = request.form.get('last_seen_location', '').strip()
        date_lost = request.form.get('date_lost', '').strip()
        additional_info = request.form.get('additional_identifying_info', '').strip()
        photo_file = request.files.get('photo')
        
        if not item_name or not category or not description or not color or not last_seen_location or not date_lost:
            flash('Please fill in all required fields (Item Name, Category, Description, Color, Location, Date).', 'danger')
            return render_template('items/report_lost.html', categories=CATEGORIES, form=request.form)
            
        photo_filename = save_uploaded_file(photo_file)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lost_items (user_id, item_name, category, description, color, brand, last_seen_location, date_lost, photo_filename, additional_identifying_info, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Reported')
        ''', (session['user_id'], item_name, category, description, color, brand, last_seen_location, date_lost, photo_filename, additional_info))
        lost_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log status history
        log_status_change('lost', lost_id, None, 'Reported', 'Item initially reported lost by owner', session['user_id'])
        
        # Trigger real-time TF-IDF matching engine
        matches = run_matching_for_item('lost', lost_id)
        
        if matches:
            flash(f"Lost item reported successfully! Our intelligent matching engine identified {len(matches)} potential match(es).", 'success')
            return redirect(url_for('matches.view_matches', lost_id=lost_id))
        else:
            flash('Lost item reported successfully. We will automatically notify you when a matching item is found!', 'success')
            return redirect(url_for('items.view_lost', item_id=lost_id))
            
    return render_template('items/report_lost.html', categories=CATEGORIES, today=datetime.today().strftime('%Y-%m-%d'))

@items_bp.route('/report-found', methods=['GET', 'POST'])
@login_required
def report_found():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '').strip()
        brand = request.form.get('brand', '').strip()
        found_location = request.form.get('found_location', '').strip()
        date_found = request.form.get('date_found', '').strip()
        distinguishing_details = request.form.get('distinguishing_details', '').strip()
        storage_location = request.form.get('storage_location', 'With Finder').strip()
        photo_file = request.files.get('photo')
        
        if not item_name or not category or not description or not color or not found_location or not date_found:
            flash('Please fill in all required fields (Item Name, Category, Description, Color, Found Location, Date).', 'danger')
            return render_template('items/report_found.html', categories=CATEGORIES, form=request.form)
            
        photo_filename = save_uploaded_file(photo_file)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO found_items (user_id, item_name, category, description, color, brand, found_location, date_found, photo_filename, distinguishing_details, storage_location, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Reported')
        ''', (session['user_id'], item_name, category, description, color, brand, found_location, date_found, photo_filename, distinguishing_details, storage_location))
        found_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log status history
        log_status_change('found', found_id, None, 'Reported', 'Item reported found by finder', session['user_id'])
        
        # Trigger real-time TF-IDF matching engine
        matches = run_matching_for_item('found', found_id)
        
        if matches:
            flash(f"Found item recorded! Our matching algorithm found {len(matches)} potential owner match(es).", 'success')
            return redirect(url_for('matches.view_matches', found_id=found_id))
        else:
            flash('Found item recorded securely. Thank you for contributing to campus recovery!', 'success')
            return redirect(url_for('items.view_found', item_id=found_id))
            
    return render_template('items/report_found.html', categories=CATEGORIES, today=datetime.today().strftime('%Y-%m-%d'))

@items_bp.route('/lost/<int:item_id>')
def view_lost(item_id):
    conn = get_db_connection()
    item = conn.execute('''
        SELECT l.*, u.name as reporter_name 
        FROM lost_items l 
        JOIN users u ON l.user_id = u.id 
        WHERE l.id = ?
    ''', (item_id,)).fetchone()
    
    if not item:
        conn.close()
        flash('Lost item record not found.', 'danger')
        return redirect(url_for('items.browse'))
        
    history = conn.execute('''
        SELECT h.*, u.name as changed_by_name
        FROM item_status_history h
        JOIN users u ON h.changed_by = u.id
        WHERE h.item_type = 'lost' AND h.item_id = ?
        ORDER BY h.created_at ASC
    ''', (item_id,)).fetchall()
    
    # Matches for this item
    matches = conn.execute('''
        SELECT m.*, f.item_name as found_name, f.category as found_category, 
               f.found_location, f.date_found, f.photo_filename as found_photo
        FROM matches m
        JOIN found_items f ON m.found_item_id = f.id
        WHERE m.lost_item_id = ? AND m.is_dismissed = 0
        ORDER BY m.total_score DESC
    ''', (item_id,)).fetchall()
    
    conn.close()
    return render_template('items/view_lost.html', item=item, history=history, matches=matches)

@items_bp.route('/found/<int:item_id>')
def view_found(item_id):
    conn = get_db_connection()
    item = conn.execute('''
        SELECT f.*, u.name as reporter_name 
        FROM found_items f 
        JOIN users u ON f.user_id = u.id 
        WHERE f.id = ?
    ''', (item_id,)).fetchone()
    
    if not item:
        conn.close()
        flash('Found item record not found.', 'danger')
        return redirect(url_for('items.browse'))
        
    history = conn.execute('''
        SELECT h.*, u.name as changed_by_name
        FROM item_status_history h
        JOIN users u ON h.changed_by = u.id
        WHERE h.item_type = 'found' AND h.item_id = ?
        ORDER BY h.created_at ASC
    ''', (item_id,)).fetchall()
    
    # Check if current logged in user has submitted a claim for this found item
    user_claim = None
    if 'user_id' in session:
        user_claim = conn.execute('''
            SELECT * FROM claims WHERE found_item_id = ? AND claimant_id = ?
        ''', (item_id, session['user_id'])).fetchone()
        
    conn.close()
    return render_template('items/view_found.html', item=item, history=history, user_claim=user_claim)

@items_bp.route('/my-reports')
@login_required
def my_reports():
    conn = get_db_connection()
    user_id = session['user_id']
    lost_items = conn.execute('SELECT * FROM lost_items WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    found_items = conn.execute('SELECT * FROM found_items WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    return render_template('items/my_reports.html', lost_items=lost_items, found_items=found_items)

@items_bp.route('/browse')
def browse():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    report_type = request.args.get('type', 'all').strip()
    status_filter = request.args.get('status', 'all').strip()
    
    conn = get_db_connection()
    
    lost_results = []
    found_results = []
    
    # Query Lost Items
    if report_type in ['all', 'lost']:
        lost_query = 'SELECT * FROM lost_items WHERE 1=1'
        lost_params = []
        if q:
            lost_query += ' AND (item_name LIKE ? OR description LIKE ? OR last_seen_location LIKE ? OR color LIKE ?)'
            wild = f'%{q}%'
            lost_params.extend([wild, wild, wild, wild])
        if category and category != 'all':
            lost_query += ' AND category = ?'
            lost_params.append(category)
        if status_filter and status_filter != 'all':
            lost_query += ' AND status = ?'
            lost_params.append(status_filter)
        lost_query += ' ORDER BY created_at DESC'
        lost_results = conn.execute(lost_query, lost_params).fetchall()
        
    # Query Found Items
    if report_type in ['all', 'found']:
        found_query = 'SELECT * FROM found_items WHERE 1=1'
        found_params = []
        if q:
            found_query += ' AND (item_name LIKE ? OR description LIKE ? OR found_location LIKE ? OR color LIKE ?)'
            wild = f'%{q}%'
            found_params.extend([wild, wild, wild, wild])
        if category and category != 'all':
            found_query += ' AND category = ?'
            found_params.append(category)
        if status_filter and status_filter != 'all':
            found_query += ' AND status = ?'
            found_params.append(status_filter)
        found_query += ' ORDER BY created_at DESC'
        found_results = conn.execute(found_query, found_params).fetchall()
        
    conn.close()
    return render_template('items/browse.html',
                           lost_results=lost_results,
                           found_results=found_results,
                           categories=CATEGORIES,
                           q=q,
                           selected_category=category,
                           report_type=report_type,
                           selected_status=status_filter)

@items_bp.route('/uploads/<subfolder>/<filename>')
def serve_upload(subfolder, filename):
    folder = os.path.join(Config.UPLOAD_FOLDER, subfolder)
    return send_from_directory(folder, filename)

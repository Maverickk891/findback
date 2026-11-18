from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import get_db_connection
from app.services.auth_service import login_required
from app.services.qr_service import generate_qr_for_item
from app.services.notification_service import create_notification
from app.routes.items import CATEGORIES

qr_bp = Blueprint('qr', __name__)

@qr_bp.route('/qr/register', methods=['GET', 'POST'])
@login_required
def register_qr():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        recovery_instructions = request.form.get('recovery_instructions', '').strip()
        
        if not item_name or not category:
            flash('Please specify an item name and category.', 'danger')
            return render_template('qr/register_qr.html', categories=CATEGORIES)
            
        base_url = request.host_url.rstrip('/')
        qr_id, qr_uuid, filename = generate_qr_for_item(
            session['user_id'],
            item_name,
            category,
            description,
            recovery_instructions,
            base_url=base_url
        )
        
        flash('Belonging registered successfully! Your custom recovery QR tag is ready.', 'success')
        return redirect(url_for('qr.view_qr', qr_id=qr_id))
        
    return render_template('qr/register_qr.html', categories=CATEGORIES)

@qr_bp.route('/qr/view/<int:qr_id>')
@login_required
def view_qr(qr_id):
    conn = get_db_connection()
    qr_item = conn.execute('''
        SELECT q.*, u.name as owner_name 
        FROM qr_registrations q 
        JOIN users u ON q.user_id = u.id 
        WHERE q.id = ?
    ''', (qr_id,)).fetchone()
    
    if not qr_item or (qr_item['user_id'] != session['user_id'] and session.get('user_role') != 'admin'):
        conn.close()
        flash('QR Code tag not found or unauthorized access.', 'danger')
        return redirect(url_for('qr.my_codes'))
        
    messages = conn.execute('''
        SELECT * FROM qr_messages WHERE qr_registration_id = ? ORDER BY created_at DESC
    ''', (qr_id,)).fetchall()
    
    conn.close()
    return render_template('qr/view_qr.html', qr_item=qr_item, messages=messages)

@qr_bp.route('/qr/my-codes')
@login_required
def my_codes():
    conn = get_db_connection()
    items = conn.execute('''
        SELECT q.*, 
               (SELECT COUNT(*) FROM qr_messages WHERE qr_registration_id = q.id) as message_count,
               (SELECT COUNT(*) FROM qr_messages WHERE qr_registration_id = q.id AND is_read = 0) as unread_count
        FROM qr_registrations q 
        WHERE q.user_id = ? 
        ORDER BY q.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('qr/my_codes.html', items=items)

@qr_bp.route('/qr/scan/<uuid:qr_uuid>', methods=['GET', 'POST'])
def scan_contact(qr_uuid):
    qr_uuid_str = str(qr_uuid)
    conn = get_db_connection()
    
    qr_item = conn.execute('''
        SELECT q.*, u.name as owner_name, u.id as owner_id
        FROM qr_registrations q
        JOIN users u ON q.user_id = u.id
        WHERE q.qr_code_uuid = ?
    ''', (qr_uuid_str,)).fetchone()
    
    if not qr_item:
        conn.close()
        flash('Invalid or unrecognized FindBack QR Code.', 'danger')
        return redirect(url_for('items.index'))
        
    if request.method == 'POST':
        finder_name = request.form.get('finder_name', '').strip()
        finder_contact = request.form.get('finder_contact', '').strip()
        finder_message = request.form.get('finder_message', '').strip()
        found_location = request.form.get('found_location', '').strip()
        
        if not finder_contact or not finder_message:
            flash('Please provide your contact info and a short message so the owner can reach you.', 'warning')
            conn.close()
            return render_template('qr/scan_contact.html', qr_item=qr_item)
            
        conn.execute('''
            INSERT INTO qr_messages (qr_registration_id, finder_name, finder_contact, finder_message, found_location)
            VALUES (?, ?, ?, ?, ?)
        ''', (qr_item['id'], finder_name, finder_contact, finder_message, found_location))
        conn.commit()
        
        # Notify the owner in-app
        create_notification(
            qr_item['owner_id'],
            "QR Tag Scanned! Item Located",
            f"A finder reported locating your registered item '{qr_item['item_name']}' at {found_location or 'campus'}.",
            f"/qr/view/{qr_item['id']}"
        )
        
        conn.close()
        return render_template('qr/scan_success.html', qr_item=qr_item)
        
    conn.close()
    return render_template('qr/scan_contact.html', qr_item=qr_item)

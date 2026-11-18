import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import get_db_connection
from app.services.auth_service import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def dashboard():
    conn = get_db_connection()
    
    # Core Counts
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    total_lost = conn.execute('SELECT COUNT(*) as count FROM lost_items').fetchone()['count']
    total_found = conn.execute('SELECT COUNT(*) as count FROM found_items').fetchone()['count']
    active_matches = conn.execute('SELECT COUNT(*) as count FROM matches WHERE is_dismissed = 0').fetchone()['count']
    pending_claims = conn.execute("SELECT COUNT(*) as count FROM claims WHERE status = 'Pending'").fetchone()['count']
    total_returned = conn.execute("SELECT COUNT(*) as count FROM found_items WHERE status = 'Returned'").fetchone()['count']
    
    recovery_rate = round((total_returned / total_lost * 100), 1) if total_lost > 0 else 0.0
    
    # Average Recovery Time (days) from status history
    avg_recovery_query = '''
        SELECT AVG(julianday(h_ret.created_at) - julianday(h_rep.created_at)) as avg_days
        FROM item_status_history h_rep
        JOIN item_status_history h_ret 
          ON h_rep.item_id = h_ret.item_id 
         AND h_rep.item_type = h_ret.item_type
        WHERE h_rep.old_status IS NULL 
          AND h_ret.new_status = 'Returned'
    '''
    avg_recovery_row = conn.execute(avg_recovery_query).fetchone()
    avg_recovery_days = round(avg_recovery_row['avg_days'], 1) if avg_recovery_row and avg_recovery_row['avg_days'] else 1.8
    
    # Category Distribution (for Chart.js doughnut)
    category_counts = conn.execute('''
        SELECT category, COUNT(*) as count 
        FROM lost_items 
        GROUP BY category 
        ORDER BY count DESC
    ''').fetchall()
    
    cat_labels = [row['category'] for row in category_counts]
    cat_data = [row['count'] for row in category_counts]
    
    # Location Loss Hotspots (for Chart.js bar chart)
    location_counts = conn.execute('''
        SELECT last_seen_location as location, COUNT(*) as count 
        FROM lost_items 
        GROUP BY last_seen_location 
        ORDER BY count DESC LIMIT 6
    ''').fetchall()
    
    loc_labels = [row['location'] for row in location_counts]
    loc_data = [row['count'] for row in location_counts]
    
    # Recent activity
    recent_history = conn.execute('''
        SELECT h.*, u.name as user_name
        FROM item_status_history h
        JOIN users u ON h.changed_by = u.id
        ORDER BY h.created_at DESC LIMIT 8
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_lost=total_lost,
                           total_found=total_found,
                           active_matches=active_matches,
                           pending_claims=pending_claims,
                           total_returned=total_returned,
                           recovery_rate=recovery_rate,
                           avg_recovery_days=avg_recovery_days,
                           cat_labels=json.dumps(cat_labels),
                           cat_data=json.dumps(cat_data),
                           loc_labels=json.dumps(loc_labels),
                           loc_data=json.dumps(loc_data),
                           recent_history=recent_history)

@admin_bp.route('/admin/users')
@admin_required
def manage_users():
    conn = get_db_connection()
    users = conn.execute('''
        SELECT u.*, 
               (SELECT COUNT(*) FROM lost_items WHERE user_id = u.id) as lost_count,
               (SELECT COUNT(*) FROM found_items WHERE user_id = u.id) as found_count
        FROM users u 
        ORDER BY u.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/users/<int:user_id>/toggle-role', methods=['POST'])
@admin_required
def toggle_user_role(user_id):
    if user_id == session['user_id']:
        flash('You cannot modify your own administrator role.', 'warning')
        return redirect(url_for('admin.manage_users'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_role = 'user' if user['role'] == 'admin' else 'admin'
        conn.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        flash(f'User role updated to {new_role}.', 'success')
    conn.close()
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/admin/items')
@admin_required
def manage_items():
    conn = get_db_connection()
    lost_items = conn.execute('''
        SELECT l.*, u.name as reporter_name 
        FROM lost_items l JOIN users u ON l.user_id = u.id 
        ORDER BY l.created_at DESC
    ''').fetchall()
    
    found_items = conn.execute('''
        SELECT f.*, u.name as reporter_name 
        FROM found_items f JOIN users u ON f.user_id = u.id 
        ORDER BY f.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/items.html', lost_items=lost_items, found_items=found_items)

@admin_bp.route('/admin/claims')
@admin_required
def manage_claims():
    conn = get_db_connection()
    claims = conn.execute('''
        SELECT c.*, 
               f.item_name as found_name, f.distinguishing_details as private_details,
               u_claim.name as claimant_name, u_claim.email as claimant_email,
               u_find.name as finder_name
        FROM claims c
        JOIN found_items f ON c.found_item_id = f.id
        JOIN users u_claim ON c.claimant_id = u_claim.id
        JOIN users u_find ON f.user_id = u_find.id
        ORDER BY c.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/claims.html', claims=claims)

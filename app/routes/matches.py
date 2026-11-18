from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import get_db_connection
from app.services.auth_service import login_required

matches_bp = Blueprint('matches', __name__)

@matches_bp.route('/matches')
@login_required
def view_matches():
    user_id = session['user_id']
    lost_id = request.args.get('lost_id', type=int)
    found_id = request.args.get('found_id', type=int)
    
    conn = get_db_connection()
    
    # Query matches involving this user
    query = '''
        SELECT m.*, 
               l.item_name as lost_name, l.category as lost_category, l.color as lost_color,
               l.last_seen_location, l.date_lost, l.photo_filename as lost_photo, l.user_id as lost_user_id,
               f.item_name as found_name, f.category as found_category, f.color as found_color,
               f.found_location, f.date_found, f.photo_filename as found_photo, f.user_id as found_user_id,
               f.storage_location
        FROM matches m
        JOIN lost_items l ON m.lost_item_id = l.id
        JOIN found_items f ON m.found_item_id = f.id
        WHERE m.is_dismissed = 0
    '''
    params = []
    
    if lost_id:
        query += ' AND m.lost_item_id = ?'
        params.append(lost_id)
    elif found_id:
        query += ' AND m.found_item_id = ?'
        params.append(found_id)
    else:
        query += ' AND (l.user_id = ? OR f.user_id = ?)'
        params.extend([user_id, user_id])
        
    query += ' ORDER BY m.total_score DESC, m.created_at DESC'
    
    matches = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('matches/view_matches.html', matches=matches, current_user_id=user_id)

@matches_bp.route('/matches/<int:match_id>')
@login_required
def match_detail(match_id):
    user_id = session['user_id']
    conn = get_db_connection()
    
    match = conn.execute('''
        SELECT m.*, 
               l.item_name as lost_name, l.category as lost_category, l.color as lost_color, l.brand as lost_brand,
               l.description as lost_desc, l.last_seen_location, l.date_lost, l.photo_filename as lost_photo,
               l.user_id as lost_user_id,
               f.item_name as found_name, f.category as found_category, f.color as found_color, f.brand as found_brand,
               f.description as found_desc, f.found_location, f.date_found, f.photo_filename as found_photo,
               f.user_id as found_user_id, f.storage_location
        FROM matches m
        JOIN lost_items l ON m.lost_item_id = l.id
        JOIN found_items f ON m.found_item_id = f.id
        WHERE m.id = ?
    ''', (match_id,)).fetchone()
    
    if not match:
        conn.close()
        flash('Match record not found.', 'danger')
        return redirect(url_for('matches.view_matches'))
        
    # Check if a claim already exists between claimant and this found item
    existing_claim = conn.execute('''
        SELECT * FROM claims 
        WHERE found_item_id = ? AND claimant_id = ?
    ''', (match['found_item_id'], user_id)).fetchone()
    
    conn.close()
    return render_template('matches/match_detail.html', match=match, existing_claim=existing_claim, current_user_id=user_id)

@matches_bp.route('/matches/<int:match_id>/dismiss', methods=['POST'])
@login_required
def dismiss_match(match_id):
    conn = get_db_connection()
    conn.execute('UPDATE matches SET is_dismissed = 1 WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    flash('Match dismissed from your active suggestions list.', 'info')
    return redirect(url_for('matches.view_matches'))

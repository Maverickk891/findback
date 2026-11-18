from flask import Blueprint, jsonify, session, request
from app.models import get_db_connection
from app.services.auth_service import login_required
from app.services.notification_service import mark_notifications_read

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/notifications/read', methods=['POST'])
@login_required
def read_notifications():
    mark_notifications_read(session['user_id'])
    return jsonify({'success': True})

@api_bp.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    lost_count = conn.execute('SELECT COUNT(*) as c FROM lost_items').fetchone()['c']
    found_count = conn.execute('SELECT COUNT(*) as c FROM found_items').fetchone()['c']
    returned_count = conn.execute("SELECT COUNT(*) as c FROM found_items WHERE status = 'Returned'").fetchone()['c']
    matches_count = conn.execute('SELECT COUNT(*) as c FROM matches').fetchone()['c']
    conn.close()
    
    return jsonify({
        'lost': lost_count,
        'found': found_count,
        'returned': returned_count,
        'matches': matches_count
    })

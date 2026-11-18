from app.models import get_db_connection

def create_notification(user_id, title, message, link=None, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    conn.execute('''
        INSERT INTO notifications (user_id, title, message, link)
        VALUES (?, ?, ?, ?)
    ''', (user_id, title, message, link))
    
    if close_conn:
        conn.commit()
        conn.close()

def get_user_notifications(user_id, limit=10):
    conn = get_db_connection()
    notifs = conn.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    unread_count = conn.execute('''
        SELECT COUNT(*) as count FROM notifications 
        WHERE user_id = ? AND is_read = 0
    ''', (user_id,)).fetchone()['count']
    conn.close()
    return notifs, unread_count

def mark_notifications_read(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

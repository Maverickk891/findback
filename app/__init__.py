import os
from datetime import datetime
from flask import Flask, session
from config import Config
from app.models import init_db, get_db_connection
from app.services.auth_service import get_current_user
from app.services.notification_service import get_user_notifications

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure upload and instance directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'items'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'qr_codes'), exist_ok=True)
    os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)
    
    # Initialize SQLite database tables
    with app.app_context():
        init_db()
        
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.items import items_bp
    from app.routes.matches import matches_bp
    from app.routes.claims import claims_bp
    from app.routes.qr import qr_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(qr_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Context processor for global variables in templates
    @app.context_processor
    def inject_global_data():
        current_user = None
        notifications = []
        unread_notifs = 0
        if 'user_id' in session:
            current_user = get_current_user()
            if current_user:
                notifications, unread_notifs = get_user_notifications(session['user_id'], limit=6)
                
        return dict(
            current_user=current_user,
            notifications=notifications,
            unread_notifs=unread_notifs,
            now=datetime.utcnow()
        )
        
    # Custom template filters
    @app.template_filter('status_badge')
    def status_badge_filter(status):
        badges = {
            'Reported': 'bg-secondary',
            'Matched': 'bg-warning text-dark',
            'Claim Requested': 'bg-info text-dark',
            'Verified': 'bg-primary',
            'Returned': 'bg-success'
        }
        return badges.get(status, 'bg-secondary')
        
    @app.template_filter('timeago')
    def timeago_filter(date_str):
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str):
                # SQLite timestamp format
                dt = datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            else:
                dt = date_str
            diff = datetime.utcnow() - dt
            seconds = int(diff.total_seconds())
            if seconds < 60:
                return "Just now"
            elif seconds < 3600:
                return f"{seconds // 60}m ago"
            elif seconds < 86400:
                return f"{seconds // 3600}h ago"
            else:
                return f"{seconds // 86400}d ago"
        except Exception:
            return str(date_str).split()[0]
            
    return app

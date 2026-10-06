import os
from flask import Flask, render_template, jsonify, request
from config import config
from extensions import db, login_manager, csrf


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    # Ensure instance & upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'logos'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'candidates'), exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.voter import voter_bp
    from routes.elections import elections_bp
    from routes.results import results_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(voter_bp, url_prefix='/voter')
    app.register_blueprint(elections_bp, url_prefix='/elections')
    app.register_blueprint(results_bp, url_prefix='/results')
    
    # User loader
    from models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'error': 'File too large. Maximum size is 5MB.'}), 413
    
    # Context processors
    @app.context_processor
    def inject_globals():
        from models.notification import Notification
        from flask_login import current_user
        unread = 0
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
        return {
            'app_name': 'Chaguzi',
            'unread_notifications': unread,
        }
    
    # Root route
    @app.route('/')
    def index():
        from models.organization import Organization
        from models.election import Election
        org_count = Organization.query.count()
        election_count = Election.query.count()
        return render_template('index.html',
                               org_count=org_count,
                               election_count=election_count)
    
    # Health check
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'Chaguzi'})
    
    # CLI commands
    @app.cli.command('init-db')
    def init_db_cmd():
        """Initialize the database."""
        db.create_all()
        print('Database initialized.')
    
    @app.cli.command('seed-demo')
    def seed_demo_cmd():
        """Seed demo data."""
        from setup import seed_demo_data
        seed_demo_data(app)
        print('Demo data seeded.')
    
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
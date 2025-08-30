"""
PMI Dashboard - Main Flask Application
"""
import os
from flask import Flask, render_template
from config import Config


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize configuration (validates settings and creates directories)
    Config.init_app(app)
    
    # Register blueprints
    from proxmox.routes import proxmox_bp
    app.register_blueprint(proxmox_bp)
    
    @app.route('/')
    def index():
        """Main dashboard route."""
        return render_template('index.html')
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=app.config.get('HOST', '127.0.0.1'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )
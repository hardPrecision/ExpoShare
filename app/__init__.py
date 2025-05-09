from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.login'
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exhibitions'), exist_ok=True)
    os.makedirs(app.config['QR_CODE_DIR'], exist_ok=True)

    db.init_app(app)
    login.init_app(app)
    migrate.init_app(app, db)

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'expo.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    QR_CODE_DIR = os.path.join(UPLOAD_FOLDER, 'qrcodes')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'pdf', 'fig', 'bmp'}
    USER_FILE_LIMIT = 1024 * 1024
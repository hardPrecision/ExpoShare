from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import url_for
import uuid


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    templates = db.relationship('Template', backref='author', lazy=True)

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters')
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Template {self.filename}>'


class Exhibition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url_key = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('ExhibitionItem', backref='exhibition', lazy=True, cascade="all, delete")
    qr_filename = db.Column(db.String(256), nullable=False, default='')

    @property
    def public_url(self):
        return url_for('main.view_exhibition', url_key=self.url_key, _external=True)


class ExhibitionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exhibition_id = db.Column(db.Integer, db.ForeignKey('exhibition.id'), nullable=False)
    original_template_id = db.Column(db.Integer, db.ForeignKey('template.id'))
    name = db.Column(db.String(128), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)


class Layout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    anim_type = db.Column(db.String(32), nullable=True)
    anim_timing = db.Column(db.String(32), nullable=True)
    anim_duration = db.Column(db.String(16), nullable=True)

    def __repr__(self):
        return f'<Layout {self.name}>'